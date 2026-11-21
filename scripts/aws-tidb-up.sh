#!/usr/bin/env bash
# Dựng cụm TiDB bằng TiUP trên các VM do Terraform tạo (stack tidb1 hoặc tidb3) và chuẩn bị VM tải.
# Chạy trên MÁY CỦA BẠN sau `terraform apply` (cần ssh/scp và khóa riêng của key pair AWS):
#   terraform -chdir=infra/aws output -json > tf-out.json
#   scripts/aws-tidb-up.sh tf-out.json [đường-dẫn-khóa-riêng]
# Việc làm: chờ bootstrap xong, tạo khóa ssh tạm trên VM tải rồi cho phép nó vào các VM cụm (khóa riêng của bạn KHÔNG
# được chép lên VM), cài TiUP, check --apply, deploy, start, chép mã nguồn và viết env.sh cho chế độ remote.
# Cụm được đặt tên "flashsale"; chạy lại script sẽ báo lỗi nếu cụm đã tồn tại (dùng `tiup cluster destroy` trước).
set -euo pipefail
cd -- "$(dirname -- "$0")/.."

OUT="${1:?Thiếu đường dẫn tới đầu ra terraform (output -json)}"
KEY="${2:-$HOME/.ssh/flashsale_aws}"
SSH_OPTS=(-i "$KEY" -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15)
TIDB_VERSION="${TIDB_VERSION:-v8.5.7}"

say() { printf '%s %s\n' "$(date -u +%H:%M:%S)" "$*" >&2; }
json() { python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print($1)" "$OUT"; }

LOADGEN="$(json "d['public_ips']['value']['loadgen']")"
mapfile -t NODES < <(json "'\n'.join(k+' '+v for k,v in d['public_ips']['value'].items() if k!='loadgen')")
[[ ${#NODES[@]} -gt 0 ]] || { echo "Không có VM cụm TiDB trong $OUT (stack có phải tidb1/tidb3?)" >&2; exit 2; }
TOPOLOGY="$(ls infra/aws/generated/topology-tidb*.yaml | head -1)"

remote() { local host="$1"; shift; timeout "${REMOTE_TIMEOUT:-300}" ssh "${SSH_OPTS[@]}" "ubuntu@$host" "$@" </dev/null; }

wait_boot() {
    local host="$1"
    for _ in $(seq 1 40); do
        if remote "$host" 'test -f /var/lib/flashsale-bootstrap-done' 2>/dev/null; then return 0; fi
        sleep 8
    done
    echo "Bootstrap chưa xong trên $host" >&2
    return 1
}

say "Chờ bootstrap trên máy tải $LOADGEN và ${#NODES[@]} VM cụm"
wait_boot "$LOADGEN"
for line in "${NODES[@]}"; do wait_boot "${line#* }"; done

say "Tạo khóa ssh tạm trên máy tải và phân phối khóa công khai"
remote "$LOADGEN" 'test -f ~/.ssh/tiup_ed25519 || ssh-keygen -q -t ed25519 -N "" -f ~/.ssh/tiup_ed25519'
PUB="$(remote "$LOADGEN" 'cat ~/.ssh/tiup_ed25519.pub')"
for line in "${NODES[@]}"; do
    ip="${line#* }"
    remote "$ip" "grep -qF '$PUB' ~/.ssh/authorized_keys || echo '$PUB' >> ~/.ssh/authorized_keys"
done

say "Chép mã nguồn, topology và cài đặt Python trên máy tải"
git archive --format=tar.gz HEAD -o "${TMPDIR:-/tmp}/flashsale-src.tgz"
scp -q "${SSH_OPTS[@]}" "${TMPDIR:-/tmp}/flashsale-src.tgz" "ubuntu@$LOADGEN:/home/ubuntu/flashsale-src.tgz"
scp -q "${SSH_OPTS[@]}" "$TOPOLOGY" "ubuntu@$LOADGEN:/home/ubuntu/topology.yaml"
REMOTE_TIMEOUT=600 remote "$LOADGEN" 'mkdir -p DBMS && tar xzf flashsale-src.tgz -C DBMS && cd DBMS && python3 -m venv .venv && . .venv/bin/activate && pip install -q -r requirements.txt && pip install -q -e .'

say "Cài TiUP, check --apply, deploy $TIDB_VERSION và start (có thể mất vài phút)"
REMOTE_TIMEOUT=900 remote "$LOADGEN" "
set -e
export PATH=\$HOME/.tiup/bin:\$PATH
command -v tiup >/dev/null || (curl --proto '=https' --tlsv1.2 -sSf https://tiup-mirrors.pingcap.com/install.sh | sh >/dev/null 2>&1)
export PATH=\$HOME/.tiup/bin:\$PATH
tiup cluster check topology.yaml --user ubuntu -i ~/.ssh/tiup_ed25519 --apply --yes > tiup-check.out 2>&1 || true
tiup cluster deploy flashsale $TIDB_VERSION topology.yaml --user ubuntu -i ~/.ssh/tiup_ed25519 --yes > tiup-deploy.out 2>&1
tiup cluster start flashsale >> tiup-deploy.out 2>&1
tiup cluster display flashsale | grep -E 'tikv|pd|tidb' | awk '{print \$2, \$6}'
"

say "Viết env.sh (chế độ remote) trên máy tải"
python3 - "$OUT" <<'PY' | remote "$LOADGEN" 'cat > ~/DBMS/env.sh'
import json, sys
d = json.load(open(sys.argv[1]))
nodes = json.loads(d["flashsale_remote_nodes"]["value"])
tidb = nodes["tidb"]["host"]
cpus = sum(n["cpus"] for n in nodes.values())
memory = sum(n["memory_bytes"] for n in nodes.values())
tikv = sum(1 for k in nodes if k.startswith("tikv"))
print(f"export FLASHSALE_DB_HOST={tidb}")
print("export FLASHSALE_TIDB_PORT=4000")
print("export FLASHSALE_PD_PORT=2379")
print(f"export FLASHSALE_TIKV_COUNT={tikv}")
print("export FLASHSALE_REMOTE_NODES='" + json.dumps(nodes, separators=(",", ":")) + "'")
print(f"export FLASHSALE_REMOTE_BUDGET_CPUS={cpus}")
print(f"export FLASHSALE_REMOTE_BUDGET_MEMORY_BYTES={memory}")
print("export FLASHSALE_LOADGEN_CPUS=${FLASHSALE_LOADGEN_CPUS:-4}")
PY
say "Xong. Ssh vào máy tải: ssh -i $KEY ubuntu@$LOADGEN, rồi: cd DBMS && . .venv/bin/activate && . ./env.sh"
