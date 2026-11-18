#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."

if [[ ${1:-} == --vm ]]; then
    source /etc/os-release
    if [[ $ID != ubuntu || $VERSION_ID != 24.04 || $(uname -m) != x86_64 ]]; then
        printf 'Môi trường mục tiêu là Ubuntu 24.04 LTS x86_64.\n' >&2
        exit 1
    fi
    command -v python3.12 >/dev/null
    python3.12 --version
    docker version --format '{{.Server.Os}}/{{.Server.Arch}} {{.Server.Version}}'
    docker compose version --short
    docker compose up --help | awk '/--wait-timeout/{found=1} END{exit !found}'
    cpus=$(nproc)
    memory_kib=$(awk '/^MemTotal:/{print $2}' /proc/meminfo)
    disk_kib=$(df -Pk . | awk 'NR==2{print $4}')
    printf 'VM CPU=%s RAM_KiB=%s workspace_free_KiB=%s\n' "$cpus" "$memory_kib" "$disk_kib"
    if (( cpus < 4 || memory_kib < 7 * 1024 * 1024 || disk_kib < 10 * 1024 * 1024 )); then
        printf 'Tài nguyên dưới ngưỡng kiểm tra: 4 CPU, 7 GiB RAM báo cáo và 10 GiB đĩa rảnh.\n' >&2
        exit 1
    fi
    docker_root=$(docker info --format '{{.DockerRootDir}}')
    if [[ -d $docker_root ]]; then
        df -h -- "$docker_root"
    fi
else
    .venv/bin/flashsale doctor
fi
