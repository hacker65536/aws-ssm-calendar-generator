# Variables for AWS SSM Change Calendar Holiday Schedule Management Tool

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "holiday-calendar"
}

variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "owner" {
  description = "Owner of the resources"
  type        = string
  default     = "platform-team"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-1"
}

# VPC Configuration
variable "create_vpc" {
  description = "Whether to create a new VPC"
  type        = bool
  default     = true
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["ap-northeast-1a", "ap-northeast-1c", "ap-northeast-1d"]
}

variable "existing_vpc_id" {
  description = "ID of existing VPC (if create_vpc is false)"
  type        = string
  default     = ""
}

variable "existing_vpc_cidr" {
  description = "CIDR of existing VPC (if create_vpc is false)"
  type        = string
  default     = ""
}

variable "existing_private_subnet_ids" {
  description = "List of existing private subnet IDs (if create_vpc is false)"
  type        = list(string)
  default     = []
}

variable "existing_public_subnet_ids" {
  description = "List of existing public subnet IDs (if create_vpc is false)"
  type        = list(string)
  default     = []
}

# ECS Configuration
variable "container_image" {
  description = "Docker image for the application"
  type        = string
  default     = "ghcr.io/your-org/holiday-calendar:latest"
}

variable "task_cpu" {
  description = "CPU units for the task (1024 = 1 vCPU)"
  type        = number
  default     = 512
  validation {
    condition     = contains([256, 512, 1024, 2048, 4096], var.task_cpu)
    error_message = "Task CPU must be one of: 256, 512, 1024, 2048, 4096."
  }
}

variable "task_memory" {
  description = "Memory for the task in MB"
  type        = number
  default     = 1024
  validation {
    condition = var.task_memory >= 512 && var.task_memory <= 30720
    error_message = "Task memory must be between 512 and 30720 MB."
  }
}

variable "desired_count" {
  description = "Desired number of tasks"
  type        = number
  default     = 2
  validation {
    condition     = var.desired_count >= 1 && var.desired_count <= 100
    error_message = "Desired count must be between 1 and 100."
  }
}

# Auto Scaling Configuration
variable "min_capacity" {
  description = "Minimum number of tasks"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Maximum number of tasks"
  type        = number
  default     = 10
}

# Load Balancer Configuration
variable "ssl_certificate_arn" {
  description = "ARN of SSL certificate for HTTPS listener"
  type        = string
  default     = ""
}

variable "enable_deletion_protection" {
  description = "Enable deletion protection for load balancer"
  type        = bool
  default     = true
}

# Scheduler Configuration
variable "enable_scheduler" {
  description = "Enable scheduled Lambda function"
  type        = bool
  default     = true
}

variable "schedule_expression" {
  description = "Schedule expression for EventBridge rule (cron or rate)"
  type        = string
  default     = "cron(0 2 * * ? *)"  # Daily at 2 AM UTC
  validation {
    condition = can(regex("^(cron|rate)\\(.*\\)$", var.schedule_expression))
    error_message = "Schedule expression must be a valid cron or rate expression."
  }
}

# Logging Configuration
variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
  validation {
    condition = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.log_retention_days)
    error_message = "Log retention days must be a valid CloudWatch retention period."
  }
}

# Monitoring Configuration
variable "sns_topic_arn" {
  description = "SNS topic ARN for CloudWatch alarms"
  type        = string
  default     = ""
}

variable "enable_detailed_monitoring" {
  description = "Enable detailed CloudWatch monitoring"
  type        = bool
  default     = false
}

# Security Configuration
variable "allowed_cidr_blocks" {
  description = "List of CIDR blocks allowed to access the application"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "enable_waf" {
  description = "Enable AWS WAF for the load balancer"
  type        = bool
  default     = false
}

# Backup Configuration
variable "enable_backup" {
  description = "Enable automated backups"
  type        = bool
  default     = true
}

variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 30
}

# Database Configuration (for future use)
variable "enable_database" {
  description = "Enable RDS database"
  type        = bool
  default     = false
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

variable "db_engine_version" {
  description = "RDS engine version"
  type        = string
  default     = "15.4"
}

# Cache Configuration
variable "enable_redis" {
  description = "Enable ElastiCache Redis"
  type        = bool
  default     = false
}

variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_num_cache_nodes" {
  description = "Number of cache nodes"
  type        = number
  default     = 1
}

# Feature Flags
variable "feature_flags" {
  description = "Feature flags for the application"
  type        = map(bool)
  default = {
    enable_api_v2           = false
    enable_metrics_export   = true
    enable_debug_logging    = false
    enable_performance_mode = false
  }
}

# Cost Optimization
variable "enable_spot_instances" {
  description = "Use Spot instances for ECS tasks"
  type        = bool
  default     = false
}

variable "spot_allocation_strategy" {
  description = "Spot allocation strategy"
  type        = string
  default     = "diversified"
  validation {
    condition     = contains(["diversified", "spot"], var.spot_allocation_strategy)
    error_message = "Spot allocation strategy must be 'diversified' or 'spot'."
  }
}

# Multi-Region Configuration
variable "enable_multi_region" {
  description = "Enable multi-region deployment"
  type        = bool
  default     = false
}

variable "secondary_regions" {
  description = "List of secondary regions for multi-region deployment"
  type        = list(string)
  default     = ["us-east-1", "eu-west-1"]
}

# Compliance and Security
variable "enable_encryption_at_rest" {
  description = "Enable encryption at rest for all storage"
  type        = bool
  default     = true
}

variable "enable_encryption_in_transit" {
  description = "Enable encryption in transit"
  type        = bool
  default     = true
}

variable "compliance_framework" {
  description = "Compliance framework to adhere to"
  type        = string
  default     = "none"
  validation {
    condition     = contains(["none", "soc2", "pci", "hipaa", "gdpr"], var.compliance_framework)
    error_message = "Compliance framework must be one of: none, soc2, pci, hipaa, gdpr."
  }
}

# Development and Testing
variable "enable_debug_mode" {
  description = "Enable debug mode for development"
  type        = bool
  default     = false
}

variable "enable_test_data" {
  description = "Enable test data generation"
  type        = bool
  default     = false
}

# Custom Domain Configuration
variable "domain_name" {
  description = "Custom domain name for the application"
  type        = string
  default     = ""
}

variable "hosted_zone_id" {
  description = "Route53 hosted zone ID for the domain"
  type        = string
  default     = ""
}

# Notification Configuration
variable "notification_endpoints" {
  description = "List of notification endpoints"
  type = object({
    email = optional(list(string), [])
    slack = optional(string, "")
    teams = optional(string, "")
  })
  default = {
    email = []
    slack = ""
    teams = ""
  }
}

# Resource Tagging
variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# Performance Configuration
variable "performance_mode" {
  description = "Performance mode configuration"
  type = object({
    enable_caching     = optional(bool, true)
    cache_ttl_seconds  = optional(number, 3600)
    enable_compression = optional(bool, true)
    max_connections    = optional(number, 1000)
  })
  default = {
    enable_caching     = true
    cache_ttl_seconds  = 3600
    enable_compression = true
    max_connections    = 1000
  }
}