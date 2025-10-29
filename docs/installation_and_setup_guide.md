# インストールとセットアップガイド

## 概要

AWS SSM Change Calendar 休業日スケジュール管理ツールの詳細なインストールとセットアップ手順を説明します。

## 目次

1. [システム要件](#システム要件)
2. [インストール方法](#インストール方法)
3. [AWS環境の設定](#aws環境の設定)
4. [初期設定](#初期設定)
5. [動作確認](#動作確認)
6. [高度な設定](#高度な設定)
7. [トラブルシューティング](#トラブルシューティング)

---

## システム要件

### 必須要件

| 項目 | 要件 | 推奨 |
|------|------|------|
| **Python** | 3.8以上 | 3.11以上 |
| **OS** | Windows 10/11, macOS 10.15+, Linux (Ubuntu 18.04+) | 最新版 |
| **メモリ** | 512MB以上 | 1GB以上 |
| **ディスク容量** | 100MB以上 | 500MB以上 |
| **ネットワーク** | インターネット接続 | 高速回線 |

### 依存パッケージ

| パッケージ | バージョン | 用途 |
|-----------|-----------|------|
| `boto3` | ≥1.26.0 | AWS SDK |
| `icalendar` | ≥5.0.0 | ICS生成・解析 |
| `click` | ≥8.0.0 | CLI フレームワーク |
| `requests` | ≥2.28.0 | HTTP通信 |
| `chardet` | ≥5.0.0 | 文字エンコーディング検出 |
| `pytz` | ≥2022.1 | タイムゾーン処理 |
| `python-dateutil` | ≥2.8.0 | 日付解析 |

---

## インストール方法

### 方法1: GitHubからのクローン（推奨）

#### 1. リポジトリのクローン

```bash
# HTTPSでクローン
git clone https://github.com/your-org/aws-ssm-calendar-generator.git
cd aws-ssm-calendar-generator

# SSHでクローン（SSH鍵設定済みの場合）
git clone git@github.com:your-org/aws-ssm-calendar-generator.git
cd aws-ssm-calendar-generator
```

#### 2. 仮想環境の作成

```bash
# Python仮想環境の作成
python -m venv .venv

# 仮想環境の有効化
# Windows (Command Prompt)
.venv\Scripts\activate.bat

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate
```

#### 3. 依存関係のインストール

```bash
# 基本パッケージのインストール
pip install --upgrade pip
pip install -r requirements.txt

# 開発用パッケージも含める場合（オプション）
pip install -r requirements-dev.txt
```

### 方法2: リリース版のダウンロード

#### 1. リリース版の取得

```bash
# 最新リリースをダウンロード
wget https://github.com/your-org/aws-ssm-calendar-generator/archive/v1.0.0.tar.gz

# 展開
tar -xzf v1.0.0.tar.gz
cd aws-ssm-calendar-generator-1.0.0
```

#### 2. セットアップ

```bash
# 仮想環境作成と依存関係インストール
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# または .venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 方法3: pipでのインストール（将来対応予定）

```bash
# PyPIからのインストール（将来実装予定）
pip install aws-ssm-calendar-generator

# 開発版のインストール
pip install git+https://github.com/your-org/aws-ssm-calendar-generator.git
```

### 方法4: Dockerでのインストール

#### 1. Dockerイメージのビルド

```bash
# Dockerfileからビルド
docker build -t aws-ssm-calendar-tool .

# または、プリビルドイメージの使用
docker pull your-org/aws-ssm-calendar-tool:latest
```

#### 2. Dockerでの実行

```bash
# 基本的な実行
docker run --rm aws-ssm-calendar-tool python main.py holidays

# AWS認証情報をマウント
docker run --rm \
  -v ~/.aws:/root/.aws:ro \
  -v $(pwd)/output:/app/output \
  aws-ssm-calendar-tool \
  python main.py holidays --output /app/output/holidays.ics

# 環境変数での認証情報設定
docker run --rm \
  -e AWS_ACCESS_KEY_ID=your-key \
  -e AWS_SECRET_ACCESS_KEY=your-secret \
  -e AWS_DEFAULT_REGION=ap-northeast-1 \
  aws-ssm-calendar-tool \
  python main.py list-calendars
```

---

## AWS環境の設定

### 1. AWS CLIのインストール

#### Windows

```powershell
# Chocolateyを使用
choco install awscli

# または、MSIインストーラーをダウンロード
# https://aws.amazon.com/cli/
```

#### macOS

```bash
# Homebrewを使用
brew install awscli

# または、pipを使用
pip install awscli
```

#### Linux

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install awscli

# CentOS/RHEL
sudo yum install awscli

# または、pipを使用
pip install awscli
```

### 2. AWS認証情報の設定

#### 方法1: AWS CLI設定（推奨）

```bash
# 基本設定
aws configure
# AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE
# AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
# Default region name [None]: ap-northeast-1
# Default output format [None]: json

# 設定確認
aws configure list
aws sts get-caller-identity
```

#### 方法2: プロファイル別設定

```bash
# 本番環境用プロファイル
aws configure --profile production
# 開発環境用プロファイル
aws configure --profile development

# プロファイル一覧確認
aws configure list-profiles

# 特定プロファイルでの実行
aws --profile production sts get-caller-identity
```

#### 方法3: AWS SSO設定

```bash
# SSO設定
aws configure sso
# SSO start URL: https://your-org.awsapps.com/start
# SSO region: us-east-1
# Account ID: 123456789012
# Role name: PowerUserAccess
# CLI default client Region: ap-northeast-1
# CLI default output format: json
# CLI profile name: sso-profile

# SSOログイン
aws sso login --profile sso-profile

# SSO設定確認
aws --profile sso-profile sts get-caller-identity
```

#### 方法4: 環境変数設定

```bash
# 基本認証情報
export AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
export AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
export AWS_DEFAULT_REGION="ap-northeast-1"

# セッショントークン（一時的な認証情報）
export AWS_SESSION_TOKEN="temporary-session-token"

# プロファイル指定
export AWS_PROFILE="production"

# 設定確認
env | grep AWS
```

### 3. IAM権限の設定

#### 最小権限ポリシー（読み取り専用）

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SSMReadOnlyAccess",
      "Effect": "Allow",
      "Action": [
        "ssm:GetDocument",
        "ssm:ListDocuments",
        "ssm:GetCalendarState",
        "ssm:DescribeParameters"
      ],
      "Resource": "*"
    }
  ]
}
```

#### 完全機能ポリシー

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SSMFullAccess",
      "Effect": "Allow",
      "Action": [
        "ssm:CreateDocument",
        "ssm:UpdateDocument",
        "ssm:DeleteDocument",
        "ssm:GetDocument",
        "ssm:ListDocuments",
        "ssm:GetCalendarState",
        "ssm:DescribeParameters",
        "ssm:AddTagsToResource",
        "ssm:RemoveTagsFromResource",
        "ssm:ListTagsForResource"
      ],
      "Resource": "*"
    }
  ]
}
```

#### IAMポリシーの適用

```bash
# ポリシーファイルの作成
cat > ssm-calendar-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetDocument",
        "ssm:ListDocuments",
        "ssm:GetCalendarState"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# IAMポリシーの作成
aws iam create-policy \
  --policy-name SSMCalendarReadOnly \
  --policy-document file://ssm-calendar-policy.json

# ユーザーにポリシーをアタッチ
aws iam attach-user-policy \
  --user-name your-username \
  --policy-arn arn:aws:iam::123456789012:policy/SSMCalendarReadOnly
```

---

## 初期設定

### 1. ディレクトリ構造の作成

```bash
# 設定ディレクトリの作成
mkdir -p ~/.aws-ssm-calendar/cache
mkdir -p ~/.aws-ssm-calendar/logs
mkdir -p ./output

# 権限設定（Linux/macOS）
chmod 700 ~/.aws-ssm-calendar
chmod 755 ./output
```

### 2. 設定ファイルの作成

#### 基本設定ファイル

```bash
cat > ~/.aws-ssm-calendar/config.json << 'EOF'
{
  "aws": {
    "region": "ap-northeast-1",
    "profile": null,
    "timeout": 30
  },
  "calendar": {
    "default_timezone": "Asia/Tokyo",
    "exclude_sunday_holidays": true,
    "output_format": "ics"
  },
  "output": {
    "directory": "./output",
    "filename_template": "{calendar_name}_{date}.ics",
    "encoding": "utf-8"
  },
  "cache": {
    "enabled": true,
    "ttl_days": 30,
    "directory": "~/.aws-ssm-calendar/cache",
    "max_size_mb": 100
  },
  "logging": {
    "level": "INFO",
    "format": "structured",
    "file": "~/.aws-ssm-calendar/logs/application.log",
    "enable_performance_monitoring": true,
    "enable_system_monitoring": true
  },
  "network": {
    "timeout": 30,
    "retry_count": 3,
    "retry_delay": 1
  }
}
EOF
```

#### 環境別設定ファイル

**開発環境用設定:**
```bash
cat > ~/.aws-ssm-calendar/config-dev.json << 'EOF'
{
  "aws": {
    "region": "us-west-2",
    "profile": "development"
  },
  "logging": {
    "level": "DEBUG",
    "format": "detailed"
  }
}
EOF
```

**本番環境用設定:**
```bash
cat > ~/.aws-ssm-calendar/config-prod.json << 'EOF'
{
  "aws": {
    "region": "ap-northeast-1",
    "profile": "production"
  },
  "logging": {
    "level": "WARNING",
    "format": "json",
    "file": "/var/log/aws-ssm-calendar/application.log"
  }
}
EOF
```

### 3. 環境変数の設定

#### Bashの場合

```bash
# ~/.bashrcまたは~/.bash_profileに追加
cat >> ~/.bashrc << 'EOF'

# AWS SSM Calendar Tool
export AWS_SSM_CALENDAR_CONFIG="$HOME/.aws-ssm-calendar/config.json"
export AWS_SSM_CALENDAR_CACHE_DIR="$HOME/.aws-ssm-calendar/cache"
export AWS_DEFAULT_REGION="ap-northeast-1"

# エイリアス設定
alias ssm-calendar="python /path/to/aws-ssm-calendar-generator/main.py"
EOF

# 設定を反映
source ~/.bashrc
```

#### Zshの場合

```bash
# ~/.zshrcに追加
cat >> ~/.zshrc << 'EOF'

# AWS SSM Calendar Tool
export AWS_SSM_CALENDAR_CONFIG="$HOME/.aws-ssm-calendar/config.json"
export AWS_SSM_CALENDAR_CACHE_DIR="$HOME/.aws-ssm-calendar/cache"
export AWS_DEFAULT_REGION="ap-northeast-1"

# エイリアス設定
alias ssm-calendar="python /path/to/aws-ssm-calendar-generator/main.py"
EOF

# 設定を反映
source ~/.zshrc
```

#### Windowsの場合

```powershell
# PowerShellプロファイルに追加
$ProfilePath = $PROFILE
if (!(Test-Path $ProfilePath)) {
    New-Item -Path $ProfilePath -Type File -Force
}

Add-Content -Path $ProfilePath -Value @"

# AWS SSM Calendar Tool
`$env:AWS_SSM_CALENDAR_CONFIG = "`$env:USERPROFILE\.aws-ssm-calendar\config.json"
`$env:AWS_SSM_CALENDAR_CACHE_DIR = "`$env:USERPROFILE\.aws-ssm-calendar\cache"
`$env:AWS_DEFAULT_REGION = "ap-northeast-1"

# エイリアス設定
function ssm-calendar { python C:\path\to\aws-ssm-calendar-generator\main.py @args }
"@
```

---

## 動作確認

### 1. 基本機能テスト

```bash
# ヘルプ表示テスト
python main.py --help

# バージョン情報確認
python main.py --version

# 設定確認
python main.py system-metrics
```

### 2. 祝日データテスト

```bash
# 祝日データの初期化
python main.py refresh-holidays

# 今年の祝日表示
python main.py holidays

# 特定日の祝日判定
python main.py check-holiday --date 2024-01-01

# 祝日統計表示
python main.py holidays --format json
```

### 3. AWS接続テスト

```bash
# AWS認証確認
aws sts get-caller-identity

# Change Calendar一覧取得
python main.py list-calendars

# システム情報表示
python main.py system-metrics
```

### 4. ICS生成テスト

```bash
# 基本的なICS生成
python main.py holidays --year 2024 --output test_holidays.ics

# 生成されたファイルの確認
ls -la test_holidays.ics
file test_holidays.ics

# ICSファイルの解析
python main.py analyze-ics test_holidays.ics
```

### 5. 包括的テストスクリプト

```bash
#!/bin/bash
# comprehensive_test.sh

echo "=== AWS SSM Calendar Tool 動作確認テスト ==="

# 1. Python環境確認
echo "1. Python環境確認"
python --version
pip list | grep -E "(boto3|icalendar|click|requests)"

# 2. AWS認証確認
echo "2. AWS認証確認"
if aws sts get-caller-identity > /dev/null 2>&1; then
    echo "✓ AWS認証成功"
else
    echo "✗ AWS認証失敗"
    exit 1
fi

# 3. 祝日データテスト
echo "3. 祝日データテスト"
if python main.py refresh-holidays > /dev/null 2>&1; then
    echo "✓ 祝日データ取得成功"
else
    echo "✗ 祝日データ取得失敗"
    exit 1
fi

# 4. ICS生成テスト
echo "4. ICS生成テスト"
if python main.py holidays --year 2024 --output test.ics > /dev/null 2>&1; then
    echo "✓ ICS生成成功"
    rm -f test.ics
else
    echo "✗ ICS生成失敗"
    exit 1
fi

# 5. AWS Change Calendar接続テスト
echo "5. AWS Change Calendar接続テスト"
if python main.py list-calendars > /dev/null 2>&1; then
    echo "✓ AWS Change Calendar接続成功"
else
    echo "✗ AWS Change Calendar接続失敗"
fi

echo "=== テスト完了 ==="
```

---

## 高度な設定

### 1. プロキシ環境での設定

#### HTTP/HTTPSプロキシ

```bash
# 環境変数での設定
export HTTP_PROXY="http://proxy.company.com:8080"
export HTTPS_PROXY="http://proxy.company.com:8080"
export NO_PROXY="localhost,127.0.0.1,.company.com"

# 認証付きプロキシ
export HTTP_PROXY="http://username:password@proxy.company.com:8080"
export HTTPS_PROXY="http://username:password@proxy.company.com:8080"
```

#### プロキシ設定ファイル

```json
{
  "network": {
    "proxy": {
      "http": "http://proxy.company.com:8080",
      "https": "http://proxy.company.com:8080",
      "no_proxy": ["localhost", "127.0.0.1", ".company.com"]
    },
    "timeout": 60,
    "retry_count": 5
  }
}
```

### 2. ログ設定の詳細化

#### 高度なログ設定

```json
{
  "logging": {
    "level": "INFO",
    "format": "structured",
    "handlers": {
      "file": {
        "enabled": true,
        "path": "~/.aws-ssm-calendar/logs/application.log",
        "max_size_mb": 10,
        "backup_count": 5,
        "rotation": "daily"
      },
      "console": {
        "enabled": true,
        "format": "simple",
        "level": "WARNING"
      },
      "syslog": {
        "enabled": false,
        "facility": "local0",
        "address": ["localhost", 514]
      }
    },
    "performance_monitoring": {
      "enabled": true,
      "threshold_ms": 1000,
      "sample_rate": 0.1
    }
  }
}
```

### 3. セキュリティ設定

#### ファイル権限の設定

```bash
# 設定ファイルの権限を制限
chmod 600 ~/.aws-ssm-calendar/config.json
chmod 600 ~/.aws/credentials
chmod 600 ~/.aws/config

# ディレクトリ権限の設定
chmod 700 ~/.aws-ssm-calendar
chmod 700 ~/.aws
```

#### 暗号化設定

```bash
# 設定ファイルの暗号化（gpg使用）
gpg --symmetric --cipher-algo AES256 ~/.aws-ssm-calendar/config.json
rm ~/.aws-ssm-calendar/config.json

# 復号化して使用
gpg --decrypt ~/.aws-ssm-calendar/config.json.gpg > ~/.aws-ssm-calendar/config.json
python main.py holidays
rm ~/.aws-ssm-calendar/config.json
```

### 4. パフォーマンス最適化

#### メモリ使用量の最適化

```json
{
  "performance": {
    "memory_optimization": {
      "enable_monitoring": false,
      "cache_size_limit_mb": 50,
      "gc_threshold": 1000
    },
    "concurrent_processing": {
      "max_workers": 4,
      "chunk_size": 100
    }
  }
}
```

#### キャッシュ設定の最適化

```json
{
  "cache": {
    "enabled": true,
    "ttl_days": 30,
    "directory": "~/.aws-ssm-calendar/cache",
    "max_size_mb": 100,
    "compression": true,
    "cleanup_interval_hours": 24,
    "strategies": {
      "holidays": {
        "ttl_days": 30,
        "max_entries": 1000
      },
      "aws_calendars": {
        "ttl_days": 1,
        "max_entries": 100
      }
    }
  }
}
```

---

## トラブルシューティング

### 1. インストール関連の問題

#### Python バージョンエラー

```bash
# 問題: Python 3.7以下を使用している
python --version
# Python 3.7.x

# 解決: Python 3.8以上をインストール
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-pip

# macOS (Homebrew)
brew install python@3.11

# Windows
# https://www.python.org/downloads/ からダウンロード
```

#### 依存関係インストールエラー

```bash
# 問題: パッケージインストールに失敗
pip install -r requirements.txt
# ERROR: Could not build wheels for some-package

# 解決1: pipとsetuptoolsのアップグレード
pip install --upgrade pip setuptools wheel

# 解決2: システムパッケージのインストール（Linux）
sudo apt install python3-dev build-essential

# 解決3: 個別パッケージのインストール
pip install boto3
pip install icalendar
pip install click
pip install requests
pip install chardet
pip install pytz
pip install python-dateutil
```

### 2. AWS認証関連の問題

#### 認証情報が見つからない

```bash
# 問題: NoCredentialsError
python main.py list-calendars
# NoCredentialsError: Unable to locate credentials

# 解決1: AWS CLIで設定
aws configure

# 解決2: 環境変数で設定
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"

# 解決3: プロファイル確認
aws configure list
aws configure list-profiles
```

#### 権限不足エラー

```bash
# 問題: AccessDenied
python main.py list-calendars
# ClientError: An error occurred (AccessDenied) when calling the ListDocuments operation

# 解決: 必要な権限を確認・付与
aws iam list-attached-user-policies --user-name your-username
aws iam attach-user-policy --user-name your-username --policy-arn arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess
```

### 3. ネットワーク関連の問題

#### 内閣府サーバーへの接続エラー

```bash
# 問題: 祝日データ取得に失敗
python main.py refresh-holidays
# NetworkError: Failed to connect to Cabinet Office server

# 解決1: ネットワーク接続確認
curl -I https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv

# 解決2: プロキシ設定
export HTTP_PROXY="http://proxy:8080"
export HTTPS_PROXY="http://proxy:8080"

# 解決3: 手動データ配置
wget https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv
mkdir -p ~/.aws-ssm-calendar/cache
cp syukujitsu.csv ~/.aws-ssm-calendar/cache/japanese_holidays.csv
```

### 4. ファイル・ディレクトリ関連の問題

#### 権限エラー

```bash
# 問題: PermissionError
python main.py holidays --output /root/holidays.ics
# PermissionError: [Errno 13] Permission denied

# 解決1: 出力ディレクトリの変更
python main.py holidays --output ./holidays.ics

# 解決2: ディレクトリ権限の修正
sudo chown -R $USER:$USER ~/.aws-ssm-calendar
chmod 755 ~/.aws-ssm-calendar
```

#### ディスク容量不足

```bash
# 問題: No space left on device
df -h
# /dev/sda1  100%  Used

# 解決1: 不要ファイルの削除
rm -rf ~/.aws-ssm-calendar/cache/*
rm -rf ~/.aws-ssm-calendar/logs/*

# 解決2: キャッシュサイズの制限
# config.jsonで設定
{
  "cache": {
    "max_size_mb": 10
  }
}
```

### 5. 診断ツール

#### システム診断スクリプト

```bash
#!/bin/bash
# diagnosis.sh - システム診断ツール

echo "=== AWS SSM Calendar Tool システム診断 ==="

# Python環境
echo "1. Python環境"
python --version
which python
echo "仮想環境: $VIRTUAL_ENV"

# 依存パッケージ
echo "2. 依存パッケージ"
pip list | grep -E "(boto3|icalendar|click|requests|chardet|pytz|python-dateutil)"

# AWS設定
echo "3. AWS設定"
aws configure list
echo "認証情報テスト:"
aws sts get-caller-identity 2>&1 | head -5

# ディレクトリ・ファイル
echo "4. ディレクトリ・ファイル"
ls -la ~/.aws-ssm-calendar/ 2>/dev/null || echo "設定ディレクトリなし"
ls -la ./output/ 2>/dev/null || echo "出力ディレクトリなし"

# ネットワーク
echo "5. ネットワーク"
curl -I https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv 2>&1 | head -3

# ディスク容量
echo "6. ディスク容量"
df -h . | tail -1

echo "=== 診断完了 ==="
```

#### ログ解析ツール

```bash
#!/bin/bash
# log_analyzer.sh - ログ解析ツール

LOG_FILE="$HOME/.aws-ssm-calendar/logs/application.log"

if [ ! -f "$LOG_FILE" ]; then
    echo "ログファイルが見つかりません: $LOG_FILE"
    exit 1
fi

echo "=== ログ解析結果 ==="

# エラー統計
echo "1. エラー統計"
grep -c "ERROR" "$LOG_FILE" 2>/dev/null || echo "0"
grep -c "WARNING" "$LOG_FILE" 2>/dev/null || echo "0"

# 最新のエラー
echo "2. 最新のエラー (最大5件)"
grep "ERROR" "$LOG_FILE" | tail -5

# パフォーマンス情報
echo "3. パフォーマンス情報"
grep "performance" "$LOG_FILE" | tail -3

echo "=== 解析完了 ==="
```

これらの手順に従って、AWS SSM Change Calendar 休業日スケジュール管理ツールを正しくインストール・設定してください。問題が発生した場合は、トラブルシューティングセクションを参照するか、診断ツールを使用して問題を特定してください。