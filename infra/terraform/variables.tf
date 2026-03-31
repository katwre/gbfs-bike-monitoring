variable "aws_region" {
  type        = string
  default     = "eu-north-1"
  description = "AWS region"
}

variable "project_name" {
  type        = string
  default     = "gbfs-bike-monitoring"
  description = "Project name used for resource tags"
}

variable "instance_type" {
  type        = string
  default     = "t3.small"
  description = "EC2 instance type"
}

variable "key_name" {
  type        = string
  description = "Existing AWS EC2 key pair name for SSH"
}

variable "repo_url" {
  type        = string
  description = "Git repository URL for this project"
}

variable "allowed_cidrs" {
  type        = list(string)
  default     = ["0.0.0.0/0"]
  description = "CIDR blocks allowed to access exposed ports"
}

variable "existing_security_group_id" {
  type        = string
  default     = ""
  description = "Optional existing security group ID to use instead of creating a new one"
}

variable "enable_bootstrap" {
  type        = bool
  default     = true
  description = "Whether to run cloud-init bootstrap that installs Docker and starts the stack"
}
