# トラブルシューティングとFAQ

## 概要

AWS SSM Change Calendar 休業日スケジュール管理ツールの一般的な問題と解決方法、よくある質問への回答を提供します。

## 目次

1. [クイック診断](#クイック診断)
2. [一般的な問題と解決方法](#一般的な問題と解決方法)
3. [エラーメッセージ別対処法](#エラーメッセージ別対処法)
4. [パフォーマンス問題](#パフォーマンス問題)
5. [AWS関連の問題](#aws関連の問題)
6. [インストール・セットアップ問題](#インストール・セットアップ問題)
7. [よくある質問 (FAQ)](#よくある質問-faq)
8. [デバッグツール](#デバッグツール)
9. [サポート情報](#サポート情報)

---

## クイック診断

問題が発生した場合、まず以下のクイック診断を実行してください。

### 1分間診断スクリプト

```bash
#!/bin/bash
# quick_diagnosis.sh - 1分間でシステム状態を確認

echo "=== AWS SSM Calendar Tool クイック診断 ==="
echo "実行時刻: $(date)"
echo

# 1. Python環境確認
echo "1. Python環境"
python --version 2>/dev/null && echo "✓ Python OK" || echo "✗ Python NG"

# 2. 依存パッケージ確認
echo "2. 依存パッケージ"
python -c "import boto3, icalendar, click, requests; print('✓ 主要パッケージ OK')" 2>/dev/null || echo "✗ パッケージ不足"

# 3. AWS認証確認
echo "3. AWS認証"
aws sts get-caller-identity >/dev/null 2>&1 && echo "✓ AWS認証 OK" || echo "✗ AWS認証 NG"

# 4. ネットワーク確認
echo "4. ネットワーク"
curl -s -I https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv | head -1 | grep -q "200" && echo "✓ ネットワーク OK" || echo "✗ ネットワーク NG"

# 5. 基本機能確認
echo "5. 基本機能"
python main.py --help >/dev/null 2>&1 && echo "✓ 基本機能 OK" || echo "✗ 基本機能 NG"

echo
echo "=== 診断完了 ==="
echo "問題がある項目については、詳細なトラブルシューティングを参照してください。"
```

### 問題の分類

| 症状 | 可能性の高い原因 | 参照セクション |
|------|----------------|---------------|
| `python main.py`が動作しない | Python環境・依存関係 | [インストール・セットアップ問題](#インストール・セットアップ問題) |
| AWS関連エラー | 認証・権限・ネットワーク | [AWS関連の問題](#aws関連の問題) |
| 祝日データ取得エラー | ネットワーク・プロキシ | [一般的な問題と解決方法](#一般的な問題と解決方法) |
| 処理が遅い・メモリ不足 | パフォーマンス設定 | [パフォーマンス問題](#パフォーマンス問題) |
| ファイル生成・読み込みエラー | ファイル権限・ディスク容量 | [エラーメッセージ別対処法](#エラーメッセージ別対処法) |

---

## 一般的な問題と解決方法

### 1. 祝日データの取得に失敗する

#### 症状
```
NetworkError: 内閣府サーバーへの接続に失敗しました
```

#### 原因
- インターネット接続の問題
- 内閣府サーバーの一時的な障害
- ファイアウォールによるブロック
- プロキシ設定の問題

#### 解決方法

**基本的な対処:**
```python
from src.japanese_holidays import JapaneseHolidays
from src.error_handler import NetworkError

try:
    holidays = JapaneseHolidays()
    holidays.refresh_data()
except NetworkError as e:
    print(f"ネットワークエラー: {e}")
    print("キャッシュデータを使用します")
    
    # キャッシュが利用可能かチェック
    try:
        test_holiday = holidays.is_holiday(date(2024, 1, 1))
        print("キャッシュデータで動作継続")
    except Exception:
        print("キャッシュデータも利用できません")
```

**プロキシ環境での対処:**
```python
import os
import requests

# プロキシ設定
os.environ['HTTP_PROXY'] = 'http://proxy.company.com:8080'
os.environ['HTTPS_PROXY'] = 'http://proxy.company.com:8080'

# または直接requests設定
proxies = {
    'http': 'http://proxy.company.com:8080',
    'https': 'http://proxy.company.com:8080'
}

# カスタムHTTPセッションで祝日データ取得
session = requests.Session()
session.proxies.update(proxies)
```

**手動データ配置:**
```bash
# 手動で祝日データをダウンロード
curl -o japanese_holidays.csv https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv

# キャッシュディレクトリに配置
mkdir -p ~/.aws-ssm-calendar/cache/
cp japanese_holidays.csv ~/.aws-ssm-calendar/cache/
```

### 2. 文字エンコーディングエラー

#### 症状
```
EncodingError: 文字エンコーディングの変換に失敗しました
UnicodeDecodeError: 'utf-8' codec can't decode byte
```

#### 原因
- 内閣府CSVファイルのエンコーディング変更
- 破損したキャッシュファイル
- システムのロケール設定問題

#### 解決方法

**キャッシュクリアと再取得:**
```python
import os
from pathlib import Path

# キャッシュファイルを削除
cache_path = Path.home() / '.aws-ssm-calendar' / 'cache' / 'japanese_holidays.csv'
if cache_path.exists():
    cache_path.unlink()
    print("キャッシュファイルを削除しました")

# 再初期化
from src.japanese_holidays import JapaneseHolidays
holidays = JapaneseHolidays()
```

**手動エンコーディング指定:**
```python
import chardet
import csv

def manual_encoding_fix(csv_file_path: str):
    """手動でエンコーディングを修正"""
    
    # ファイルのエンコーディングを検出
    with open(csv_file_path, 'rb') as f:
        raw_data = f.read()
        encoding_result = chardet.detect(raw_data)
        detected_encoding = encoding_result['encoding']
    
    print(f"検出されたエンコーディング: {detected_encoding}")
    
    # UTF-8に変換して保存
    with open(csv_file_path, 'r', encoding=detected_encoding) as f:
        content = f.read()
    
    utf8_path = csv_file_path.replace('.csv', '_utf8.csv')
    with open(utf8_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"UTF-8ファイルを作成: {utf8_path}")
    return utf8_path

# 使用例
fixed_file = manual_encoding_fix("japanese_holidays.csv")
```

### 3. ICSファイル生成エラー

#### 症状
```
ICSGenerationError: ICSファイルの生成に失敗しました
ValueError: Invalid datetime format
```

#### 原因
- 無効な日付データ
- タイムゾーン設定の問題
- メモリ不足

#### 解決方法

**日付データの検証:**
```python
from datetime import date, datetime
from src.ics_generator import ICSGenerator
from src.japanese_holidays import JapaneseHolidays

def validate_and_generate_ics(year: int):
    """検証付きICS生成"""
    
    holidays = JapaneseHolidays()
    generator = ICSGenerator(holidays)
    
    try:
        # 祝日データの検証
        year_holidays = holidays.get_holidays_by_year(year)
        
        valid_holidays = []
        for holiday_date, holiday_name in year_holidays:
            # 日付の妥当性チェック
            if isinstance(holiday_date, date) and holiday_name:
                valid_holidays.append((holiday_date, holiday_name))
            else:
                print(f"無効な祝日データをスキップ: {holiday_date}, {holiday_name}")
        
        print(f"有効な祝日データ: {len(valid_holidays)}件")
        
        # ICS生成
        events = generator.convert_holidays_to_events(valid_holidays)
        calendar = generator.create_aws_ssm_calendar()
        
        for event in events:
            calendar.add_component(event)
        
        filename = f"holidays_{year}_validated.ics"
        generator.save_to_file(filename)
        
        print(f"ICSファイル生成完了: {filename}")
        return filename
        
    except Exception as e:
        print(f"ICS生成エラー: {e}")
        return None

# 使用例
result = validate_and_generate_ics(2024)
```

**メモリ不足対策:**
```python
# 監視機能を無効にしてメモリ使用量を削減
holidays = JapaneseHolidays(enable_monitoring=False)
generator = ICSGenerator(holidays, exclude_sunday_holidays=True)

# 年単位での分割処理
for year in range(2024, 2027):
    year_holidays = holidays.get_holidays_by_year(year)
    # 年ごとに個別のICSファイルを生成
    filename = f"holidays_{year}.ics"
    # 処理後にメモリを解放
    del year_holidays
```

### 4. AWS認証エラー

#### 症状
```
AWSError: AWS認証に失敗しました
NoCredentialsError: Unable to locate credentials
```

#### 原因
- AWS認証情報が設定されていない
- 権限不足
- プロファイル設定の問題

#### 解決方法

**認証情報の確認:**
```bash
# AWS CLI設定確認
aws configure list

# 認証情報の設定
aws configure

# プロファイル別設定
aws configure --profile myprofile
```

**プログラムでの認証確認:**
```python
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

def check_aws_credentials():
    """AWS認証情報の確認"""
    
    try:
        # デフォルト認証情報でテスト
        session = boto3.Session()
        credentials = session.get_credentials()
        
        if credentials is None:
            print("AWS認証情報が設定されていません")
            return False
        
        print(f"アクセスキーID: {credentials.access_key[:8]}...")
        
        # SSMクライアントでテスト
        ssm = session.client('ssm')
        response = ssm.describe_parameters(MaxResults=1)
        
        print("AWS SSM接続テスト成功")
        return True
        
    except NoCredentialsError:
        print("認証情報が見つかりません")
        print("以下のコマンドで設定してください:")
        print("aws configure")
        return False
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'AccessDenied':
            print("SSMへのアクセス権限がありません")
            print("必要な権限: ssm:DescribeParameters")
        else:
            print(f"AWS APIエラー: {e}")
        return False

# 実行
check_aws_credentials()
```

**必要なIAMポリシー:**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
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

---

## エラーメッセージ別対処法

### NetworkError関連

#### `ConnectionTimeout: 接続がタイムアウトしました`

**対処法:**
```python
import requests
from src.japanese_holidays import JapaneseHolidays

# タイムアウト時間を延長
class ExtendedHolidays(JapaneseHolidays):
    def fetch_official_data(self):
        response = requests.get(
            self.OFFICIAL_URL,
            timeout=60,  # 60秒に延長
            headers={'User-Agent': 'Mozilla/5.0 (compatible; HolidayBot/1.0)'}
        )
        return response.text

holidays = ExtendedHolidays()
```

#### `DNSResolutionError: ドメイン名の解決に失敗`

**対処法:**
```bash
# DNS設定確認
nslookup www8.cao.go.jp

# 代替DNS使用
echo "nameserver 8.8.8.8" >> /etc/resolv.conf
```

### EncodingError関連

#### `UnicodeDecodeError: 文字の解読に失敗`

**対処法:**
```python
import chardet

def robust_encoding_detection(file_path: str) -> str:
    """堅牢なエンコーディング検出"""
    
    encodings_to_try = ['shift_jis', 'cp932', 'utf-8', 'euc-jp', 'iso-2022-jp']
    
    with open(file_path, 'rb') as f:
        raw_data = f.read()
    
    # chardetによる自動検出
    detected = chardet.detect(raw_data)
    if detected['confidence'] > 0.8:
        return detected['encoding']
    
    # 手動で各エンコーディングを試行
    for encoding in encodings_to_try:
        try:
            raw_data.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    
    raise EncodingError("適切なエンコーディングが見つかりません")
```

### AWSError関連

#### `AccessDenied: アクセスが拒否されました`

**対処法:**
```python
def check_required_permissions():
    """必要な権限をチェック"""
    
    import boto3
    from botocore.exceptions import ClientError
    
    ssm = boto3.client('ssm')
    
    required_actions = [
        ('ssm:ListDocuments', lambda: ssm.list_documents(MaxResults=1)),
        ('ssm:GetDocument', lambda: ssm.get_document(Name='test')),
        ('ssm:GetCalendarState', lambda: ssm.get_calendar_state(CalendarNames=['test']))
    ]
    
    for action_name, action_func in required_actions:
        try:
            action_func()
            print(f"✓ {action_name}: 権限あり")
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                print(f"✗ {action_name}: 権限なし")
            elif e.response['Error']['Code'] in ['DocumentNotFound', 'InvalidDocument']:
                print(f"✓ {action_name}: 権限あり（テストドキュメント不存在）")
            else:
                print(f"? {action_name}: {e}")

check_required_permissions()
```

---

## パフォーマンス問題

### 1. メモリ使用量が多い

#### 症状
- システムが遅くなる
- メモリ不足エラー
- プロセスが強制終了される

#### 対処法

**メモリ監視の無効化:**
```python
# パフォーマンス監視を無効にしてメモリ使用量を削減
holidays = JapaneseHolidays(enable_monitoring=False)
```

**バッチ処理の実装:**
```python
def process_holidays_in_batches(start_year: int, end_year: int, batch_size: int = 3):
    """バッチ処理で大量の年度を処理"""
    
    holidays = JapaneseHolidays(enable_monitoring=False)
    
    for batch_start in range(start_year, end_year + 1, batch_size):
        batch_end = min(batch_start + batch_size - 1, end_year)
        
        print(f"処理中: {batch_start}-{batch_end}年")
        
        for year in range(batch_start, batch_end + 1):
            year_holidays = holidays.get_holidays_by_year(year)
            # 年ごとの処理
            filename = f"holidays_{year}.ics"
            # 処理完了後にメモリ解放
            del year_holidays
        
        # バッチ完了後にガベージコレクション
        import gc
        gc.collect()

# 使用例
process_holidays_in_batches(2020, 2030, batch_size=3)
```

### 2. 処理速度が遅い

#### 症状
- 祝日判定に時間がかかる
- ICS生成が遅い

#### 対処法

**キャッシュの活用:**
```python
from functools import lru_cache

class FastHolidayChecker:
    def __init__(self):
        self.holidays = JapaneseHolidays()
        self._holiday_set = None
    
    def _build_holiday_set(self):
        """高速検索用のセットを構築"""
        if self._holiday_set is None:
            all_holidays = []
            current_year = date.today().year
            
            # 過去5年から未来5年のデータを事前読み込み
            for year in range(current_year - 5, current_year + 6):
                year_holidays = self.holidays.get_holidays_by_year(year)
                all_holidays.extend([h[0] for h in year_holidays])
            
            self._holiday_set = set(all_holidays)
    
    @lru_cache(maxsize=1000)
    def is_holiday_fast(self, check_date: date) -> bool:
        """高速祝日判定"""
        self._build_holiday_set()
        return check_date in self._holiday_set

# 使用例
checker = FastHolidayChecker()

# 大量の日付を高速チェック
import time
start_time = time.time()

for i in range(10000):
    result = checker.is_holiday_fast(date(2024, 1, 1))

elapsed = time.time() - start_time
print(f"10,000回の判定時間: {elapsed:.3f}秒")
```

---

## AWS関連の問題

### 1. Change Calendarが見つからない

#### 症状
```
DocumentNotFound: Change Calendar 'MyCalendar' が見つかりません
```

#### 対処法

**利用可能なカレンダーを確認:**
```python
from src.aws_client import SSMChangeCalendarClient

def list_available_calendars():
    """利用可能なChange Calendarを一覧表示"""
    
    client = SSMChangeCalendarClient()
    
    try:
        # SSMドキュメントを検索
        ssm = client.ssm_client
        
        # Change Calendarタイプのドキュメントを検索
        response = ssm.list_documents(
            Filters=[
                {
                    'Key': 'DocumentType',
                    'Values': ['ChangeCalendar']
                }
            ]
        )
        
        calendars = response.get('DocumentIdentifiers', [])
        
        if not calendars:
            print("Change Calendarが見つかりません")
            return []
        
        print(f"利用可能なChange Calendar: {len(calendars)}個")
        
        for calendar in calendars:
            name = calendar['Name']
            status = calendar.get('Status', 'Unknown')
            print(f"- {name} (ステータス: {status})")
        
        return [cal['Name'] for cal in calendars]
        
    except Exception as e:
        print(f"カレンダー一覧取得エラー: {e}")
        return []

# 実行
available_calendars = list_available_calendars()
```

**Change Calendarの作成:**
```python
def create_change_calendar(calendar_name: str, ics_content: str):
    """Change Calendarを作成"""
    
    import boto3
    
    ssm = boto3.client('ssm')
    
    try:
        response = ssm.create_document(
            Content=ics_content,
            Name=calendar_name,
            DocumentType='ChangeCalendar',
            DocumentFormat='TEXT',
            Tags=[
                {
                    'Key': 'Purpose',
                    'Value': 'Japanese Holidays'
                },
                {
                    'Key': 'CreatedBy',
                    'Value': 'HolidayCalendarTool'
                }
            ]
        )
        
        print(f"Change Calendar作成成功: {calendar_name}")
        return response
        
    except Exception as e:
        print(f"Change Calendar作成エラー: {e}")
        return None

# 使用例
from src.ics_generator import ICSGenerator

generator = ICSGenerator()
ics_content = generator.generate_ics_content()
create_change_calendar("japanese-holidays-2024", ics_content)
```

### 2. リージョン設定の問題

#### 症状
- 異なるリージョンのリソースにアクセスできない
- 予期しないリージョンでリソースが作成される

#### 対処法

**リージョン設定の確認:**
```python
import boto3

def check_region_settings():
    """リージョン設定の確認"""
    
    # 現在のセッション情報
    session = boto3.Session()
    
    print("=== AWS設定情報 ===")
    print(f"デフォルトリージョン: {session.region_name}")
    print(f"プロファイル: {session.profile_name}")
    
    # 利用可能なリージョン
    ec2 = session.client('ec2')
    regions = ec2.describe_regions()
    
    print(f"\n利用可能なリージョン: {len(regions['Regions'])}個")
    for region in regions['Regions'][:5]:  # 最初の5個を表示
        print(f"- {region['RegionName']}")
    
    # SSMが利用可能なリージョンをチェック
    ssm_regions = []
    for region in ['us-east-1', 'us-west-2', 'ap-northeast-1', 'eu-west-1']:
        try:
            ssm = session.client('ssm', region_name=region)
            ssm.describe_parameters(MaxResults=1)
            ssm_regions.append(region)
        except Exception:
            pass
    
    print(f"\nSSM利用可能リージョン: {ssm_regions}")

check_region_settings()
```

**明示的なリージョン指定:**
```python
from src.aws_client import SSMChangeCalendarClient

# 明示的にリージョンを指定
client = SSMChangeCalendarClient(
    region_name='ap-northeast-1',  # 東京リージョン
    profile_name='my-profile'
)

# 環境変数での指定
import os
os.environ['AWS_DEFAULT_REGION'] = 'ap-northeast-1'
```

---

## インストール・セットアップ問題

### 1. Python環境関連

#### Python バージョンが古い

**症状:**
```
SyntaxError: invalid syntax
TypeError: 'type' object is not subscriptable
```

**原因:** Python 3.7以下を使用している

**解決方法:**
```bash
# Python バージョン確認
python --version

# Python 3.8以上のインストール
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-pip

# macOS (Homebrew)
brew install python@3.11

# Windows
# https://www.python.org/downloads/ からダウンロード

# 仮想環境を新しいPythonで作成
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### 仮想環境の問題

**症状:**
```
ModuleNotFoundError: No module named 'boto3'
```

**原因:** 仮想環境が有効化されていない、または依存関係が未インストール

**解決方法:**
```bash
# 仮想環境の確認
echo $VIRTUAL_ENV

# 仮想環境の有効化
source .venv/bin/activate  # Linux/macOS
# または
.venv\Scripts\activate     # Windows

# 依存関係の再インストール
pip install --upgrade pip
pip install -r requirements.txt

# インストール確認
pip list | grep -E "(boto3|icalendar|click)"
```

### 2. 依存関係インストール問題

#### パッケージビルドエラー

**症状:**
```
ERROR: Failed building wheel for some-package
error: Microsoft Visual C++ 14.0 is required
```

**解決方法:**

**Windows:**
```powershell
# Visual Studio Build Tools のインストール
# https://visualstudio.microsoft.com/visual-cpp-build-tools/

# または、プリコンパイル済みパッケージの使用
pip install --only-binary=all -r requirements.txt
```

**Linux:**
```bash
# 開発ツールのインストール
# Ubuntu/Debian
sudo apt install build-essential python3-dev

# CentOS/RHEL
sudo yum groupinstall "Development Tools"
sudo yum install python3-devel
```

**macOS:**
```bash
# Xcode Command Line Tools のインストール
xcode-select --install

# または Homebrew でツールチェーンをインストール
brew install gcc
```

#### ネットワーク関連のインストールエラー

**症状:**
```
WARNING: Retrying (Retry(total=4, connect=None, read=None, redirect=None, status=None))
ERROR: Could not find a version that satisfies the requirement
```

**解決方法:**
```bash
# プロキシ設定
pip install --proxy http://proxy.company.com:8080 -r requirements.txt

# タイムアウト延長
pip install --timeout 300 -r requirements.txt

# 代替インデックスの使用
pip install -i https://pypi.douban.com/simple/ -r requirements.txt

# オフラインインストール（事前にパッケージをダウンロード）
pip download -r requirements.txt -d ./packages
pip install --find-links ./packages --no-index -r requirements.txt
```

### 3. 設定ファイル問題

#### 設定ファイルが見つからない

**症状:**
```
ConfigurationError: Configuration file not found
```

**解決方法:**
```bash
# デフォルト設定ファイルの作成
mkdir -p ~/.aws-ssm-calendar
cat > ~/.aws-ssm-calendar/config.json << 'EOF'
{
  "aws": {
    "region": "ap-northeast-1",
    "profile": null
  },
  "calendar": {
    "default_timezone": "Asia/Tokyo",
    "exclude_sunday_holidays": true
  },
  "output": {
    "directory": "./output"
  }
}
EOF

# 設定ファイルパスの明示的指定
python main.py --config ~/.aws-ssm-calendar/config.json holidays
```

#### JSON形式エラー

**症状:**
```
JSONDecodeError: Expecting ',' delimiter
```

**解決方法:**
```bash
# JSON形式の検証
python -m json.tool ~/.aws-ssm-calendar/config.json

# 設定ファイルの修正例
cat > ~/.aws-ssm-calendar/config.json << 'EOF'
{
  "aws": {
    "region": "ap-northeast-1"
  }
}
EOF

# オンラインJSON検証ツールの使用
# https://jsonlint.com/
```

### 4. ファイル・ディレクトリ権限問題

#### 権限不足エラー

**症状:**
```
PermissionError: [Errno 13] Permission denied
```

**解決方法:**
```bash
# ディレクトリ権限の確認
ls -la ~/.aws-ssm-calendar/

# 権限の修正
chmod 755 ~/.aws-ssm-calendar/
chmod 644 ~/.aws-ssm-calendar/config.json

# 出力ディレクトリの作成・権限設定
mkdir -p ./output
chmod 755 ./output

# 所有者の変更（必要な場合）
sudo chown -R $USER:$USER ~/.aws-ssm-calendar/
```

#### ディスク容量不足

**症状:**
```
OSError: [Errno 28] No space left on device
```

**解決方法:**
```bash
# ディスク使用量確認
df -h
du -sh ~/.aws-ssm-calendar/

# 不要ファイルの削除
rm -rf ~/.aws-ssm-calendar/cache/*
rm -rf ~/.aws-ssm-calendar/logs/*

# キャッシュサイズ制限の設定
# config.json に追加
{
  "cache": {
    "max_size_mb": 50,
    "cleanup_enabled": true
  }
}
```

### 5. 環境変数問題

#### 環境変数が認識されない

**症状:**
```
AWS credentials not found
```

**解決方法:**
```bash
# 環境変数の確認
env | grep AWS
echo $AWS_PROFILE
echo $AWS_DEFAULT_REGION

# 環境変数の設定
export AWS_PROFILE="your-profile"
export AWS_DEFAULT_REGION="ap-northeast-1"

# 永続的な設定
echo 'export AWS_PROFILE="your-profile"' >> ~/.bashrc
source ~/.bashrc

# Windows PowerShell
$env:AWS_PROFILE = "your-profile"
[Environment]::SetEnvironmentVariable("AWS_PROFILE", "your-profile", "User")
```

### 6. パス・モジュール問題

#### モジュールが見つからない

**症状:**
```
ModuleNotFoundError: No module named 'src'
ImportError: attempted relative import with no known parent package
```

**解決方法:**
```bash
# 正しいディレクトリから実行
cd /path/to/aws-ssm-calendar-generator
python main.py holidays

# PYTHONPATHの設定
export PYTHONPATH="${PYTHONPATH}:/path/to/aws-ssm-calendar-generator"

# 開発モードでのインストール
pip install -e .

# __init__.py ファイルの確認
ls -la src/__init__.py
```

### 7. 文字エンコーディング問題

#### 文字化け・エンコーディングエラー

**症状:**
```
UnicodeDecodeError: 'utf-8' codec can't decode byte
UnicodeEncodeError: 'ascii' codec can't encode character
```

**解決方法:**
```bash
# ロケール設定の確認
locale
echo $LANG

# UTF-8ロケールの設定
export LANG=ja_JP.UTF-8
export LC_ALL=ja_JP.UTF-8

# Windows
chcp 65001

# Python環境での文字エンコーディング設定
export PYTHONIOENCODING=utf-8

# 設定ファイルでのエンコーディング指定
{
  "output": {
    "encoding": "utf-8"
  }
}
```

### 8. セキュリティ・ファイアウォール問題

#### ネットワーク接続がブロックされる

**症状:**
```
ConnectionError: HTTPSConnectionPool
SSLError: certificate verify failed
```

**解決方法:**
```bash
# プロキシ設定
export HTTP_PROXY="http://proxy.company.com:8080"
export HTTPS_PROXY="http://proxy.company.com:8080"
export NO_PROXY="localhost,127.0.0.1"

# SSL証明書の問題
pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt

# 企業ファイアウォール環境
# IT部門に以下のURLへのアクセス許可を依頼
# - https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv
# - https://pypi.org/
# - AWS API エンドポイント (*.amazonaws.com)
```

### 9. 診断・修復ツール

#### 自動診断スクリプト

```bash
#!/bin/bash
# auto_diagnosis.sh - 自動診断・修復スクリプト

echo "=== 自動診断・修復ツール ==="

# 1. Python環境チェック
echo "1. Python環境チェック"
if python --version | grep -q "3\.[89]\|3\.1[0-9]"; then
    echo "✓ Python バージョン OK"
else
    echo "✗ Python バージョンが古い"
    echo "  推奨: Python 3.8以上をインストールしてください"
fi

# 2. 仮想環境チェック
echo "2. 仮想環境チェック"
if [ -n "$VIRTUAL_ENV" ]; then
    echo "✓ 仮想環境 有効"
else
    echo "⚠ 仮想環境 無効"
    echo "  推奨: 仮想環境を有効化してください"
    echo "  コマンド: source .venv/bin/activate"
fi

# 3. 依存関係チェック
echo "3. 依存関係チェック"
missing_packages=()
for package in boto3 icalendar click requests chardet pytz python-dateutil; do
    if python -c "import $package" 2>/dev/null; then
        echo "✓ $package インストール済み"
    else
        echo "✗ $package 未インストール"
        missing_packages+=($package)
    fi
done

if [ ${#missing_packages[@]} -gt 0 ]; then
    echo "  修復: 不足パッケージをインストールします"
    pip install "${missing_packages[@]}"
fi

# 4. 設定ファイルチェック
echo "4. 設定ファイルチェック"
config_file="$HOME/.aws-ssm-calendar/config.json"
if [ -f "$config_file" ]; then
    if python -m json.tool "$config_file" >/dev/null 2>&1; then
        echo "✓ 設定ファイル OK"
    else
        echo "✗ 設定ファイル 形式エラー"
        echo "  修復: デフォルト設定ファイルを作成します"
        mkdir -p "$(dirname "$config_file")"
        cat > "$config_file" << 'EOF'
{
  "aws": {
    "region": "ap-northeast-1"
  },
  "calendar": {
    "default_timezone": "Asia/Tokyo"
  }
}
EOF
    fi
else
    echo "⚠ 設定ファイル 未作成"
    echo "  修復: デフォルト設定ファイルを作成します"
    mkdir -p "$(dirname "$config_file")"
    cat > "$config_file" << 'EOF'
{
  "aws": {
    "region": "ap-northeast-1"
  },
  "calendar": {
    "default_timezone": "Asia/Tokyo"
  }
}
EOF
fi

# 5. ディレクトリ権限チェック
echo "5. ディレクトリ権限チェック"
for dir in "$HOME/.aws-ssm-calendar" "./output"; do
    if [ -d "$dir" ]; then
        if [ -w "$dir" ]; then
            echo "✓ $dir 書き込み可能"
        else
            echo "✗ $dir 書き込み不可"
            echo "  修復: 権限を修正します"
            chmod 755 "$dir"
        fi
    else
        echo "⚠ $dir 存在しない"
        echo "  修復: ディレクトリを作成します"
        mkdir -p "$dir"
        chmod 755 "$dir"
    fi
done

echo "=== 診断・修復完了 ==="
```

#### 環境リセットスクリプト

```bash
#!/bin/bash
# reset_environment.sh - 環境リセットスクリプト

echo "=== 環境リセット ==="
echo "警告: この操作により設定とキャッシュが削除されます"
read -p "続行しますか? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "キャンセルしました"
    exit 1
fi

# 1. 仮想環境の削除・再作成
echo "1. 仮想環境のリセット"
deactivate 2>/dev/null || true
rm -rf .venv
python -m venv .venv
source .venv/bin/activate

# 2. 依存関係の再インストール
echo "2. 依存関係の再インストール"
pip install --upgrade pip
pip install -r requirements.txt

# 3. 設定・キャッシュの削除
echo "3. 設定・キャッシュのクリア"
rm -rf ~/.aws-ssm-calendar/cache/*
rm -rf ~/.aws-ssm-calendar/logs/*

# 4. デフォルト設定の作成
echo "4. デフォルト設定の作成"
mkdir -p ~/.aws-ssm-calendar
cat > ~/.aws-ssm-calendar/config.json << 'EOF'
{
  "aws": {
    "region": "ap-northeast-1"
  },
  "calendar": {
    "default_timezone": "Asia/Tokyo",
    "exclude_sunday_holidays": true
  },
  "output": {
    "directory": "./output"
  },
  "cache": {
    "enabled": true,
    "ttl_days": 30
  }
}
EOF

# 5. 動作確認
echo "5. 動作確認"
python main.py --help >/dev/null 2>&1 && echo "✓ 基本動作 OK" || echo "✗ 基本動作 NG"

echo "=== リセット完了 ==="
echo "次のコマンドで動作確認してください:"
echo "  python main.py holidays"
```

---

## よくある質問 (FAQ)

### Q1: 祝日データはどのくらいの頻度で更新すべきですか？

**A:** 内閣府は通常2月頃に翌年の祝日を正式発表します。以下の頻度での更新を推奨します：

- **月1回**: 定期的な更新（月初めに実行）
- **2月**: 翌年の祝日発表時期なので必須
- **手動**: 祝日法改正などの特別な場合

```python
# 自動更新スケジュールの例
from datetime import date

def should_update_holidays():
    today = date.today()
    
    # 月初めまたは2月は更新
    if today.day == 1 or today.month == 2:
        return True
    
    return False

if should_update_holidays():
    holidays = JapaneseHolidays()
    holidays.refresh_data()
```

### Q2: AWS Change Calendarの制限はありますか？

**A:** 以下の制限があります：

- **最大イベント数**: 1つのChange Calendarあたり1,000イベント
- **ファイルサイズ**: 最大1MB
- **リージョン制限**: Change Calendarはリージョン固有のリソース

**対策:**
```python
# 年単位でChange Calendarを分割
def create_yearly_calendars(start_year: int, end_year: int):
    for year in range(start_year, end_year + 1):
        calendar_name = f"japanese-holidays-{year}"
        # 年ごとに個別のChange Calendarを作成
```

### Q3: 大量のイベント処理時のメモリ使用量を抑えるには？

**A:** 以下の方法でメモリ使用量を最適化できます：

```python
# 1. 監視機能を無効化
holidays = JapaneseHolidays(enable_monitoring=False)

# 2. バッチ処理
def process_in_batches(years: list, batch_size: int = 3):
    for i in range(0, len(years), batch_size):
        batch = years[i:i + batch_size]
        # バッチごとに処理
        for year in batch:
            # 処理
            pass
        # ガベージコレクション
        import gc
        gc.collect()

# 3. 必要最小限のデータのみ保持
current_year = date.today().year
relevant_years = range(current_year, current_year + 3)
```

### Q4: タイムゾーンの扱いで注意点はありますか？

**A:** 以下の点に注意してください：

- **日本の祝日**: 常にAsia/Tokyoタイムゾーンで処理
- **AWS Change Calendar**: UTCで保存されるが、表示時にローカルタイムゾーンに変換
- **ICSファイル**: タイムゾーン情報を明示的に含める

```python
# タイムゾーン設定の例
from datetime import datetime
import pytz

# 日本時間での処理
jst = pytz.timezone('Asia/Tokyo')
holiday_datetime = jst.localize(datetime(2024, 1, 1, 0, 0, 0))

# UTC変換
utc_datetime = holiday_datetime.astimezone(pytz.UTC)
```

### Q5: プロキシ環境での使用方法は？

**A:** 以下の方法でプロキシ設定を行います：

```python
import os

# 環境変数でプロキシ設定
os.environ['HTTP_PROXY'] = 'http://proxy.company.com:8080'
os.environ['HTTPS_PROXY'] = 'http://proxy.company.com:8080'

# 認証が必要な場合
os.environ['HTTP_PROXY'] = 'http://username:password@proxy.company.com:8080'

# プロキシ除外設定
os.environ['NO_PROXY'] = 'localhost,127.0.0.1,.company.com'
```

### Q6: 複数のAWSアカウントで使用する場合は？

**A:** プロファイルを使い分けます：

```bash
# 複数プロファイルの設定
aws configure --profile production
aws configure --profile development
```

```python
# プロファイル指定での使用
from src.aws_client import SSMChangeCalendarClient

# 本番環境
prod_client = SSMChangeCalendarClient(
    region_name='us-east-1',
    profile_name='production'
)

# 開発環境
dev_client = SSMChangeCalendarClient(
    region_name='us-west-2',
    profile_name='development'
)
```

---

## デバッグツール

### 1. システム診断ツール

```python
def comprehensive_system_diagnosis():
    """包括的なシステム診断"""
    
    import sys
    import os
    from datetime import date
    
    print("=== システム診断レポート ===")
    print(f"実行日時: {datetime.now()}")
    print(f"Python バージョン: {sys.version}")
    print(f"作業ディレクトリ: {os.getcwd()}")
    print()
    
    # 1. 祝日システムの診断
    print("1. 祝日システム診断")
    try:
        from src.japanese_holidays import JapaneseHolidays
        holidays = JapaneseHolidays()
        
        # 基本機能テスト
        test_date = date(2024, 1, 1)
        is_holiday = holidays.is_holiday(test_date)
        holiday_name = holidays.get_holiday_name(test_date)
        
        print(f"   ✓ 基本機能: 正常 ({test_date} = {holiday_name})")
        
        # 統計情報
        stats = holidays.get_stats()
        print(f"   ✓ データ統計: {stats['total']}件 ({stats['min_year']}-{stats['max_year']})")
        
        # キャッシュファイル
        cache_path = holidays.cache_file
        if os.path.exists(cache_path):
            cache_size = os.path.getsize(cache_path)
            print(f"   ✓ キャッシュ: {cache_size} bytes")
        else:
            print("   ⚠ キャッシュファイルなし")
            
    except Exception as e:
        print(f"   ✗ 祝日システムエラー: {e}")
    
    print()
    
    # 2. AWS接続診断
    print("2. AWS接続診断")
    try:
        import boto3
        from botocore.exceptions import NoCredentialsError
        
        session = boto3.Session()
        credentials = session.get_credentials()
        
        if credentials:
            print(f"   ✓ 認証情報: 設定済み")
            print(f"   ✓ リージョン: {session.region_name}")
            
            # SSM接続テスト
            ssm = session.client('ssm')
            response = ssm.describe_parameters(MaxResults=1)
            print(f"   ✓ SSM接続: 正常")
            
        else:
            print("   ✗ 認証情報: 未設定")
            
    except NoCredentialsError:
        print("   ✗ AWS認証情報が見つかりません")
    except Exception as e:
        print(f"   ✗ AWS接続エラー: {e}")
    
    print()
    
    # 3. 依存関係診断
    print("3. 依存関係診断")
    required_packages = [
        'icalendar', 'boto3', 'requests', 'chardet', 
        'click', 'pytz', 'python-dateutil'
    ]
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"   ✓ {package}: インストール済み")
        except ImportError:
            print(f"   ✗ {package}: 未インストール")
    
    print()
    
    # 4. ファイルシステム診断
    print("4. ファイルシステム診断")
    
    # 出力ディレクトリ
    output_dir = "./output"
    if os.path.exists(output_dir):
        if os.access(output_dir, os.W_OK):
            print(f"   ✓ 出力ディレクトリ: {output_dir} (書き込み可能)")
        else:
            print(f"   ✗ 出力ディレクトリ: {output_dir} (書き込み不可)")
    else:
        print(f"   ⚠ 出力ディレクトリ: {output_dir} (存在しない)")
    
    # キャッシュディレクトリ
    cache_dir = os.path.expanduser("~/.aws-ssm-calendar/cache")
    if os.path.exists(cache_dir):
        print(f"   ✓ キャッシュディレクトリ: 存在")
    else:
        print(f"   ⚠ キャッシュディレクトリ: 存在しない")
    
    print("\n=== 診断完了 ===")

# 実行
comprehensive_system_diagnosis()
```

### 2. パフォーマンス測定ツール

```python
import time
import tracemalloc
from datetime import date

def performance_benchmark():
    """パフォーマンスベンチマーク"""
    
    print("=== パフォーマンスベンチマーク ===")
    
    # メモリ使用量の追跡開始
    tracemalloc.start()
    
    from src.japanese_holidays import JapaneseHolidays
    
    # 1. 初期化時間
    start_time = time.time()
    holidays = JapaneseHolidays()
    init_time = time.time() - start_time
    
    current, peak = tracemalloc.get_traced_memory()
    print(f"初期化時間: {init_time:.3f}秒")
    print(f"初期化後メモリ: {current / 1024 / 1024:.2f} MB")
    
    # 2. 祝日判定速度
    test_dates = [date(2024, 1, 1), date(2024, 5, 3), date(2024, 12, 31)]
    
    start_time = time.time()
    for _ in range(1000):
        for test_date in test_dates:
            holidays.is_holiday(test_date)
    search_time = (time.time() - start_time) / (1000 * len(test_dates))
    
    print(f"祝日判定速度: {search_time * 1000:.3f}ms/回")
    
    # 3. 年間データ取得速度
    start_time = time.time()
    year_holidays = holidays.get_holidays_by_year(2024)
    year_fetch_time = time.time() - start_time
    
    print(f"年間データ取得: {year_fetch_time:.3f}秒 ({len(year_holidays)}件)")
    
    # 4. ICS生成速度
    from src.ics_generator import ICSGenerator
    
    start_time = time.time()
    generator = ICSGenerator(holidays)
    events = generator.convert_holidays_to_events(year_holidays)
    ics_content = generator.generate_ics_content()
    ics_time = time.time() - start_time
    
    print(f"ICS生成時間: {ics_time:.3f}秒 ({len(ics_content)} bytes)")
    
    # 最終メモリ使用量
    current, peak = tracemalloc.get_traced_memory()
    print(f"最大メモリ使用量: {peak / 1024 / 1024:.2f} MB")
    
    tracemalloc.stop()
    
    print("=== ベンチマーク完了 ===")

# 実行
performance_benchmark()
```

### 3. ログ解析ツール

```python
import re
from datetime import datetime
from collections import Counter

def analyze_application_logs(log_file_path: str):
    """アプリケーションログの解析"""
    
    if not os.path.exists(log_file_path):
        print(f"ログファイルが見つかりません: {log_file_path}")
        return
    
    print(f"=== ログ解析: {log_file_path} ===")
    
    error_patterns = {
        'network_error': r'NetworkError|ConnectionError|TimeoutError',
        'encoding_error': r'EncodingError|UnicodeDecodeError',
        'aws_error': r'AWSError|ClientError|NoCredentialsError',
        'file_error': r'FileNotFoundError|PermissionError'
    }
    
    error_counts = Counter()
    warning_counts = Counter()
    total_lines = 0
    
    with open(log_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            total_lines += 1
            
            # エラーパターンの検出
            for error_type, pattern in error_patterns.items():
                if re.search(pattern, line, re.IGNORECASE):
                    error_counts[error_type] += 1
            
            # 警告の検出
            if 'WARNING' in line or 'WARN' in line:
                warning_counts['warnings'] += 1
    
    print(f"総行数: {total_lines}")
    print(f"警告数: {warning_counts.get('warnings', 0)}")
    
    if error_counts:
        print("\nエラー統計:")
        for error_type, count in error_counts.most_common():
            print(f"  {error_type}: {count}件")
    else:
        print("エラーは検出されませんでした")
    
    # 最近のエラーを表示
    print("\n最近のエラー (最大5件):")
    with open(log_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        error_lines = [line for line in lines[-100:] if 'ERROR' in line]
        
        for line in error_lines[-5:]:
            print(f"  {line.strip()}")

# 使用例
analyze_application_logs("application.log")
```

---

## サポート情報

### 問題報告時に含めるべき情報

1. **システム情報**
   - OS とバージョン
   - Python バージョン
   - 依存パッケージのバージョン

2. **エラー情報**
   - 完全なエラーメッセージ
   - スタックトレース
   - 再現手順

3. **設定情報**
   - AWS リージョン
   - 使用しているプロファイル
   - 環境変数の設定

4. **ログファイル**
   - アプリケーションログ
   - AWS CLI ログ（該当する場合）

### 情報収集スクリプト

```python
def collect_support_info():
    """サポート用情報収集"""
    
    import sys
    import platform
    import pkg_resources
    
    info = {
        'timestamp': datetime.now().isoformat(),
        'system': {
            'os': platform.system(),
            'os_version': platform.version(),
            'python_version': sys.version,
            'architecture': platform.architecture()
        },
        'packages': {},
        'aws_config': {},
        'application_status': {}
    }
    
    # パッケージバージョン
    required_packages = ['icalendar', 'boto3', 'requests', 'chardet', 'click', 'pytz']
    for package in required_packages:
        try:
            version = pkg_resources.get_distribution(package).version
            info['packages'][package] = version
        except:
            info['packages'][package] = 'not installed'
    
    # AWS設定
    try:
        import boto3
        session = boto3.Session()
        info['aws_config']['region'] = session.region_name
        info['aws_config']['profile'] = session.profile_name
    except:
        info['aws_config']['error'] = 'AWS SDK not available'
    
    # アプリケーション状態
    try:
        from src.japanese_holidays import JapaneseHolidays
        holidays = JapaneseHolidays()
        stats = holidays.get_stats()
        info['application_status']['holiday_data'] = stats
    except Exception as e:
        info['application_status']['error'] = str(e)
    
    return info

# 実行してJSONで出力
import json
support_info = collect_support_info()
print(json.dumps(support_info, indent=2, ensure_ascii=False))
```

### 連絡先とリソース

- **GitHub Issues**: プロジェクトのGitHubリポジトリでIssueを作成
- **ドキュメント**: `docs/` ディレクトリ内の各種ドキュメント
- **サンプルコード**: `examples/` ディレクトリ内のサンプル

### 既知の問題と回避策

1. **内閣府サーバーの一時的な障害**
   - 回避策: キャッシュデータの利用
   - 対処: 数時間後に再試行

2. **AWS リージョン間でのChange Calendar同期**
   - 制限: Change Calendarはリージョン固有
   - 対処: リージョンごとに個別作成

3. **大量データ処理時のメモリ不足**
   - 回避策: バッチ処理の実装
   - 対処: 監視機能の無効化

これらの情報を参考に、問題の解決を図ってください。解決しない場合は、上記の情報収集スクリプトの結果と共にサポートにお問い合わせください。