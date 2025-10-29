# AWS SSM Change Calendar 休業日スケジュール管理ツール
# Terraform統合例

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}

# プロバイダー設定
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "HolidayCalendar"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# 変数定義
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "calendar_years" {
  description = "Years to generate calendars for"
  type        = list(number)
  default     = [2024, 2025, 2026]
}

variable "exclude_sunday_holidays" {
  description = "Exclude Sunday holidays"
  type        = bool
  default     = true
}

variable "notification_email" {
  description = "Email for notifications"
  type        = string
  default     = "admin@example.com"
}

# ローカル値
locals {
  calendar_name_prefix = "japanese-holidays"
  
  common_tags = {
    Project     = "HolidayCalendar"
    Environment = var.environment
    CreatedBy   = "Terraform"
    Purpose     = "JapaneseHolidays"
  }
}

# ICSファイル生成用のnullリソース
resource "null_resource" "generate_ics_files" {
  count = length(var.calendar_years)
  
  triggers = {
    year                    = var.calendar_years[count.index]
    exclude_sunday_holidays = var.exclude_sunday_holidays
    # 毎月1日に再生成をトリガー
    monthly_trigger = formatdate("YYYY-MM", timestamp())
  }
  
  provisioner "local-exec" {
    command = <<-EOT
      cd ${path.module}/../../../
      python main.py holidays \
        --year ${var.calendar_years[count.index]} \
        --output terraform_output/holidays_${var.calendar_years[count.index]}.ics \
        ${var.exclude_sunday_holidays ? "" : "--include-sundays"}
    EOT
  }
  
  provisioner "local-exec" {
    when    = destroy
    command = "rm -f ${path.module}/terraform_output/holidays_${self.triggers.year}.ics"
  }
}

# 生成されたICSファイルの読み込み
data "local_file" "ics_files" {
  count = length(var.calendar_years)
  
  filename = "${path.module}/terraform_output/holidays_${var.calendar_years[count.index]}.ics"
  
  depends_on = [null_resource.generate_ics_files]
}

# AWS SSM Change Calendar ドキュメント
resource "aws_ssm_document" "japanese_holidays" {
  count = length(var.calendar_years)
  
  name            = "${local.calendar_name_prefix}-${var.calendar_years[count.index]}"
  document_type   = "ChangeCalendar"
  document_format = "TEXT"
  
  content = data.local_file.ics_files[count.index].content
  
  tags = merge(local.common_tags, {
    Year = tostring(var.calendar_years[count.index])
    Type = "HolidayCalendar"
  })
  
  depends_on = [null_resource.generate_ics_files]
}

# Change Calendar の状態確認用データソース
data "aws_ssm_document" "calendar_info" {
  count = length(aws_ssm_document.japanese_holidays)
  
  name = aws_ssm_document.japanese_holidays[count.index].name
}

# SNS トピック（通知用）
resource "aws_sns_topic" "holiday_calendar_notifications" {
  name = "holiday-calendar-notifications-${var.environment}"
  
  tags = local.common_tags
}

# SNS サブスクリプション
resource "aws_sns_topic_subscription" "email_notification" {
  topic_arn = aws_sns_topic.holiday_calendar_notifications.arn
  protocol  = "email"
  endpoint  = var.notification_email
}

# CloudWatch イベントルール（月次更新用）
resource "aws_cloudwatch_event_rule" "monthly_update" {
  name                = "holiday-calendar-monthly-update-${var.environment}"
  description         = "Trigger monthly holiday calendar update"
  schedule_expression = "cron(0 2 1 * ? *)"  # 毎月1日の午前2時
  
  tags = local.common_tags
}

# Lambda 実行ロール
resource "aws_iam_role" "lambda_execution_role" {
  name = "holiday-calendar-lambda-role-${var.environment}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
  
  tags = local.common_tags
}

# Lambda 実行ポリシー
resource "aws_iam_role_policy" "lambda_policy" {
  name = "holiday-calendar-lambda-policy-${var.environment}"
  role = aws_iam_role.lambda_execution_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:UpdateDocument",
          "ssm:GetDocument",
          "ssm:ListDocuments"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.holiday_calendar_notifications.arn
      }
    ]
  })
}

# Lambda 関数（更新処理用）
resource "aws_lambda_function" "holiday_calendar_updater" {
  filename         = "holiday_calendar_updater.zip"
  function_name    = "holiday-calendar-updater-${var.environment}"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "lambda_function.lambda_handler"
  runtime         = "python3.11"
  timeout         = 300
  
  environment {
    variables = {
      ENVIRONMENT           = var.environment
      SNS_TOPIC_ARN        = aws_sns_topic.holiday_calendar_notifications.arn
      EXCLUDE_SUNDAY_HOLIDAYS = tostring(var.exclude_sunday_holidays)
    }
  }
  
  tags = local.common_tags
}

# CloudWatch イベントターゲット
resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.monthly_update.name
  target_id = "HolidayCalendarLambdaTarget"
  arn       = aws_lambda_function.holiday_calendar_updater.arn
}

# Lambda 実行権限
resource "aws_lambda_permission" "allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.holiday_calendar_updater.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.monthly_update.arn
}

# S3 バケット（アーティファクト保存用）
resource "aws_s3_bucket" "holiday_calendar_artifacts" {
  bucket = "holiday-calendar-artifacts-${var.environment}-${random_id.bucket_suffix.hex}"
  
  tags = local.common_tags
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# S3 バケット設定
resource "aws_s3_bucket_versioning" "artifacts_versioning" {
  bucket = aws_s3_bucket.holiday_calendar_artifacts.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts_encryption" {
  bucket = aws_s3_bucket.holiday_calendar_artifacts.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 オブジェクト（ICSファイルのアップロード）
resource "aws_s3_object" "ics_artifacts" {
  count = length(var.calendar_years)
  
  bucket = aws_s3_bucket.holiday_calendar_artifacts.id
  key    = "calendars/holidays_${var.calendar_years[count.index]}.ics"
  source = "${path.module}/terraform_output/holidays_${var.calendar_years[count.index]}.ics"
  etag   = filemd5("${path.module}/terraform_output/holidays_${var.calendar_years[count.index]}.ics")
  
  tags = merge(local.common_tags, {
    Year = tostring(var.calendar_years[count.index])
  })
  
  depends_on = [null_resource.generate_ics_files]
}

# CloudWatch ダッシュボード
resource "aws_cloudwatch_dashboard" "holiday_calendar_dashboard" {
  dashboard_name = "HolidayCalendar-${var.environment}"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        
        properties = {
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", aws_lambda_function.holiday_calendar_updater.function_name],
            [".", "Errors", ".", "."],
            [".", "Invocations", ".", "."]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Lambda Function Metrics"
        }
      },
      {
        type   = "log"
        x      = 0
        y      = 6
        width  = 24
        height = 6
        
        properties = {
          query   = "SOURCE '/aws/lambda/${aws_lambda_function.holiday_calendar_updater.function_name}' | fields @timestamp, @message | sort @timestamp desc | limit 100"
          region  = var.aws_region
          title   = "Lambda Function Logs"
        }
      }
    ]
  })
}

# 出力値
output "change_calendar_names" {
  description = "Names of created Change Calendars"
  value       = aws_ssm_document.japanese_holidays[*].name
}

output "change_calendar_arns" {
  description = "ARNs of created Change Calendars"
  value       = [for doc in aws_ssm_document.japanese_holidays : "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:document/${doc.name}"]
}

output "sns_topic_arn" {
  description = "SNS topic ARN for notifications"
  value       = aws_sns_topic.holiday_calendar_notifications.arn
}

output "lambda_function_name" {
  description = "Lambda function name for updates"
  value       = aws_lambda_function.holiday_calendar_updater.function_name
}

output "s3_bucket_name" {
  description = "S3 bucket name for artifacts"
  value       = aws_s3_bucket.holiday_calendar_artifacts.id
}

output "dashboard_url" {
  description = "CloudWatch dashboard URL"
  value       = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.holiday_calendar_dashboard.dashboard_name}"
}

# データソース
data "aws_caller_identity" "current" {}

# 出力ディレクトリの作成
resource "null_resource" "create_output_directory" {
  provisioner "local-exec" {
    command = "mkdir -p ${path.module}/terraform_output"
  }
}

# Lambda デプロイメントパッケージの作成
data "archive_file" "lambda_zip" {
  type        = "zip"
  output_path = "${path.module}/holiday_calendar_updater.zip"
  
  source {
    content = templatefile("${path.module}/lambda_function.py.tpl", {
      calendar_years          = var.calendar_years
      exclude_sunday_holidays = var.exclude_sunday_holidays
    })
    filename = "lambda_function.py"
  }
}

# Terraform 状態ファイル用 S3 バケット（オプション）
resource "aws_s3_bucket" "terraform_state" {
  count = var.environment == "production" ? 1 : 0
  
  bucket = "terraform-state-holiday-calendar-${random_id.state_suffix.hex}"
  
  tags = merge(local.common_tags, {
    Purpose = "TerraformState"
  })
}

resource "random_id" "state_suffix" {
  byte_length = 4
}

# DynamoDB テーブル（Terraform ロック用）
resource "aws_dynamodb_table" "terraform_lock" {
  count = var.environment == "production" ? 1 : 0
  
  name           = "terraform-lock-holiday-calendar"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "LockID"
  
  attribute {
    name = "LockID"
    type = "S"
  }
  
  tags = merge(local.common_tags, {
    Purpose = "TerraformLock"
  })
}