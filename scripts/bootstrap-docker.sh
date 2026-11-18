#!/usr/bin/env bash
set -euo pipefail
if [[ ${1:-} != --install || $# != 1 || $EUID != 0 ]]; then
    printf 'Chạy rõ quyền quản trị bằng sudo bash scripts/bootstrap-docker.sh --install\n' >&2
    exit 2
fi
source /etc/os-release
if [[ $ID != ubuntu || $VERSION_ID != 24.04 || $(uname -m) != x86_64 ]]; then
    printf 'Script bootstrap hỗ trợ Ubuntu 24.04 LTS x86_64.\n' >&2
    exit 1
fi
apt-get update
apt-get install -y ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl --fail --silent --show-error --location https://download.docker.com/linux/ubuntu/gpg \
    --output /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
cat >/etc/apt/sources.list.d/docker.sources <<'SOURCES'
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: noble
Components: stable
Architectures: amd64
Signed-By: /etc/apt/keyrings/docker.asc
SOURCES
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
docker version
docker compose version
