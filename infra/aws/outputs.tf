output "public_ips" {
  value = { for name, node in aws_instance.node : name => node.public_ip }
}

output "private_ips" {
  value = { for name, node in aws_instance.node : name => node.private_ip }
}

output "ssh_loadgen" {
  value = "ssh -i <khoa-rieng> ubuntu@${aws_instance.node["loadgen"].public_ip}"
}

output "single_node_limits" {
  description = "Bien moi truong cho compose override tren VM MySQL/MongoDB."
  value = {
    FLASHSALE_AWS_CPUSET = "0-${var.single_node_cpus - 1}"
    FLASHSALE_AWS_MEM    = "${var.single_node_mem_gb}g"
  }
}

# Dan gia tri nay vao FLASHSALE_REMOTE_NODES tren VM loadgen (chi cac VM DBMS, khong gom loadgen/monitor).
output "flashsale_remote_nodes" {
  description = "JSON cho FLASHSALE_REMOTE_NODES: host noi bo, so vCPU va RAM cua tung VM DBMS."
  value = jsonencode({
    for name, node in local.nodes : name => {
      host         = aws_instance.node[name].private_ip
      cpus         = contains(["mysql", "mongo"], node.role) ? var.single_node_cpus : data.aws_ec2_instance_type.type[node.type].default_vcpus
      memory_bytes = (contains(["mysql", "mongo"], node.role) ? var.single_node_mem_gb * 1024 : data.aws_ec2_instance_type.type[node.type].memory_size) * 1024 * 1024
    } if contains(["mysql", "mongo", "pd", "tidb", "tikv"], node.role)
  })
}
