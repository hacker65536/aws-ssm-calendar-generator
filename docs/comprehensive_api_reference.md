# 🔌 包括的 API リファレンス

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![API Documentation](https://img.shields.io/badge/docs-API%20Reference-green.svg)](docs/comprehensive_api_reference.md)
[![Code Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen.svg)](#)

## 📋 概要

AWS SSM Change Calendar 休業日スケジュール管理ツールの完全なAPI仕様書です。開発者がプログラムからツールを利用するための詳細な技術仕様を提供します。

### 🎯 対象読者
- **アプリケーション開発者**: ツールをライブラリとして組み込みたい方
- **システム統合者**: 既存システムとの連携を実装したい方
- **DevOpsエンジニア**: 自動化スクリプトを作成したい方
- **API利用者**: プログラムから祝日判定機能を使いたい方

### 📚 ドキュメント構成
- **基本API**: 祝日判定、データ取得の基本機能
- **高度なAPI**: ICS生成、AWS統合、比較機能
- **ユーティリティ**: 設定管理、エラーハンドリング
- **拡張機能**: カスタマイズ、プラグイン開発

## 目次

1. [JapaneseHolidays クラス](#japaneseholidays-クラス)
2. [ICSGenerator クラス](#icsgenerator-クラス)
3. [CalendarAnalyzer クラス](#calendaranalyzer-クラス)
4. [SSMChangeCalendarClient クラス](#ssmchangecalendarclient-クラス)
5. [DateTimeHandler クラス](#datetimehandler-クラス)
6. [Config クラス](#config-クラス)
7. [CLI コマンド](#cli-コマンド)
8. [エラーハンドリング](#エラーハンドリング)
9. [使用例とベストプラクティス](#使用例とベストプラクティス)
10. [トラブルシューティング](#トラブルシューティング)

---

## JapaneseHolidays クラス

### 概要

日本の祝日データを管理するクラスです。内閣府の公式データを取得し、効率的な祝日判定機能を提供します。

### インポート

```python
from src.japanese_holidays import JapaneseHolidays
```

### コンストラクタ

#### `__init__(cache_file: Optional[str] = None, enable_monitoring: bool = True)`

**パラメータ:**
- `cache_file` (Optional[str]): キャッシュファイルのパス
- `enable_monitoring` (bool): パフォーマンス監視を有効にするか

**例:**
```python
# デフォルト設定
holidays = JapaneseHolidays()

# カスタムキャッシュパス
holidays = JapaneseHolidays("/custom/path/holidays.csv")

# 監視無効
holidays = JapaneseHolidays(enable_monitoring=False)
```

### 祝日判定メソッド

#### `is_holiday(check_date: date) -> bool`

指定された日付が祝日かどうかを判定します。

**パラメータ:**
- `check_date` (date): 判定対象の日付

**戻り値:**
- `bool`: 祝日の場合True

**例:**
```python
from datetime import date

holidays = JapaneseHolidays()
is_new_year = holidays.is_holiday(date(2024, 1, 1))  # True
```

#### `get_holiday_name(check_date: date) -> Optional[str]`

祝日名を取得します。

**パラメータ:**
- `check_date` (date): 対象日付

**戻り値:**
- `Optional[str]`: 祝日名（祝日でない場合はNone）

**例:**
```python
name = holidays.get_holiday_name(date(2024, 1, 1))  # "元日"
```

### 祝日検索メソッド

#### `get_holidays_in_range(start_date: date, end_date: date) -> List[Tuple[date, str]]`

期間内の祝日一覧を取得します。

**パラメータ:**
- `start_date` (date): 開始日（含む）
- `end_date` (date): 終了日（含む）

**戻り値:**
- `List[Tuple[date, str]]`: (日付, 祝日名)のリスト

**例:**
```python
jan_holidays = holidays.get_holidays_in_range(
    date(2024, 1, 1), 
    date(2024, 1, 31)
)
```

#### `get_holidays_by_year(year: int) -> List[Tuple[date, str]]`

指定年の全祝日を取得します。

**例:**
```python
holidays_2024 = holidays.get_holidays_by_year(2024)
```

#### `get_next_holiday(from_date: Optional[date] = None) -> Optional[Tuple[date, str]]`

次の祝日を取得します。

**例:**
```python
next_holiday = holidays.get_next_holiday()
```

### データ管理メソッド

#### `refresh_data() -> None`

祝日データを強制更新します。

#### `get_stats() -> Dict[str, int]`

統計情報を取得します。

**戻り値構造:**
```python
{
    'total': int,      # 総祝日数
    'years': int,      # 対象年数  
    'min_year': int,   # 最古年
    'max_year': int    # 最新年
}
```

---

## ICSGenerator クラス

### 概要

AWS SSM Change Calendar用のICSファイルを生成するクラスです。日本の祝日統合機能も提供します。

### インポート

```python
from src.ics_generator import ICSGenerator
from src.japanese_holidays import JapaneseHolidays
```

### コンストラクタ

#### `__init__(japanese_holidays: Optional[JapaneseHolidays] = None, exclude_sunday_holidays: bool = True)`

**パラメータ:**
- `japanese_holidays` (Optional[JapaneseHolidays]): 祝日管理インスタンス
- `exclude_sunday_holidays` (bool): 日曜祝日を除外するか

**例:**
```python
# デフォルト設定（日曜祝日除外）
generator = ICSGenerator()

# 日曜祝日を含める
generator = ICSGenerator(exclude_sunday_holidays=False)

# カスタム祝日インスタンス
holidays = JapaneseHolidays()
generator = ICSGenerator(japanese_holidays=holidays)
```

### カレンダー作成メソッド

#### `create_aws_ssm_calendar() -> Calendar`

AWS SSM Change Calendar専用のカレンダーを作成します。

**戻り値:**
- `Calendar`: icalendarライブラリのCalendarオブジェクト

**例:**
```python
generator = ICSGenerator()
calendar = generator.create_aws_ssm_calendar()
```

#### `add_timezone_definition() -> None`

Asia/Tokyoタイムゾーン定義を追加します。

### 祝日統合メソッド

#### `convert_holidays_to_events(holidays: List[Tuple[date, str]]) -> List[Event]`

祝日データをICSイベントに変換します。

**パラメータ:**
- `holidays` (List[Tuple[date, str]]): (日付, 祝日名)のリスト

**戻り値:**
- `List[Event]`: ICSイベントのリスト

#### `generate_holiday_event(holiday_date: date, holiday_name: str) -> Event`

個別祝日イベントを生成します。

**パラメータ:**
- `holiday_date` (date): 祝日の日付
- `holiday_name` (str): 祝日名

**戻り値:**
- `Event`: ICSイベントオブジェクト

### ファイル出力メソッド

#### `generate_ics_content() -> str`

ICS形式の文字列を生成します。

**戻り値:**
- `str`: ICS形式のカレンダーデータ

#### `save_to_file(filepath: str) -> None`

ICSファイルを保存します。

**パラメータ:**
- `filepath` (str): 保存先ファイルパス

**例:**
```python
generator = ICSGenerator()
generator.save_to_file("holidays_2024.ics")
```

### 統計メソッド

#### `get_generation_stats() -> Dict[str, Any]`

生成統計を取得します。

**戻り値構造:**
```python
{
    'total_events': int,
    'holiday_events': int,
    'sunday_holidays_found': int,
    'sunday_holidays_excluded': int,
    'file_size_bytes': int,
    'generation_time_ms': float
}
```

---

## CalendarAnalyzer クラス

### 概要

ICSファイルの解析、比較、可視化機能を提供するクラスです。

### インポート

```python
from src.calendar_analyzer import ICSAnalyzer
```

### コンストラクタ

#### `__init__()`

```python
analyzer = ICSAnalyzer()
```

### ファイル解析メソッド

#### `parse_ics_file(filepath: str) -> Dict`

ICSファイルを解析します。

**パラメータ:**
- `filepath` (str): ICSファイルのパス

**戻り値構造:**
```python
{
    'file_info': {
        'filepath': str,
        'file_size': int,
        'total_events': int,
        'date_range': {'start': date, 'end': date}
    },
    'events': List[Dict],
    'statistics': Dict,
    'validation_errors': List[str]
}
```

#### `analyze_events(events: List[Dict]) -> Dict`

イベント分析を実行します。

### 比較メソッド

#### `compare_ics_files(file1_path: str, file2_path: str) -> Dict`

2つのICSファイルを比較します。

**パラメータ:**
- `file1_path` (str): 比較元ファイル
- `file2_path` (str): 比較先ファイル

**戻り値構造:**
```python
{
    'file1_info': Dict,
    'file2_info': Dict,
    'summary': {
        'added': int,
        'deleted': int,
        'modified': int,
        'unchanged': int
    },
    'changes': {
        'added': List[Dict],
        'deleted': List[Dict],
        'modified': List[Dict]
    }
}
```

#### `generate_event_semantic_diff(file1: str, file2: str) -> Dict`

イベント意味的差分を生成します。

**例:**
```python
analyzer = ICSAnalyzer()
diff_result = analyzer.generate_event_semantic_diff(
    "holidays_2024.ics", 
    "holidays_2025.ics"
)
```

### AWS統合メソッド

#### `compare_with_aws_change_calendar(local_file: str, calendar_name: str, region: str = 'us-east-1') -> Dict`

AWS Change Calendarとの比較を実行します。

**パラメータ:**
- `local_file` (str): ローカルICSファイル
- `calendar_name` (str): AWS Change Calendar名
- `region` (str): AWSリージョン

### 出力フォーマットメソッド

#### `format_human_readable(analysis: Dict) -> str`

人間可読形式でフォーマットします。

#### `export_json(analysis: Dict) -> str`

JSON形式でエクスポートします。

#### `export_csv(events: List[Dict]) -> str`

CSV形式でエクスポートします。

---

## SSMChangeCalendarClient クラス

### 概要

AWS Systems Manager Change Calendarとの連携機能を提供します。

### インポート

```python
from src.aws_client import SSMChangeCalendarClient
```

### コンストラクタ

#### `__init__(region_name: str = 'us-east-1', profile_name: Optional[str] = None)`

**パラメータ:**
- `region_name` (str): AWSリージョン
- `profile_name` (Optional[str]): AWSプロファイル名

**例:**
```python
# デフォルトリージョン
client = SSMChangeCalendarClient()

# カスタムリージョンとプロファイル
client = SSMChangeCalendarClient(
    region_name='ap-northeast-1',
    profile_name='my-profile'
)
```

### Change Calendarメソッド

#### `get_change_calendar(calendar_name: str) -> Dict`

Change Calendarドキュメントを取得します。

**パラメータ:**
- `calendar_name` (str): カレンダー名

**戻り値:**
- `Dict`: カレンダードキュメントデータ

#### `list_change_calendars() -> List[Dict]`

利用可能なChange Calendarを一覧表示します。

#### `get_calendar_state(calendar_name: str) -> str`

カレンダーの現在状態を取得します。

**戻り値:**
- `str`: 'OPEN' または 'CLOSED'

---

## DateTimeHandler クラス

### 概要

日時処理とタイムゾーン変換機能を提供します。

### インポート

```python
from src.datetime_handler import DateTimeHandler
```

### メソッド

#### `parse_datetime(datetime_str: str) -> datetime`

様々な形式の日時文字列を解析します。

#### `convert_timezone(dt: datetime, target_tz: str) -> datetime`

タイムゾーン変換を実行します。

#### `format_for_ics(dt: datetime) -> str`

ICS準拠の日時文字列を生成します。

---

## Config クラス

### 概要

アプリケーション設定を管理します。

### インポート

```python
from src.config import Config
```

### 設定構造

```json
{
    "aws": {
        "region": "us-east-1",
        "profile": null
    },
    "calendar": {
        "default_timezone": "UTC",
        "output_format": "ics"
    },
    "output": {
        "directory": "./output",
        "filename_template": "{calendar_name}_{date}.ics"
    }
}
```

---

## CLI コマンド

### 基本コマンド

#### `holidays`

祝日の表示・エクスポート

```bash
# 今年の祝日を表示
python main.py holidays

# 特定年の祝日
python main.py holidays --year 2024

# ICSファイルにエクスポート
python main.py holidays --year 2024 --output holidays.ics
```

#### `export`

Change CalendarのICSエクスポート

```bash
# 基本エクスポート
python main.py export MyCalendar -o calendar.ics

# 祝日を含める
python main.py export MyCalendar --include-holidays -o calendar.ics
```

#### `check-holiday`

祝日判定

```bash
# 今日をチェック
python main.py check-holiday

# 特定日をチェック
python main.py check-holiday --date 2024-01-01
```

#### `analyze-ics`

ICSファイル解析

```bash
# 基本解析
python main.py analyze-ics holidays.ics

# JSON出力
python main.py analyze-ics holidays.ics --format json
```

#### `compare-ics`

ICSファイル比較

```bash
# 基本比較
python main.py compare-ics file1.ics file2.ics

# 意味的差分
python main.py compare-ics file1.ics file2.ics --format semantic
```

### グローバルオプション

```bash
--config, -c        # 設定ファイルパス
--profile, -p       # AWSプロファイル
--region, -r        # AWSリージョン
--debug             # デバッグモード
--log-level         # ログレベル
--log-format        # ログ形式
--no-monitoring     # 監視無効
```

---

## エラーハンドリング

### エラークラス階層

```python
BaseApplicationError
├── NetworkError
├── EncodingError
├── DataIntegrityError
├── AWSError
├── ConfigurationError
└── FileSystemError
```

### エラーハンドリング例

```python
from src.error_handler import handle_error, NetworkError

@handle_error
def fetch_holidays():
    holidays = JapaneseHolidays()
    return holidays.get_holidays_by_year(2024)

try:
    result = fetch_holidays()
except NetworkError as e:
    print(f"ネットワークエラー: {e}")
    # フォールバック処理
```

---

## 使用例とベストプラクティス

### 1. 営業日計算システム

```python
from datetime import date, timedelta
from src.japanese_holidays import JapaneseHolidays

class BusinessDayCalculator:
    def __init__(self):
        self.holidays = JapaneseHolidays()
    
    def is_business_day(self, check_date: date) -> bool:
        """営業日判定"""
        # 土日チェック
        if check_date.weekday() >= 5:
            return False
        
        # 祝日チェック
        return not self.holidays.is_holiday(check_date)
    
    def add_business_days(self, start_date: date, days: int) -> date:
        """営業日加算"""
        current = start_date
        added = 0
        
        while added < days:
            current += timedelta(days=1)
            if self.is_business_day(current):
                added += 1
        
        return current

# 使用例
calculator = BusinessDayCalculator()
result_date = calculator.add_business_days(date.today(), 5)
print(f"5営業日後: {result_date}")
```

### 2. 祝日統合カレンダー生成

```python
from src.ics_generator import ICSGenerator
from src.japanese_holidays import JapaneseHolidays

def create_comprehensive_calendar(year: int, include_sundays: bool = False):
    """包括的カレンダー生成"""
    
    # 祝日データ取得
    holidays = JapaneseHolidays()
    
    # ICSジェネレーター初期化
    generator = ICSGenerator(
        japanese_holidays=holidays,
        exclude_sunday_holidays=not include_sundays
    )
    
    # カレンダー作成
    calendar = generator.create_aws_ssm_calendar()
    
    # 祝日追加
    year_holidays = holidays.get_holidays_by_year(year)
    events = generator.convert_holidays_to_events(year_holidays)
    
    for event in events:
        calendar.add_component(event)
    
    # ファイル保存
    filename = f"calendar_{year}_{'with' if include_sundays else 'without'}_sundays.ics"
    generator.save_to_file(filename)
    
    # 統計表示
    stats = generator.get_generation_stats()
    print(f"生成完了: {filename}")
    print(f"総イベント数: {stats['total_events']}")
    print(f"ファイルサイズ: {stats['file_size_bytes']} bytes")

# 使用例
create_comprehensive_calendar(2024, include_sundays=True)
```

### 3. AWS Change Calendar同期

```python
from src.aws_client import SSMChangeCalendarClient
from src.calendar_analyzer import ICSAnalyzer

def sync_with_aws_calendar(local_file: str, calendar_name: str):
    """AWS Change Calendarとの同期"""
    
    analyzer = ICSAnalyzer()
    
    # 比較実行
    comparison = analyzer.compare_with_aws_change_calendar(
        local_file, calendar_name
    )
    
    # 差分レポート
    summary = comparison['summary']
    print(f"AWS Change Calendar同期レポート:")
    print(f"追加が必要: {summary['added']}件")
    print(f"削除が必要: {summary['deleted']}件")
    print(f"変更が必要: {summary['modified']}件")
    
    # 推奨アクション
    if summary['added'] > 0:
        print("\n推奨アクション:")
        print("1. ローカルファイルをAWS Change Calendarにアップロード")
        print("2. Change Calendar状態を確認")
    
    return comparison

# 使用例
sync_result = sync_with_aws_calendar(
    "holidays_2024.ics", 
    "japanese-holidays-2024"
)
```

---

## トラブルシューティング

### よくある問題と解決方法

#### 1. ネットワーク接続エラー

**症状:** 祝日データの取得に失敗する

**解決方法:**
```python
from src.japanese_holidays import JapaneseHolidays
from src.error_handler import NetworkError

try:
    holidays = JapaneseHolidays()
    holidays.refresh_data()
except NetworkError:
    print("ネットワーク接続を確認してください")
    print("キャッシュデータを使用します")
```

#### 2. AWS認証エラー

**症状:** Change Calendarにアクセスできない

**解決方法:**
```bash
# AWS認証情報を確認
aws configure list

# プロファイル指定
python main.py export MyCalendar --profile my-profile
```

#### 3. ファイル権限エラー

**症状:** ICSファイルの保存に失敗する

**解決方法:**
```python
import os
from pathlib import Path

# 出力ディレクトリを作成
output_dir = Path("./output")
output_dir.mkdir(parents=True, exist_ok=True)

# 権限確認
if not os.access(output_dir, os.W_OK):
    print(f"書き込み権限がありません: {output_dir}")
```

#### 4. メモリ不足エラー

**症状:** 大量のイベント処理時にメモリ不足

**解決方法:**
```python
# 監視無効でメモリ使用量を削減
holidays = JapaneseHolidays(enable_monitoring=False)

# 年単位での処理
for year in range(2024, 2030):
    year_holidays = holidays.get_holidays_by_year(year)
    # 年ごとに処理
```

### デバッグユーティリティ

#### システム診断

```python
def diagnose_system():
    """システム診断"""
    import sys
    import os
    from src.japanese_holidays import JapaneseHolidays
    
    print("=== システム診断 ===")
    print(f"Python バージョン: {sys.version}")
    print(f"作業ディレクトリ: {os.getcwd()}")
    
    # 祝日システム
    try:
        holidays = JapaneseHolidays()
        stats = holidays.get_stats()
        print(f"祝日データ: {stats['total']}件読み込み済み")
    except Exception as e:
        print(f"祝日システムエラー: {e}")
    
    # AWS接続
    try:
        from src.aws_client import SSMChangeCalendarClient
        client = SSMChangeCalendarClient()
        print("AWS接続: 正常")
    except Exception as e:
        print(f"AWS接続エラー: {e}")

# 実行
diagnose_system()
```

#### パフォーマンス測定

```python
import time
from src.japanese_holidays import JapaneseHolidays

def benchmark_holiday_operations():
    """祝日操作のベンチマーク"""
    holidays = JapaneseHolidays()
    
    # 初期化時間
    start = time.time()
    holidays.refresh_data()
    init_time = time.time() - start
    
    # 検索時間
    start = time.time()
    for _ in range(1000):
        holidays.is_holiday(date(2024, 1, 1))
    search_time = (time.time() - start) / 1000
    
    print(f"初期化時間: {init_time:.3f}秒")
    print(f"検索時間: {search_time:.6f}秒/回")

# 実行
benchmark_holiday_operations()
```

---

## FAQ

### Q: 祝日データはどのくらいの頻度で更新すべきですか？

A: 内閣府は通常2月頃に翌年の祝日を発表します。月1回程度の更新で十分です。

### Q: AWS Change Calendarの制限はありますか？

A: 1つのChange Calendarあたり最大1000イベントまでです。年単位での分割を推奨します。

### Q: 大量のイベント処理時のメモリ使用量を抑えるには？

A: `enable_monitoring=False`でパフォーマンス監視を無効にし、年単位での処理を行ってください。

### Q: タイムゾーンの扱いで注意点はありますか？

A: 日本の祝日は常にAsia/Tokyoタイムゾーンで処理されます。UTC変換は自動的に行われます。

---

## 参考資料

- [内閣府 国民の祝日について](https://www8.cao.go.jp/chosei/shukujitsu/gaiyou.html)
- [AWS Systems Manager Change Calendar](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-change-calendar.html)
- [iCalendar RFC 5545](https://tools.ietf.org/html/rfc5545)
- [Python icalendar ライブラリ](https://icalendar.readthedocs.io/)