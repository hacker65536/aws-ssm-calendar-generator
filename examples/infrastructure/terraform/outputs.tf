# Outputs for AWS SSM Change Calendar Holiday Schedule Management Tool

# VPC Outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = var.create_vpc ? module.vpc[0].vpc_id : var.existing_vpc_id
}

output "vpc_cidr" {
  description = "CIDR block of the VPC"
  value       = var.create_vpc ? module.vpc[0].vpc_cidr : var.existing_vpc_cidr
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = var.create_vpc ? module.vpc[0].private_subnet_ids : var.existing_private_subnet_ids
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = var.create_vpc ? module.vpc[0].public_subnet_ids : var.existing_public_subnet_ids
}

# ECS Outputs
output "ecs_cluster_id" {
  description = "ID of the ECS cluster"
  value       = aws_ecs_cluster.holiday_calendar_cluster.id
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.holiday_calendar_cluster.name
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.holiday_calendar_service.name
}

output "ecs_task_definition_arn" {
  description = "ARN of the ECS task definition"
  value       = aws_ecs_task_definition.holiday_calendar_task.arn
}

# Load Balancer Outputs
output "load_balancer_arn" {
  description = "ARN of the load balancer"
  value       = aws_lb.holiday_calendar_alb.arn
}

output "load_balancer_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.holiday_calendar_alb.dns_name
}

output "load_balancer_zone_id" {
  description = "Zone ID of the load balancer"
  value       = aws_lb.holiday_calendar_alb.zone_id
}

output "target_group_arn" {
  description = "ARN of the target group"
  value       = aws_lb_target_group.holiday_calendar_tg.arn
}

# Security Outputs
output "security_group_id" {
  description = "ID of the application security group"
  value       = aws_security_group.holiday_calendar_app.id
}

output "iam_role_arn" {
  description = "ARN of the IAM role"
  value       = aws_iam_role.holiday_calendar_role.arn
}

output "iam_role_name" {
  description = "Name of the IAM role"
  value       = aws_iam_role.holiday_calendar_role.name
}

# Storage Outputs
output "s3_bucket_name" {
  description = "Name of the S3 bucket"
  value       = aws_s3_bucket.holiday_calendar_storage.bucket
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.holiday_calendar_storage.arn
}

output "s3_bucket_domain_name" {
  description = "Domain name of the S3 bucket"
  value       = aws_s3_bucket.holiday_calendar_storage.bucket_domain_name
}

# Logging Outputs
output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.holiday_calendar_logs.name
}

output "cloudwatch_log_group_arn" {
  description = "ARN of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.holiday_calendar_logs.arn
}

# Lambda Outputs (if enabled)
output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = var.enable_scheduler ? aws_lambda_function.holiday_calendar_scheduler[0].function_name : null
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = var.enable_scheduler ? aws_lambda_function.holiday_calendar_scheduler[0].arn : null
}

# EventBridge Outputs (if enabled)
output "eventbridge_rule_name" {
  description = "Name of the EventBridge rule"
  value       = var.enable_scheduler ? aws_cloudwatch_event_rule.holiday_calendar_schedule[0].name : null
}

output "eventbridge_rule_arn" {
  description = "ARN of the EventBridge rule"
  value       = var.enable_scheduler ? aws_cloudwatch_event_rule.holiday_calendar_schedule[0].arn : null
}

# Auto Scaling Outputs
output "autoscaling_target_resource_id" {
  description = "Resource ID of the autoscaling target"
  value       = aws_appautoscaling_target.holiday_calendar_target.resource_id
}

output "autoscaling_policy_arn" {
  description = "ARN of the autoscaling policy"
  value       = aws_appautoscaling_policy.holiday_calendar_up.arn
}

# CloudWatch Alarms Outputs
output "cpu_alarm_name" {
  description = "Name of the CPU utilization alarm"
  value       = aws_cloudwatch_metric_alarm.high_cpu.alarm_name
}

output "memory_alarm_name" {
  description = "Name of the memory utilization alarm"
  value       = aws_cloudwatch_metric_alarm.high_memory.alarm_name
}

# Application URLs
output "application_url" {
  description = "URL of the application"
  value       = var.ssl_certificate_arn != "" ? "https://${aws_lb.holiday_calendar_alb.dns_name}" : "http://${aws_lb.holiday_calendar_alb.dns_name}"
}

output "health_check_url" {
  description = "Health check URL"
  value       = "${var.ssl_certificate_arn != "" ? "https" : "http"}://${aws_lb.holiday_calendar_alb.dns_name}/health"
}

# Environment Information
output "environment" {
  description = "Environment name"
  value       = var.environment
}

output "aws_region" {
  description = "AWS region"
  value       = data.aws_region.current.name
}

output "aws_account_id" {
  description = "AWS account ID"
  value       = data.aws_caller_identity.current.account_id
}

# Resource Names for External Reference
output "resource_names" {
  description = "Map of resource names for external reference"
  value = {
    cluster_name      = aws_ecs_cluster.holiday_calendar_cluster.name
    service_name      = aws_ecs_service.holiday_calendar_service.name
    task_family       = aws_ecs_task_definition.holiday_calendar_task.family
    load_balancer     = aws_lb.holiday_calendar_alb.name
    target_group      = aws_lb_target_group.holiday_calendar_tg.name
    security_group    = aws_security_group.holiday_calendar_app.name
    iam_role          = aws_iam_role.holiday_calendar_role.name
    s3_bucket         = aws_s3_bucket.holiday_calendar_storage.bucket
    log_group         = aws_cloudwatch_log_group.holiday_calendar_logs.name
    lambda_function   = var.enable_scheduler ? aws_lambda_function.holiday_calendar_scheduler[0].function_name : null
    eventbridge_rule  = var.enable_scheduler ? aws_cloudwatch_event_rule.holiday_calendar_schedule[0].name : null
  }
}

# Deployment Information
output "deployment_info" {
  description = "Deployment information"
  value = {
    project_name    = var.project_name
    environment     = var.environment
    aws_region      = data.aws_region.current.name
    container_image = var.container_image
    desired_count   = var.desired_count
    task_cpu        = var.task_cpu
    task_memory     = var.task_memory
    min_capacity    = var.min_capacity
    max_capacity    = var.max_capacity
  }
}

# Monitoring Endpoints
output "monitoring_endpoints" {
  description = "Monitoring and observability endpoints"
  value = {
    cloudwatch_logs = "https://console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#logsV2:log-groups/log-group/${replace(aws_cloudwatch_log_group.holiday_calendar_logs.name, "/", "$252F")}"
    ecs_service     = "https://console.aws.amazon.com/ecs/home?region=${data.aws_region.current.name}#/clusters/${aws_ecs_cluster.holiday_calendar_cluster.name}/services/${aws_ecs_service.holiday_calendar_service.name}/details"
    load_balancer   = "https://console.aws.amazon.com/ec2/v2/home?region=${data.aws_region.current.name}#LoadBalancers:search=${aws_lb.holiday_calendar_alb.name}"
    s3_bucket       = "https://console.aws.amazon.com/s3/buckets/${aws_s3_bucket.holiday_calendar_storage.bucket}"
  }
}

# Connection Information
output "connection_info" {
  description = "Connection information for the application"
  value = {
    endpoint    = aws_lb.holiday_calendar_alb.dns_name
    port        = var.ssl_certificate_arn != "" ? 443 : 80
    protocol    = var.ssl_certificate_arn != "" ? "https" : "http"
    health_path = "/health"
  }
  sensitive = false
}

# Cost Optimization Information
output "cost_optimization" {
  description = "Cost optimization information"
  value = {
    spot_instances_enabled = var.enable_spot_instances
    auto_scaling_enabled   = true
    min_capacity          = var.min_capacity
    max_capacity          = var.max_capacity
    log_retention_days    = var.log_retention_days
  }
}

# Security Information
output "security_info" {
  description = "Security configuration information"
  value = {
    encryption_at_rest     = var.enable_encryption_at_rest
    encryption_in_transit  = var.enable_encryption_in_transit
    ssl_enabled           = var.ssl_certificate_arn != ""
    vpc_enabled           = true
    private_subnets       = true
    security_groups       = [aws_security_group.holiday_calendar_app.id]
  }
}