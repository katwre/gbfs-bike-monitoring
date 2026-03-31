terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  security_group_id = var.existing_security_group_id != "" ? var.existing_security_group_id : aws_security_group.gbfs[0].id
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_ami" "ubuntu" {
  most_recent = true

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["099720109477"]
}

resource "aws_security_group" "gbfs" {
  count       = var.existing_security_group_id == "" ? 1 : 0
  name_prefix = "${var.project_name}-sg-"
  description = "Ingress for GBFS project services"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidrs
  }

  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidrs
  }

  ingress {
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidrs
  }

  ingress {
    from_port   = 9001
    to_port     = 9001
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidrs
  }
}

resource "aws_instance" "gbfs" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  subnet_id                   = data.aws_subnets.default.ids[0]
  vpc_security_group_ids      = [local.security_group_id]
  associate_public_ip_address = true
  key_name                    = var.key_name

  user_data = var.enable_bootstrap ? templatefile("${path.module}/user_data.sh.tftpl", {
    repo_url = var.repo_url
  }) : null

  root_block_device {
    volume_size           = 30
    volume_type           = "gp3"
    delete_on_termination = true
  }
}
