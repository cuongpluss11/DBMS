data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }
  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

resource "aws_vpc" "main" {
  cidr_block           = "10.20.0.0/16"
  enable_dns_hostnames = true
  tags                 = { Name = "flashsale" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
}

resource "aws_subnet" "main" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.20.1.0/24"
  availability_zone       = var.availability_zone
  map_public_ip_on_launch = true
  tags                    = { Name = "flashsale-${var.availability_zone}" }
}

resource "aws_route_table" "main" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
}

resource "aws_route_table_association" "main" {
  subnet_id      = aws_subnet.main.id
  route_table_id = aws_route_table.main.id
}

# Cluster placement group: do tre mang on dinh giua cac VM (cung AZ).
resource "aws_placement_group" "cluster" {
  name     = "flashsale-cluster"
  strategy = "cluster"
}

resource "aws_security_group" "main" {
  name_prefix = "flashsale-"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "SSH tu IP cua ban"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }
  ingress {
    description = "Noi bo cum"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    self        = true
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_key_pair" "main" {
  key_name_prefix = "flashsale-"
  public_key      = file(pathexpand(var.ssh_public_key_path))
}

locals {
  tikv_count = var.stack == "tidb3" ? 3 : (var.stack == "tidb1" ? 1 : 0)

  # role: loadgen | mysql | mongo | pd | tidb | tikv | monitor ; data: co o du lieu EBS rieng hay khong
  nodes = merge(
    { loadgen = { role = "loadgen", type = var.loadgen_instance_type, data = false } },
    var.stack == "mysql" ? { mysql = { role = "mysql", type = var.single_node_instance_type, data = true } } : {},
    var.stack == "mongo" ? { mongo = { role = "mongo", type = var.single_node_instance_type, data = true } } : {},
    local.tikv_count > 0 ? {
      pd      = { role = "pd", type = var.pd_instance_type, data = true }
      tidb    = { role = "tidb", type = var.tidb_instance_type, data = false }
      monitor = { role = "monitor", type = var.monitor_instance_type, data = false }
    } : {},
    { for i in range(local.tikv_count) :
      "tikv${i + 1}" => { role = "tikv", type = var.tikv_instance_type, data = true }
    },
  )
  data_nodes = { for name, node in local.nodes : name => node if node.data }
}

data "aws_ec2_instance_type" "type" {
  for_each      = toset([for node in local.nodes : node.type])
  instance_type = each.key
}

resource "aws_instance" "node" {
  for_each = local.nodes

  ami                         = data.aws_ami.ubuntu.id
  instance_type               = each.value.type # chi dung loai hieu nang co dinh, khong burstable (t3/t4g)
  subnet_id                   = aws_subnet.main.id
  vpc_security_group_ids      = [aws_security_group.main.id]
  key_name                    = aws_key_pair.main.key_name
  placement_group             = aws_placement_group.cluster.id
  monitoring                  = true
  associate_public_ip_address = true

  root_block_device {
    volume_type = "gp3"
    volume_size = 30
  }

  user_data = templatefile("${path.module}/scripts/bootstrap.sh.tftpl", {
    role     = each.value.role
    has_data = each.value.data
  })

  tags = { Name = "flashsale-${each.key}", Role = each.value.role }

  # Canonical phat hanh AMI moi thuong xuyen; "most_recent" se doi AMI giua cac lan plan va doi tuong chay thanh THAY THE
  # VM dang do (mat du lieu va moi truong). Ghim AMI da dung cho den khi destroy.
  lifecycle {
    ignore_changes = [ami, user_data]
  }
}

resource "aws_ebs_volume" "data" {
  for_each = local.data_nodes

  availability_zone = var.availability_zone
  type              = "gp3"
  size              = var.data_volume_gb
  iops              = var.data_volume_iops
  throughput        = var.data_volume_throughput
  # Snapshot chi gan cho VM du lieu cua stack mysql/mongo; cum TiDB nap lai bang TiUP + loader.
  snapshot_id = (var.data_snapshot_id != "" && contains(["mysql", "mongo"], each.key)) ? var.data_snapshot_id : null
  tags        = { Name = "flashsale-${each.key}-data" }
}

resource "aws_volume_attachment" "data" {
  for_each    = local.data_nodes
  device_name = "/dev/sdf"
  volume_id   = aws_ebs_volume.data[each.key].id
  instance_id = aws_instance.node[each.key].id
}

# Topology TiUP duoc render san voi IP noi bo that.
resource "local_file" "topology" {
  count    = local.tikv_count > 0 ? 1 : 0
  filename = "${path.module}/generated/topology-${var.stack}.yaml"
  content = templatefile("${path.module}/topology.yaml.tftpl", {
    pd      = aws_instance.node["pd"].private_ip
    tidb    = aws_instance.node["tidb"].private_ip
    monitor = aws_instance.node["monitor"].private_ip
    tikv    = [for i in range(local.tikv_count) : aws_instance.node["tikv${i + 1}"].private_ip]
  })
}
