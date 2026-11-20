variable "region" {
  description = "Region duy nhat cho moi thi nghiem chinh."
  type        = string
  default     = "us-east-1"
}

variable "availability_zone" {
  description = "Mot AZ duy nhat (cung AZ voi VM TestTiDB cu)."
  type        = string
  default     = "us-east-1c"
}

variable "stack" {
  description = "Chi mot he DBMS tai mot thoi diem: mysql | mongo | tidb1 | tidb3 | none (chi may tai)."
  type        = string
  default     = "none"
  validation {
    condition     = contains(["none", "mysql", "mongo", "tidb1", "tidb3"], var.stack)
    error_message = "stack phai la none, mysql, mongo, tidb1 hoac tidb3."
  }
}

variable "ssh_public_key_path" {
  description = "Duong dan file .pub cua SSH key (khoa rieng khong bao gio vao repo)."
  type        = string
}

variable "allowed_ssh_cidr" {
  description = "CIDR duoc phep SSH, vi du 203.0.113.7/32 (IP cong cong cua ban)."
  type        = string
  validation {
    condition     = var.allowed_ssh_cidr != "0.0.0.0/0"
    error_message = "Khong mo SSH cho ca Internet."
  }
}

# Loai instance. Mac dinh theo goi y cua tai lieu (TiKV 2 vCPU, TiDB 4, PD 2, may tai 4).
# Tong vCPU/RAM cua cum TiDB (PD + TiDB + TiKV) phai bang MySQL va MongoDB; khong tinh may tai/monitor.
variable "tikv_instance_type" {
  type    = string
  default = "c6i.large"
}

variable "tidb_instance_type" {
  type    = string
  default = "c6i.xlarge"
}

variable "pd_instance_type" {
  type    = string
  default = "c6i.large"
}

# May tai Python: o 3000 IOPS can ~1,9 vCPU cho moi 1.000 TPS (do o 64 client); c6i.2xlarge (8 vCPU) du cho ~4.000 TPS,
# gap doi muc da do. Neu runner canh bao loadgen_cpu_*pct_of_limit thi dung c6i.4xlarge. Dat FLASHSALE_LOADGEN_CPUS bang so vCPU.
variable "loadgen_instance_type" {
  type    = string
  default = "c6i.2xlarge"
}

variable "monitor_instance_type" {
  type    = string
  default = "c6i.large"
}

# MySQL/MongoDB: khong co c6i 12 vCPU nen dung c6i.4xlarge (16 vCPU/32 GiB) roi gioi han bang
# cpuset va mem_limit trong compose override (tai lieu cho phep; ghi ro trong bao cao).
variable "single_node_instance_type" {
  type    = string
  default = "c6i.4xlarge"
}

variable "single_node_cpus" {
  description = "So loi gioi han cho MySQL/MongoDB (cpuset 0..n-1); 12 = tong vCPU cum 3 TiKV (3x2 + 4 + 2)."
  type        = number
  default     = 12
}

variable "single_node_mem_gb" {
  description = "Gioi han bo nho (GiB) container MySQL/MongoDB; 24 = tong RAM cum 3 TiKV."
  type        = number
  default     = 24
}

# EBS gp3 co dinh, GIONG NHAU cho moi he. Mac dinh 3000 IOPS / 125 MB/s (muc co ban, khong tinh them phi).
#
# LUU Y QUAN TRONG: instance cung co tran EBS rieng (AWS describe-instance-types, da kiem tra):
#   c6i.large   : 3.600 IOPS co ban, 650 Mbps  (toi da 40.000 IOPS chi trong dot ngan, tin chi tieu ~30 phut/ngay)
#   c6i.xlarge  : 6.000 IOPS co ban, 1.250 Mbps
#   c6i.2xlarge : 12.000 IOPS co ban, 2.500 Mbps
#   c6i.4xlarge : 20.000 IOPS co ban, 5.000 Mbps
# TiKV tren c6i.large (2 vCPU) khong the duy tri qua ~3.600 IOPS, nen dat volume 10.000 IOPS cho cum TiDB chi co
# tac dung trong dot burst roi bi giam, lam so do khong lap lai duoc. Vi vay mac dinh giu 3000 (duoi co ban cua moi loai
# instance). Chi tang IOPS cho thi nghiem "do nhay cua dia" tren MOT he (vi du MySQL tren c6i.2xlarge voi 10.000),
# va ghi ro la thi nghiem rieng, khong so sanh cheo giua cac he.
variable "data_volume_gb" {
  type    = number
  default = 100
}

variable "data_volume_iops" {
  type    = number
  default = 3000
  validation {
    condition     = var.data_volume_iops >= 3000 && var.data_volume_iops <= 16000
    error_message = "gp3: 3000-16000 IOPS."
  }
}

variable "data_volume_throughput" {
  type    = number
  default = 125
  validation {
    condition     = var.data_volume_throughput >= 125 && var.data_volume_throughput <= 1000
    error_message = "gp3: 125-1000 MB/s."
  }
}

variable "data_snapshot_id" {
  description = "Snapshot EBS chua du lieu TPC-C da nap cho stack mysql/mongo (rong = o trong)."
  type        = string
  default     = ""
}
