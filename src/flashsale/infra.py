from contextlib import contextmanager
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
from urllib.request import urlopen
from uuid import uuid4

from flashsale.adapters.base import Endpoint, open_adapter

ROOT = Path(__file__).resolve().parents[2]
ENGINES = ("mysql", "mongo", "tidb")
# Ngân sách container chung cho MỌI hệ (mục 2.1: cùng tổng CPU/RAM). Xem docs/assumptions.md.
BUDGET_CPUS = 8
BUDGET_MEMORY_BYTES = 16 * 1024 ** 3
DEFAULT_PORTS = {"mysql": 13306, "mongo": 27018, "tidb": 14000, "pd": 12379}


def port(service: str) -> int:
    key = f"FLASHSALE_{service.upper()}_PORT"
    if key in os.environ:
        return int(os.environ[key])
    env_file = ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, sep, value = line.partition("=")
            if sep and name.strip() == key:
                return int(value.strip().strip('"').strip("'"))
    return DEFAULT_PORTS[service]


def endpoint(engine: str, database: str | None = None) -> Endpoint:
    return Endpoint(engine, port(engine), database or f"flashsale_{uuid4().hex}")


def docker(*args: str, timeout: float = 15, capture: bool = True) -> str:
    result = subprocess.run(["docker", *args], cwd=ROOT, timeout=timeout, check=True,
                            text=True, stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else ""


def compose(engine: str, *args: str, timeout: float = 15, capture: bool = True) -> str:
    env_file = ROOT / ".env"
    env_args = ("--env-file", str(env_file)) if env_file.is_file() else ()
    return docker("compose", *env_args, "-f", str(ROOT / "docker" / f"compose.{engine}.yml"),
                  *args, timeout=timeout, capture=capture)


@contextmanager
def project_lock():
    folder = ROOT / "results"
    folder.mkdir(exist_ok=True)
    with (folder / "project.lock").open("a+b") as stream:
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError("Một lệnh Flash-sale đang sử dụng môi trường") from exc
        yield


def active_engines() -> dict[str, list[str]]:
    running = {}
    for engine in ENGINES:
        output = docker("ps", "--quiet", "--filter", f"label=com.docker.compose.project=flashsale-{engine}")
        running[engine] = output.splitlines()
    return running


def enforce_one(engine: str, *, must_run: bool = True) -> None:
    running = active_engines()
    others = [name for name, containers in running.items() if name != engine and containers]
    if others:
        raise RuntimeError(f"Hãy dừng DBMS dự án đang chạy: {', '.join(others)}")
    if must_run and not running[engine]:
        raise RuntimeError(f"{engine} chưa chạy")


def pd_status() -> dict:
    base = f"http://127.0.0.1:{port('pd')}/pd/api/v1"
    with urlopen(base + "/stores", timeout=2) as response:
        stores = json.load(response)["stores"]
    with urlopen(base + "/config/replicate", timeout=2) as response:
        replica = json.load(response)
    live = [entry["store"] for entry in stores if entry["store"]["state_name"] == "Up"]
    if len(live) != 3 or replica.get("max-replicas") != 1:
        raise RuntimeError(f"TiDB cần 3 TiKV Up và max-replicas=1. Hiện có {len(live)} store, {replica}")
    return {"store_versions": {store["address"]: store["version"] for store in live},
            "max_replicas": replica["max-replicas"]}


def ready(engine: str, timeout: float = 150) -> dict:
    deadline = time.monotonic() + timeout
    while True:
        try:
            evidence = pd_status() if engine == "tidb" else {}
            db = open_adapter(endpoint(engine), admin=True)
            try:
                return {**evidence, **db.ping()}
            finally:
                db.close()
        except Exception as exc:
            if time.monotonic() >= deadline:
                raise RuntimeError(f"{engine} không sẵn sàng: {exc}") from exc
            time.sleep(1)


def start(engine: str) -> dict:
    enforce_one(engine, must_run=False)
    args = ["up", "-d", "--wait", "--wait-timeout", "150"]
    compose(engine, *args, timeout=240, capture=False)
    return ready(engine)


def stop(engine: str) -> None:
    compose(engine, "stop", timeout=180, capture=False)


def container_limits(engine: str) -> dict[str, dict]:
    ids = active_engines()[engine]
    inspected = json.loads(docker("inspect", *ids))
    result = {}
    for item in inspected:
        cfg = item["Config"]
        host = item["HostConfig"]
        name = cfg["Labels"]["com.docker.compose.service"]
        image = json.loads(docker("image", "inspect", item["Image"]))[0]
        result[name] = {"id": item["Id"], "image": cfg["Image"], "image_id": item["Image"],
                        "repo_digests": image["RepoDigests"],
                        "cpus": host["NanoCpus"] / 1e9, "memory_bytes": host["Memory"]}
    if len(result) != (5 if engine == "tidb" else 1):
        raise RuntimeError("Thiếu container của cấu hình mục 2.1")
    if sum(entry["cpus"] for entry in result.values()) != BUDGET_CPUS or sum(
            entry["memory_bytes"] for entry in result.values()) != BUDGET_MEMORY_BYTES:
        raise RuntimeError(f"Container đang chạy khác ngân sách {BUDGET_CPUS} CPU và "
                           f"{BUDGET_MEMORY_BYTES // 1024 ** 3} GiB")
    return result


def docker_cpu(limits: dict[str, dict]) -> dict[str, float]:
    ids = {value["id"][:12]: name for name, value in limits.items()}
    values = {}
    for line in docker("stats", "--no-stream", "--format", "{{json .}}", *ids, timeout=8).splitlines():
        row = json.loads(line)
        if row["ID"][:12] in ids and row["CPUPerc"].endswith("%"):
            values[ids[row["ID"][:12]]] = float(row["CPUPerc"][:-1])
    return values


def host_info() -> dict:
    runtime = json.loads(docker("info", "--format", "{{json .}}"))
    disk = shutil.disk_usage(ROOT)
    mem = None
    if sys.platform == "linux":
        mem = int(Path("/proc/meminfo").read_text().splitlines()[0].split()[1]) * 1024
    elif os.name == "nt":
        import ctypes
        memory = ctypes.c_ulonglong()
        if ctypes.windll.kernel32.GetPhysicallyInstalledSystemMemory(ctypes.byref(memory)):
            mem = memory.value * 1024
    repo = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=ROOT,
                          capture_output=True, text=True, check=False) if shutil.which("git") else None
    scoped = repo and repo.returncode == 0 and Path(repo.stdout.strip()).resolve() == ROOT
    commit = None
    dirty = None
    if scoped:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                capture_output=True, text=True, check=False).stdout.strip() or None
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True))
    return {"python": platform.python_version(), "host_os": platform.platform(),
            "host_cpu_count": os.cpu_count(), "host_memory_bytes": mem, "machine": platform.machine(),
            "workspace_disk_total_bytes": disk.total, "workspace_disk_free_bytes": disk.free,
            "docker_engine": runtime["ServerVersion"], "docker_os": runtime["OperatingSystem"],
            "docker_cpu_count": runtime["NCPU"], "docker_memory_bytes": runtime["MemTotal"],
            "docker_compose": docker("compose", "version", "--short"), "git_commit": commit, "git_dirty": dirty}


def source_hashes() -> dict[str, str]:
    from hashlib import sha256
    paths = [ROOT / "requirements.txt"]
    for directory, suffixes in (("src", {".py"}), ("docker", {".yml", ".toml"})):
        paths.extend(path for path in (ROOT / directory).rglob("*") if path.suffix in suffixes)
    return {path.relative_to(ROOT).as_posix(): sha256(path.read_bytes()).hexdigest()
            for path in sorted(paths)}
