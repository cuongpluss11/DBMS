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
import re
from uuid import uuid4

from flashsale.adapters.base import Endpoint, open_adapter

ROOT = Path(__file__).resolve().parents[2]
ENGINES = ("mysql", "mongo", "tidb")
# Ngân sách container chung cho MỌI hệ (mục 2.1: cùng tổng CPU/RAM). Xem docs/assumptions.md.
BUDGET_CPUS = 8
BUDGET_MEMORY_BYTES = 16 * 1024 ** 3
DEFAULT_PORTS = {"mysql": 13306, "mongo": 27018, "tidb": 14000, "pd": 12379}


def setting(key: str, default: str | None = None) -> str | None:
    """Biến môi trường, rồi `.env` (không chứa bí mật), rồi mặc định."""
    if key in os.environ:
        return os.environ[key]
    env_file = ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, sep, value = line.partition("=")
            if sep and name.strip() == key:
                return value.strip().strip('"').strip("'")
    return default


def port(service: str) -> int:
    return int(setting(f"FLASHSALE_{service.upper()}_PORT", str(DEFAULT_PORTS[service])))


def db_host() -> str:
    """Địa chỉ DBMS. Mặc định 127.0.0.1 (Docker cục bộ); trên AWS là IP nội bộ của VM DBMS."""
    return setting("FLASHSALE_DB_HOST", "127.0.0.1")


def endpoint(engine: str, database: str | None = None) -> Endpoint:
    return Endpoint(engine, port(engine), database or f"flashsale_{uuid4().hex}", db_host())


# --- Chế độ remote (AWS): DBMS chạy trên VM riêng, script tải chạy trên VM khác. ---
# FLASHSALE_REMOTE_NODES là JSON: {"mysql": {"host": "10.20.1.5", "cpus": 12, "memory_bytes": 25769803776}, ...}
# Mỗi nút có node_exporter ở cổng 9100 (xem infra/aws). Ngân sách DBMS (tổng cpus/memory) mặc định 12 vCPU / 24 GiB.
NODE_EXPORTER_PORT = 9100
REMOTE_BUDGET_CPUS = 12
REMOTE_BUDGET_MEMORY_BYTES = 24 * 1024 ** 3


def remote_nodes() -> dict[str, dict] | None:
    raw = setting("FLASHSALE_REMOTE_NODES")
    if not raw:
        return None
    nodes = json.loads(raw)
    for name, node in nodes.items():
        if not {"host", "cpus", "memory_bytes"} <= set(node):
            raise ValueError(f"FLASHSALE_REMOTE_NODES[{name}] cần host, cpus, memory_bytes")
    return nodes


def remote_budget() -> tuple[float, int]:
    return (float(setting("FLASHSALE_REMOTE_BUDGET_CPUS", str(REMOTE_BUDGET_CPUS))),
            int(setting("FLASHSALE_REMOTE_BUDGET_MEMORY_BYTES", str(REMOTE_BUDGET_MEMORY_BYTES))))


CPU_LINE = re.compile(r'^node_cpu_seconds_total\{cpu="[^"]*",mode="([^"]+)"\} ([0-9.eE+-]+)$')


def parse_node_cpu(text: str) -> tuple[float, float]:
    """Trả (tổng giây CPU bận, tổng giây mọi mode). Bận = mọi mode trừ idle và iowait."""
    busy = total = 0.0
    for line in text.splitlines():
        match = CPU_LINE.match(line)
        if match:
            value = float(match.group(2))
            total += value
            if match.group(1) not in ("idle", "iowait"):
                busy += value
    return busy, total


def node_cpu_seconds(host: str) -> tuple[float, float]:
    with urlopen(f"http://{host}:{NODE_EXPORTER_PORT}/metrics", timeout=3) as response:
        return parse_node_cpu(response.read().decode())


def tcp_rtt_ms(host: str, port: int, samples: int = 10) -> dict | None:
    """Thời gian kết nối TCP (xấp xỉ một vòng mạng) tới DBMS; trung vị, min, max theo ms.
    Chỉ có nghĩa khi DBMS ở máy khác; trả None nếu không kết nối được."""
    import socket
    import statistics
    values = []
    for _ in range(samples):
        started = time.perf_counter()
        try:
            with socket.create_connection((host, port), timeout=3):
                values.append(1000 * (time.perf_counter() - started))
        except OSError:
            return None
    return {"median": statistics.median(values), "min": min(values), "max": max(values), "samples": samples}


def cpu_sampler(limits: dict[str, dict]):
    """Hàm lấy CPU% (100% = một lõi) từng nút/container. Docker: docker stats; remote: delta node_exporter.
    Ở chế độ remote có thêm khóa "loadgen" (node_exporter của chính máy tải) để kiểm tra nút thắt của script tải."""
    nodes = remote_nodes()
    if nodes is None:
        return lambda: docker_cpu(limits)
    hosts = {name: value["host"] for name, value in limits.items()}
    hosts["loadgen"] = setting("FLASHSALE_LOADGEN_EXPORTER_HOST", "127.0.0.1")
    previous: dict[str, tuple[float, float]] = {}

    def sample() -> dict[str, float]:
        values = {}
        now = time.monotonic()
        for name, host in hosts.items():
            try:
                busy, _ = node_cpu_seconds(host)
            except Exception:
                continue
            if name in previous:
                busy0, t0 = previous[name]
                values[name] = 100 * (busy - busy0) / max(now - t0, 1e-9)
            previous[name] = (busy, now)
        return values

    return sample


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
    if remote_nodes() is not None:
        return {engine: [] for engine in ENGINES}  # DBMS remote do Terraform/TiUP/compose trên VM quản lý
    running = {}
    for engine in ENGINES:
        output = docker("ps", "--quiet", "--filter", f"label=com.docker.compose.project=flashsale-{engine}")
        running[engine] = output.splitlines()
    return running


def enforce_one(engine: str, *, must_run: bool = True) -> None:
    if remote_nodes() is not None:
        return  # Terraform chỉ dựng một stack tại một thời điểm (biến stack)
    running = active_engines()
    others = [name for name, containers in running.items() if name != engine and containers]
    if others:
        raise RuntimeError(f"Hãy dừng DBMS dự án đang chạy: {', '.join(others)}")
    if must_run and not running[engine]:
        raise RuntimeError(f"{engine} chưa chạy")


def pd_url() -> str:
    nodes = remote_nodes()
    host = nodes["pd"]["host"] if nodes and "pd" in nodes else db_host()
    return f"http://{host}:{port('pd')}/pd/api/v1"


def pd_status() -> dict:
    base = pd_url()
    with urlopen(base + "/stores", timeout=2) as response:
        stores = json.load(response)["stores"]
    with urlopen(base + "/config/replicate", timeout=2) as response:
        replica = json.load(response)
    live = [entry["store"] for entry in stores if entry["store"]["state_name"] == "Up"]
    expected = int(setting("FLASHSALE_TIKV_COUNT", "3"))
    # Lượt chính: đúng 1 bản sao. Nhóm R (docs/experiment-2.3.md) đặt FLASHSALE_TIDB_REPLICAS=3 một cách tường minh;
    # giá trị thật của PD luôn được ghi vào manifest (`max_replicas`), không suy từ biến môi trường.
    allowed = int(setting("FLASHSALE_TIDB_REPLICAS", "1"))
    if len(live) != expected or replica.get("max-replicas") != allowed:
        raise RuntimeError(f"TiDB cần {expected} TiKV Up và max-replicas={allowed}. Hiện có {len(live)} store, {replica}")
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
    if remote_nodes() is not None:
        raise RuntimeError("Chế độ remote: khởi động DBMS bằng Terraform/TiUP/compose trên VM (infra/aws/README.md)")
    enforce_one(engine, must_run=False)
    args = ["up", "-d", "--wait", "--wait-timeout", "150"]
    compose(engine, *args, timeout=240, capture=False)
    return ready(engine)


def stop(engine: str) -> None:
    if remote_nodes() is not None:
        raise RuntimeError("Chế độ remote: dừng DBMS bằng Terraform/TiUP/compose trên VM (infra/aws/README.md)")
    compose(engine, "stop", timeout=180, capture=False)


def remote_limits(engine: str, nodes: dict[str, dict]) -> dict[str, dict]:
    """Giới hạn tài nguyên của các VM DBMS (không gồm máy tải/monitor) lấy từ FLASHSALE_REMOTE_NODES."""
    result = {name: {"id": None, "image": None, "image_id": None, "repo_digests": None, "remote": True,
                     "host": node["host"], "cpus": float(node["cpus"]), "memory_bytes": int(node["memory_bytes"])}
              for name, node in nodes.items()}
    budget_cpus, budget_memory = remote_budget()
    if sum(item["cpus"] for item in result.values()) != budget_cpus or sum(
            item["memory_bytes"] for item in result.values()) != budget_memory:
        raise RuntimeError(f"Các nút DBMS khác ngân sách {budget_cpus} vCPU / {budget_memory // 1024 ** 3} GiB; "
                           "đặt FLASHSALE_REMOTE_BUDGET_* nếu chủ ý (ví dụ cụm 1 TiKV của 2.3)")
    return result


def container_limits(engine: str) -> dict[str, dict]:
    nodes = remote_nodes()
    if nodes is not None:
        return remote_limits(engine, nodes)
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
    nodes = remote_nodes()
    try:
        runtime = json.loads(docker("info", "--format", "{{json .}}"))
        compose_version = docker("compose", "version", "--short")
    except (OSError, subprocess.SubprocessError):
        if nodes is None:
            raise
        runtime = {"ServerVersion": None, "OperatingSystem": None, "NCPU": None, "MemTotal": None}
        compose_version = None
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
            "docker_compose": compose_version, "git_commit": commit, "git_dirty": dirty,
            "mode": "remote" if nodes is not None else "docker", "db_host": db_host(),
            "remote_nodes": nodes}


def source_hashes() -> dict[str, str]:
    from hashlib import sha256
    paths = [ROOT / "requirements.txt"]
    for directory, suffixes in (("src", {".py"}), ("docker", {".yml", ".toml"})):
        paths.extend(path for path in (ROOT / directory).rglob("*") if path.suffix in suffixes)
    return {path.relative_to(ROOT).as_posix(): sha256(path.read_bytes()).hexdigest()
            for path in sorted(paths)}
