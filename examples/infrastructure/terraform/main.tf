# AWS SSM Change Calendar Holiday Schedule Management Tool
# Terraform Infrastructure Configuration

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
  }

  backend "s3" {
    # Configure your S3 backend
    # bucket = "your-terraform-state-bucket"
    # key    = "holiday-calendar/terraform.tfstate"
    # region = "us-east-1"
  }
}

# Configure the AWS Provider
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "holiday-calendar"
      Environment = var.environment
      ManagedBy   = "terraform"
      Owner       = var.owner
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Random suffix for unique resource names
resource "random_id" "suffix" {
  byte_length = 4
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Owner       = var.owner
  }
}

# VPC and Networking (if creating new VPC)
module "vpc" {
  source = "./modules/vpc"
  count  = var.create_vpc ? 1 : 0

  name_prefix         = local.name_prefix
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  
  tags = local.common_tags
}

# Security Groups
resource "aws_security_group" "holiday_calendar_app" {
  name_prefix = "${local.name_prefix}-app-"
  vpc_id      = var.create_vpc ? module.vpc[0].vpc_id : var.existing_vpc_id
  description = "Security group for Holiday Calendar application"

  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = [var.create_vpc ? module.vpc[0].vpc_cidr : var.existing_vpc_cidr]
    description = "Application port"
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-app-sg"
  })
}

# IAM Role for Holiday Calendar Application
resource "aws_iam_role" "holiday_calendar_role" {
  name = "${local.name_prefix}-app-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = [
            "ecs-tasks.amazonaws.com",
            "lambda.amazonaws.com"
          ]
        }
      }
    ]
  })

  tags = local.common_tags
}

# IAM Policy for SSM Change Calendar operations
resource "aws_iam_policy" "holiday_calendar_policy" {
  name        = "${local.name_prefix}-app-policy"
  description = "Policy for Holiday Calendar application"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetDocument",
          "ssm:ListDocuments",
          "ssm:GetCalendarState",
          "ssm:CreateDocument",
          "ssm:UpdateDocument",
          "ssm:DeleteDocument",
          "ssm:AddTagsToResource",
          "ssm:RemoveTagsFromResource",
          "ssm:ListTagsForResource"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${aws_s3_bucket.holiday_calendar_storage.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.holiday_calendar_storage.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*"
      }
    ]
  })

  tags = local.common_tags
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "holiday_calendar_policy_attachment" {
  role       = aws_iam_role.holiday_calendar_role.name
  policy_arn = aws_iam_policy.holiday_calendar_policy.arn
}

# S3 Bucket for storage
resource "aws_s3_bucket" "holiday_calendar_storage" {
  bucket = "${local.name_prefix}-storage-${random_id.suffix.hex}"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-storage"
  })
}

# S3 Bucket versioning
resource "aws_s3_bucket_versioning" "holiday_calendar_storage_versioning" {
  bucket = aws_s3_bucket.holiday_calendar_storage.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Bucket encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "holiday_calendar_storage_encryption" {
  bucket = aws_s3_bucket.holiday_calendar_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 Bucket public access block
resource "aws_s3_bucket_public_access_block" "holiday_calendar_storage_pab" {
  bucket = aws_s3_bucket.holiday_calendar_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "holiday_calendar_logs" {
  name              = "/aws/holiday-calendar/${var.environment}"
  retention_in_days = var.log_retention_days

  tags = local.common_tags
}

# ECS Cluster
resource "aws_ecs_cluster" "holiday_calendar_cluster" {
  name = "${local.name_prefix}-cluster"

  configuration {
    execute_command_configuration {
      logging = "OVERRIDE"
      log_configuration {
        cloud_watch_log_group_name = aws_cloudwatch_log_group.holiday_calendar_logs.name
      }
    }
  }

  tags = local.common_tags
}

# ECS Task Definition
resource "aws_ecs_task_definition" "holiday_calendar_task" {
  family                   = "${local.name_prefix}-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.holiday_calendar_role.arn
  task_role_arn           = aws_iam_role.holiday_calendar_role.arn

  container_definitions = jsonencode([
    {
      name  = "holiday-calendar-app"
      image = var.container_image
      
      portMappings = [
        {
          containerPort = 8080
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "AWS_DEFAULT_REGION"
          value = data.aws_region.current.name
        },
        {
          name  = "ENVIRONMENT"
          value = var.environment
        },
        {
          name  = "S3_BUCKET"
          value = aws_s3_bucket.holiday_calendar_storage.bucket
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.holiday_calendar_logs.name
          awslogs-region        = data.aws_region.current.name
          awslogs-stream-prefix = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  tags = local.common_tags
}

# ECS Service
resource "aws_ecs_service" "holiday_calendar_service" {
  name            = "${local.name_prefix}-service"
  cluster         = aws_ecs_cluster.holiday_calendar_cluster.id
  task_definition = aws_ecs_task_definition.holiday_calendar_task.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.create_vpc ? module.vpc[0].private_subnet_ids : var.existing_private_subnet_ids
    security_groups  = [aws_security_group.holiday_calendar_app.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.holiday_calendar_tg.arn
    container_name   = "holiday-calendar-app"
    container_port   = 8080
  }

  depends_on = [aws_lb_listener.holiday_calendar_listener]

  tags = local.common_tags
}

# Application Load Balancer
resource "aws_lb" "holiday_calendar_alb" {
  name               = "${local.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.holiday_calendar_app.id]
  subnets            = var.create_vpc ? module.vpc[0].public_subnet_ids : var.existing_public_subnet_ids

  enable_deletion_protection = var.enable_deletion_protection

  tags = local.common_tags
}

# Target Group
resource "aws_lb_target_group" "holiday_calendar_tg" {
  name        = "${local.name_prefix}-tg"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = var.create_vpc ? module.vpc[0].vpc_id : var.existing_vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = local.common_tags
}

# ALB Listener
resource "aws_lb_listener" "holiday_calendar_listener" {
  load_balancer_arn = aws_lb.holiday_calendar_alb.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = var.ssl_certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.holiday_calendar_tg.arn
  }
}

# Auto Scaling
resource "aws_appautoscaling_target" "holiday_calendar_target" {
  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${aws_ecs_cluster.holiday_calendar_cluster.name}/${aws_ecs_service.holiday_calendar_service.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "holiday_calendar_up" {
  name               = "${local.name_prefix}-scale-up"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.holiday_calendar_target.resource_id
  scalable_dimension = aws_appautoscaling_target.holiday_calendar_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.holiday_calendar_target.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}

# Lambda function for scheduled tasks
resource "aws_lambda_function" "holiday_calendar_scheduler" {
  count = var.enable_scheduler ? 1 : 0

  filename         = "scheduler.zip"
  function_name    = "${local.name_prefix}-scheduler"
  role            = aws_iam_role.holiday_calendar_role.arn
  handler         = "scheduler.lambda_handler"
  source_code_hash = data.archive_file.scheduler_zip[0].output_base64sha256
  runtime         = "python3.11"
  timeout         = 300

  environment {
    variables = {
      ECS_CLUSTER = aws_ecs_cluster.holiday_calendar_cluster.name
      ECS_SERVICE = aws_ecs_service.holiday_calendar_service.name
      S3_BUCKET   = aws_s3_bucket.holiday_calendar_storage.bucket
    }
  }

  tags = local.common_tags
}

# Lambda deployment package
data "archive_file" "scheduler_zip" {
  count = var.enable_scheduler ? 1 : 0

  type        = "zip"
  output_path = "scheduler.zip"
  source {
    content = templatefile("${path.module}/lambda/scheduler.py", {
      cluster_name = aws_ecs_cluster.holiday_calendar_cluster.name
      service_name = aws_ecs_service.holiday_calendar_service.name
    })
    filename = "scheduler.py"
  }
}

# EventBridge rule for scheduled execution
resource "aws_cloudwatch_event_rule" "holiday_calendar_schedule" {
  count = var.enable_scheduler ? 1 : 0

  name                = "${local.name_prefix}-schedule"
  description         = "Trigger holiday calendar updates"
  schedule_expression = var.schedule_expression

  tags = local.common_tags
}

# EventBridge target
resource "aws_cloudwatch_event_target" "holiday_calendar_target" {
  count = var.enable_scheduler ? 1 : 0

  rule      = aws_cloudwatch_event_rule.holiday_calendar_schedule[0].name
  target_id = "HolidayCalendarSchedulerTarget"
  arn       = aws_lambda_function.holiday_calendar_scheduler[0].arn
}

# Lambda permission for EventBridge
resource "aws_lambda_permission" "allow_eventbridge" {
  count = var.enable_scheduler ? 1 : 0

  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.holiday_calendar_scheduler[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.holiday_calendar_schedule[0].arn
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "${local.name_prefix}-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ecs cpu utilization"
  alarm_actions       = var.sns_topic_arn != "" ? [var.sns_topic_arn] : []

  dimensions = {
    ServiceName = aws_ecs_service.holiday_calendar_service.name
    ClusterName = aws_ecs_cluster.holiday_calendar_cluster.name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "high_memory" {
  alarm_name          = "${local.name_prefix}-high-memory"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ecs memory utilization"
  alarm_actions       = var.sns_topic_arn != "" ? [var.sns_topic_arn] : []

  dimensions = {
    ServiceName = aws_ecs_service.holiday_calendar_service.name
    ClusterName = aws_ecs_cluster.holiday_calendar_cluster.name
  }

  tags = local.common_tags
}