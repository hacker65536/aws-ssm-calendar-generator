# 設計書

## 概要

AWS SSM Change Calendar 休業日スケジュール管理ツールは、日本の祝日を効率的にAWS Systems Manager Change Calendarに設定するためのモジュラーPythonアプリケーションとして設計されています。このシステムの主要目的は、内閣府の公式祝日データを自動取得し、これをAWS SSM Change Calendarの休業日スケジュールとして設定することです。また、生成された休業日スケジュールをICSファイルとしてエクスポートし、標準的なカレンダーアプリケーションでも利用できるようにします。

## アーキテクチャ

### 高レベルアーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                    ユーザーインターフェース層                │
├─────────────────────────────────────────────────────────────┤
│  CLIコマンド (src/cli.py)                                  │
│  ├── exportコマンド                                        │
│  ├── holidaysコマンド                                      │
│  ├── check-holidayコマンド                                 │
│  ├── refresh-holidaysコマンド                              │
│  └── list-calendarsコマンド                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   ビジネスロジック層                        │
├─────────────────────────────────────────────────────────────┤
│  ICSジェネレーター (src/ics_generator.py)                  │
│  ├── カレンダー作成と管理                                  │
│  ├── イベント生成とフォーマット                            │
│  └── ファイル出力処理                                      │
├─────────────────────────────────────────────────────────────┤
│  日本祝日マネージャー (src/japanese_holidays.py)           │
│  ├── 祝日データ取得とキャッシュ                            │
│  ├── 日付検証と検索                                        │
│  └── 統計と管理                                            │
├─────────────────────────────────────────────────────────────┤
│  日時ハンドラー (src/datetime_handler.py)                  │
│  ├── タイムゾーン変換                                      │
│  ├── 日付解析とフォーマット                                │
│  └── ICS日時フォーマット                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   データアクセス層                          │
├─────────────────────────────────────────────────────────────┤
│  AWS SSMクライアント (src/aws_client.py)                   │
│  ├── Change Calendar取得                                   │
│  ├── カレンダー状態管理                                    │
│  └── AWS認証処理                                           │
├─────────────────────────────────────────────────────────────┤
│  設定マネージャー (src/config.py)                          │
│  ├── 設定管理                                              │
│  ├── ファイルベース設定                                    │
│  └── 環境変数サポート                                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    外部システム                            │
├─────────────────────────────────────────────────────────────┤
│  AWS Systems Manager                                        │
│  ├── Change Calendar API                                   │
│  └── ドキュメント取得                                      │
├─────────────────────────────────────────────────────────────┤
│  内閣府                                                     │
│  ├── 公式祝日CSV                                           │
│  └── HTTPSデータエンドポイント                             │
├─────────────────────────────────────────────────────────────┤
│  ローカルファイルシステム                                  │
│  ├── 設定ファイル                                          │
│  ├── キャッシュストレージ                                  │
│  └── 出力ICSファイル                                       │
└─────────────────────────────────────────────────────────────┘
```

## Requirements Mapping to Architecture

### Requirements Coverage Analysis

**要件1 (日本祝日データ取得・管理)** → **Japanese Holidays Manager (src/japanese_holidays.py)**
- 受入基準1: 内閣府公式CSV取得 → `fetch_official_data()`
- 受入基準2: UTF-8変換 → `detect_encoding()`, `convert_to_utf8()`
- 受入基準3: 当年以降フィルタ（内閣府CSVの最終年まで） → `filter_current_year_onwards()`
- 受入基準4: キャッシュ管理 → `save_to_cache()`, `load_from_cache()`
- 受入基準5: データインテグリティ → エラーハンドリング機構

**要件2 (AWS SSM Change Calendar用ICS変換)** → **ICS Generator (src/ics_generator.py)**
- 受入基準1: AWS SSM仕様準拠 → `create_aws_ssm_calendar()`
- 受入基準2: 当年以降データ変換（内閣府CSVの最終年まで） → `convert_holidays_to_events()`
- 受入基準3: UTF-8エンコーディング → `save_to_file()`
- 受入基準4: 必須プロパティ → `generate_holiday_event()`
- 受入基準5: AWS SSM互換性 → AWS専用ICS構造
- 受入基準6: 日曜祝日フィルタリング → `filter_sunday_holidays()`

**要件3 (ICSファイル解析・可視化)** → **ICS Analyzer (src/calendar_analyzer.py)**
- 受入基準1: ICS解析機能 → `parse_ics_file()`
- 受入基準2: 人間可読形式出力 → `format_human_readable()`
- 受入基準3: 統計情報表示 → `analyze_events()`
- 受入基準4: エラー検出 → `validate_ics_format()`
- 受入基準5: 複数形式対応 → `export_json()`, `export_csv()`
- 受入基準6: 簡易出力形式 → 簡易フォーマット機能

**要件4 (ICSファイル比較・差分表示)** → **ICS Comparator (src/calendar_analyzer.py - 拡張)**
- 受入基準1: ファイル比較機能 → `compare_ics_files()`
- 受入基準2: 時系列ソート → 日付順ソート機能
- 受入基準3: 変更種別表示 → `detect_event_changes()`
- 受入基準4: 詳細差分表示 → `compare_event_properties()`
- 受入基準5: サマリー情報 → 統計情報生成

**要件4.2 (イベント意味的Diff形式)** → **Event Semantic Diff Comparator**
- EARS準拠受入基準 → `generate_event_semantic_diff()`
- diff記号表示 → カラー出力、記号分類
- 変更検出ロジック → UID主キー + 副キー照合

**要件4.3 (AWS Change Calendar統合比較)** → **AWS Change Calendar Integration Comparator**
- AWS API統合 → `fetch_aws_change_calendar()`
- データ正規化 → `normalize_aws_calendar_to_ics()`
- 統合比較 → AWS専用比較ロジック

## Components and Interfaces

### Core Components

#### 1. CLI Interface (src/cli.py)

**Purpose**: Provides command-line interface for all user interactions, implementing requirements through user-friendly commands with optimized default settings for clean output

**Requirements-Driven Command Design**:

**要件1対応コマンド**:
- `holidays`: 祝日データ表示・管理 (要件1, 要件4.1)
  - `--year`指定なし: 当年以降の全祝日データ（内閣府CSVの最終年まで、日曜祝日除外）を表示
    - 年別グループ化表示、統計情報表示
    - ICS出力時は`convert_holidays_to_events()`使用
    - 表示とICS出力で一貫した日曜祝日フィルタリング
  - `--year`指定あり: 指定年の祝日のみを表示（従来通り、日曜祝日除外）
    - `filter_sunday_holidays()`適用後の表示
    - 除外された日曜祝日の明示的表示
    - `add_japanese_holidays_for_year(year)`使用
- `check-holiday`: 特定日付の祝日確認 (要件1)
- `refresh-holidays`: 祝日データ強制更新 (要件1)

**要件2対応コマンド**:
- `export`: ICS形式でのエクスポート (要件2)
- `--exclude-sunday-holidays`: 日曜祝日フィルタリングオプション (要件2.6)

**要件3対応コマンド**:
- `analyze-ics`: ICSファイル解析・可視化 (要件3)
- `--format`: 出力形式選択 (human/json/csv/simple) (要件3.5)

**要件4対応コマンド**:
- `compare-ics`: ICSファイル比較 (要件4)
- `semantic-diff`: 意味的diff表示 (要件4.2)
- `compare-aws`: AWS Change Calendar比較 (要件4.3)

**CLI Default Configuration Design (要件4対応)**:

**デフォルト設定戦略**:
- **ユーザビリティ優先**: 一般ユーザーにはクリーンで読みやすい出力
- **段階的詳細化**: 必要に応じてオプション指定で詳細レベルを上げる
- **後方互換性**: 既存ユーザーは適切なオプションで従来の出力を維持

**デフォルト設定値**:
```python
DEFAULT_CLI_SETTINGS = {
    'log_level': 'WARNING',      # 警告以上のメッセージのみ
    'log_format': 'simple',      # シンプルなテキスト形式
    'enable_monitoring': False,  # システムモニタリング無効
    'debug_mode': False         # デバッグモード無効
}
```

**段階的詳細化レベル**:
```python
# レベル1: 通常使用（デフォルト）
python main.py holidays
# 出力: クリーンな祝日リストのみ

# レベル2: 詳細情報
python main.py --log-level INFO holidays
# 出力: 祝日リスト + 基本的な処理情報

# レベル3: モニタリング付き
python main.py --log-level INFO --enable-monitoring holidays
# 出力: 祝日リスト + 処理情報 + システムメトリクス

# レベル4: 開発者向け（最大詳細）
python main.py --debug --log-level DEBUG --log-format structured --enable-monitoring holidays
# 出力: 全ての詳細情報 + JSON構造化ログ
```

**Interface Design**:
```python
@click.group()
@click.option('--config', '-c', help='Configuration file path')
@click.option('--profile', '-p', help='AWS profile name')
@click.option('--region', '-r', help='AWS region')
@click.option('--debug', is_flag=True, help='Enable debug mode with verbose logging')
@click.option('--log-level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']), 
              default='WARNING', help='Set logging level (default: WARNING)')
@click.option('--log-format', type=click.Choice(['simple', 'detailed', 'json', 'structured']), 
              default='simple', help='Set log format (default: simple)')
@click.option('--enable-monitoring', is_flag=True, help='Enable performance and system monitoring')
def cli(ctx, config, profile, region, debug, log_level, log_format, enable_monitoring):
    """Main CLI entry point with optimized default settings"""
    
    # ログ設定の初期化
    logging_manager = setup_logging(
        log_level=getattr(LogLevel, log_level),
        log_format=getattr(LogFormat, log_format.upper()),
        enable_performance_monitoring=enable_monitoring,
        enable_system_monitoring=enable_monitoring,
        debug_mode=debug
    )

@cli.command()
def export(ctx, calendar_name, output, timezone, include_holidays, holidays_year, exclude_sunday_holidays):
    """Export command implementing 要件2 with all acceptance criteria"""

@cli.command()
def analyze_ics(ctx, file_path, format, output):
    """ICS analysis command implementing 要件3"""

@cli.command()
def compare_ics(ctx, file1, file2, format, output):
    """ICS comparison command implementing 要件4"""

@cli.command()
def semantic_diff(ctx, file1, file2, color, output):
    """Semantic diff command implementing 要件4.2"""

@cli.command()
def compare_aws(ctx, local_file, calendar_name, region):
    """AWS Change Calendar comparison implementing 要件4.3"""
```

**出力例比較**:

*デフォルト出力（レベル1）*:
```
Japanese holidays for 2025:
  2025-01-01 (Wed) - 元日
  2025-01-13 (Mon) - 成人の日
  2025-02-11 (Tue) - 建国記念の日
  ...
```

*詳細出力（レベル4）*:
```json
{
  "timestamp": "2025-10-30T03:05:45.954925",
  "level": "INFO",
  "logger": "src.logging_config",
  "message": "System monitoring started (interval: 60.0s)",
  ...
}
Japanese holidays for 2025:
  2025-01-01 (Wed) - 元日
  2025-01-13 (Mon) - 成人の日
  ...
{
  "timestamp": "2025-10-30T03:05:46.960467",
  "level": "INFO",
  "message": "System metrics - CPU: 25.9%, Memory: 55.9%",
  ...
}
```

**移行ガイド設計**:
```python
class CLIMigrationHelper:
    """v1.0.x以前のユーザー向け移行支援"""
    
    @staticmethod
    def show_migration_help():
        """従来の詳細出力を得るためのオプション説明"""
        print("""
        v1.1.0以降の変更点:
        
        従来の詳細出力が必要な場合:
        --log-level INFO --enable-monitoring を追加
        
        例:
        旧: python main.py holidays
        新: python main.py --log-level INFO --enable-monitoring holidays
        
        開発・デバッグ時:
        --debug --log-format structured --enable-monitoring を使用
        """)
```

#### 2. ICS Generator (src/ics_generator.py)

**Purpose**: 要件2の実装 - AWS SSM Change Calendar用ICS変換

**Core Requirements Implementation**:
- **AWS SSM仕様準拠**: PRODID: -//AWS//Change Calendar 1.0//EN
- **当年以降データ変換**: JapaneseHolidaysからの祝日データ変換（内閣府CSVの最終年まで）
- **文字エンコーディング**: UTF-8エンコーディング対応
- **イベントプロパティ**: UID、DTSTAMP、SUMMARY、DTSTART、DTEND必須プロパティ
- **AWS SSM互換性**: Change Calendarでの正常インポート保証
- **日曜祝日フィルタリング**: 日曜日に該当する祝日を除外するオプション（デフォルト：除外）

**Key Methods**:
```python
class ICSGenerator:
    def __init__(self, japanese_holidays: JapaneseHolidays, exclude_sunday_holidays: bool = True):
        """AWS SSM Change Calendar用ICSジェネレーター初期化"""
        
    def create_aws_ssm_calendar(self) -> Calendar:
        """AWS SSM Change Calendar専用カレンダー作成"""
        
    def add_timezone_definition(self) -> None:
        """Asia/Tokyoタイムゾーン定義追加"""
        
    def filter_sunday_holidays(self, holidays: List[Tuple[date, str]]) -> List[Tuple[date, str]]:
        """日曜祝日フィルタリング（要件2.6対応）"""
        
    def convert_holidays_to_events(self, holidays: List[Tuple[date, str]]) -> List[Event]:
        """祝日データをICSイベントに変換"""
        
    def generate_holiday_event(self, holiday_date: date, holiday_name: str) -> Event:
        """個別祝日イベント生成"""
        
    def generate_ics_content(self, exclude_sunday_holidays: bool = True) -> str:
        """AWS SSM互換ICS形式文字列生成"""
        
    def save_to_file(self, filepath: str) -> None:
        """UTF-8エンコーディングでファイル保存"""
```

**AWS SSM ICS Structure**:
```python
# カレンダーヘッダー
PRODID: -//AWS//Change Calendar 1.0//EN
X-CALENDAR-TYPE: DEFAULT_OPEN
X-WR-CALDESC: 
X-CALENDAR-CMEVENTS: DISABLED
X-WR-TIMEZONE: Asia/Tokyo

# タイムゾーン定義
VTIMEZONE: Asia/Tokyo (+09:00 JST)

# 祝日イベント
UID: jp-holiday-{YYYYMMDD}@aws-ssm-change-calendar
DTSTART;TZID=Asia/Tokyo: {YYYYMMDD}T000000
DTEND;TZID=Asia/Tokyo: {YYYYMMDD+1}T000000
SUMMARY: 日本の祝日: {祝日名}
DESCRIPTION: 日本の国民の祝日: {祝日名}
CATEGORIES: Japanese-Holiday
```

**日曜祝日フィルタリング設計**:
```python
def filter_sunday_holidays(self, holidays: List[Tuple[date, str]]) -> List[Tuple[date, str]]:
    """
    日曜祝日フィルタリング（要件2.6）
    
    Design Rationale:
    - デフォルトで日曜祝日を除外（ビジネス運用での実用性重視）
    - ユーザー選択可能（include_sunday_holidays オプション）
    - 統計情報で除外数を報告（透明性確保）
    """
    if not self.exclude_sunday_holidays:
        return holidays
    
    filtered_holidays = []
    excluded_count = 0
    
    for holiday_date, holiday_name in holidays:
        if holiday_date.weekday() == 6:  # Sunday = 6
            excluded_count += 1
            self.logger.info(f"日曜祝日除外: {holiday_date} {holiday_name}")
        else:
            filtered_holidays.append((holiday_date, holiday_name))
    
    self.stats['sunday_holidays_excluded'] = excluded_count
    return filtered_holidays
```

**Design Decisions and Rationales**:

1. **AWS SSM専用ICS形式採用**:
   - **決定**: PRODID: -//AWS//Change Calendar 1.0//EN を使用
   - **理由**: AWS SSM Change Calendarでの確実な互換性確保
   - **影響**: 標準ICSとは異なるが、主要対象システムでの動作を優先

2. **日曜祝日フィルタリングのデフォルト除外**:
   - **決定**: デフォルトで日曜祝日を除外、オプションで包含可能
   - **理由**: ビジネス運用では日曜日は既に非稼働日のため、祝日として重複管理する必要性が低い
   - **影響**: ファイルサイズ削減、運用の簡素化、ユーザー選択の柔軟性確保

3. **UTF-8エンコーディング統一**:
   - **決定**: 全ICS出力をUTF-8で統一
   - **理由**: 日本語祝日名の正確な表示、国際標準への準拠
   - **影響**: 文字化け防止、多言語環境での互換性向上

4. **イベント重複防止機構**:
   - **決定**: _events_converted フラグによる重複変換防止
   - **理由**: 同一インスタンスでの複数回変換時のデータ整合性確保
   - **影響**: メモリ効率向上、ファイルサイズ最適化

#### 3. ICS Analyzer (src/calendar_analyzer.py)

**Purpose**: 要件3の実装 - ICSファイル解析・可視化

**Core Requirements Implementation**:
- **ICS解析機能**: ICSファイルを構造化データとして解析
- **人間可読形式出力**: 日付順ソート、表形式表示
- **統計情報表示**: 総イベント数、対象期間、祝日種類別集計
- **エラー検出**: 構文エラー、不正データの検出・報告
- **複数形式対応**: 標準出力、JSON、CSV形式での出力

**Key Methods**:
```python
class ICSAnalyzer:
    def __init__(self):
        """ICSファイル解析器初期化"""
        
    def parse_ics_file(self, filepath: str) -> Dict:
        """ICSファイル解析"""
        
    def extract_events(self, calendar: Calendar) -> List[Dict]:
        """イベント情報抽出"""
        
    def analyze_events(self, events: List[Dict]) -> Dict:
        """イベント分析・統計生成"""
        
    def format_human_readable(self, analysis: Dict) -> str:
        """人間可読形式フォーマット"""
        
    def export_json(self, analysis: Dict) -> str:
        """JSON形式エクスポート"""
        
    def export_csv(self, events: List[Dict]) -> str:
        """CSV形式エクスポート"""
        
    def validate_ics_format(self, calendar: Calendar) -> List[str]:
        """ICS形式検証・エラー検出"""
```

**Analysis Output Structure**:
```python
{
    'file_info': {
        'filepath': str,
        'file_size': int,
        'total_events': int,
        'date_range': {'start': date, 'end': date}
    },
    'events': [
        {
            'uid': str,
            'summary': str,
            'dtstart': datetime,
            'dtend': datetime,
            'description': str,
            'categories': str
        }
    ],
    'statistics': {
        'total_events': int,
        'holiday_types': Dict[str, int],
        'yearly_distribution': Dict[int, int],
        'monthly_distribution': Dict[int, int]
    },
    'validation_errors': List[str]
}
```

**Design Decisions and Rationales**:

1. **icalendarライブラリ採用**:
   - **決定**: Python icalendarライブラリを解析エンジンとして使用
   - **理由**: RFC 5545完全準拠、豊富な機能、安定性
   - **影響**: 高精度な解析、標準準拠の検証機能

2. **複数出力形式サポート**:
   - **決定**: 人間可読、JSON、CSV、簡易形式の4つの出力形式
   - **理由**: 用途に応じた最適な形式選択（確認用、プログラム処理用、データ分析用）
   - **影響**: ユーザビリティ向上、他システムとの連携容易性

3. **ISO8601期間表示**:
   - **決定**: 終日イベントは日付のみ、時刻指定イベントは完全形式
   - **理由**: 情報の簡潔性と正確性のバランス
   - **影響**: 可読性向上、国際標準準拠

4. **エラー検出の段階的処理**:
   - **決定**: 致命的エラーは処理停止、軽微なエラーは警告継続
   - **理由**: 部分的に破損したファイルでも有用な情報を抽出
   - **影響**: 実用性向上、柔軟なエラーハンドリング

#### 4. ICS Comparator (src/calendar_analyzer.py - 拡張)

**Purpose**: 要件4の実装 - ICSファイル比較・差分表示

**Core Requirements Implementation**:
- **ファイル比較機能**: 2つのICSファイルをイベントレベルで差分検出
- **時系列ソート**: 比較結果を日付順にソートして表示
- **変更種別表示**: 追加・削除・変更されたイベントを明確に区別
- **詳細差分表示**: 変更されたイベントの具体的な変更内容（プロパティレベル）
- **サマリー情報**: 変更の概要統計（追加X件、削除Y件、変更Z件）

**Key Methods**:
```python
class ICSAnalyzer:
    def compare_ics_files(self, file1_path: str, file2_path: str) -> Dict:
        """2つのICSファイル比較"""
        
    def detect_event_changes(self, events1: List[Dict], events2: List[Dict]) -> Dict:
        """イベントレベルでの変更検出"""
        
    def compare_event_properties(self, event1: Dict, event2: Dict) -> List[str]:
        """イベントプロパティの詳細比較"""
        
    def format_comparison_result(self, comparison: Dict) -> str:
        """比較結果の人間可読形式フォーマット"""
        
    def export_comparison_json(self, comparison: Dict) -> str:
        """比較結果のJSON形式エクスポート"""
```

**Comparison Algorithm**:
- 主キー: UID（イベント一意識別子）による照合
- 副キー: DTSTART（開始日時）による照合（UID不一致時）
- プロパティ比較: SUMMARY、DTSTART、DTEND、DESCRIPTION、CATEGORIES

**Output Structure**:
```python
{
    'file1_info': {'filepath': str, 'total_events': int},
    'file2_info': {'filepath': str, 'total_events': int},
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

**Event Format**:
```
BEGIN:VEVENT
SUMMARY:🎌 {holiday_name} | {change_window_title}
DTSTART;VALUE=DATE:{YYYYMMDD}
DTEND;VALUE=DATE:{YYYYMMDD+1}
DTSTAMP:{current_utc_timestamp}
UID:{unique_identifier}
CATEGORIES:{event_category}
DESCRIPTION:{detailed_description}
END:VEVENT
```

#### 3. Japanese Holidays Manager (src/japanese_holidays.py)

**Purpose**: 要件1の実装 - 日本祝日データの取得・管理・キャッシュ

**Core Requirements Implementation**:
- **一次ソース取得**: 内閣府公式CSV（https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv）
- **エンコーディング変換**: Shift_JIS/CP932 → UTF-8自動変換
- **当年以降フィルタ**: 現在日時基準での祝日データ抽出（内閣府CSVの最終年まで）
- **キャッシュ管理**: 30日間有効期限付きローカルキャッシュ（`~/.aws-ssm-calendar/cache/japanese_holidays.csv`）
- **データインテグリティ**: 公式データ取得失敗時の処理停止

**Key Methods**:
```python
class JapaneseHolidays:
    def __init__(self):
        """初期化とキャッシュ確認"""
        
    def fetch_official_data(self) -> str:
        """内閣府公式CSVの取得"""
        
    def detect_encoding(self, raw_data: bytes) -> str:
        """エンコーディング自動検出（Shift_JIS → CP932 → UTF-8）"""
        
    def convert_to_utf8(self, data: str, source_encoding: str) -> str:
        """UTF-8形式への変換"""
        
    def filter_current_year_onwards(self, holidays: List[Holiday]) -> List[Holiday]:
        """当年以降の祝日データフィルタリング（内閣府CSVの最終年まで）"""
        
    def save_to_cache(self, holidays: List[Holiday]) -> None:
        """UTF-8形式でのキャッシュ保存"""
        
    def load_from_cache(self) -> Optional[List[Holiday]]:
        """キャッシュからの読み込み"""
        
    def is_cache_valid(self) -> bool:
        """キャッシュ有効期限確認（30日）"""
```

**Data Processing Flow**:
```
起動
 ↓
キャッシュ確認 (~/.aws-ssm-calendar/cache/japanese_holidays.csv)
 ↓
有効期限チェック (30日)
 ↓
[期限切れ/存在しない場合]
 ↓
内閣府HPからCSVダウンロード (HTTPS)
 ↓
エンコーディング自動検出 (Shift_JIS → CP932 → UTF-8)
 ↓
UTF-8変換
 ↓
現在日時取得
 ↓
当年以降祝日データ抽出（内閣府CSVの最終年まで）
 ↓
UTF-8形式でキャッシュ保存
 ↓
メモリ上でデータ利用可能
```

**Error Handling Strategy**:
```python
class HolidayDataError(Exception):
    """祝日データ関連エラー"""
    
class NetworkError(HolidayDataError):
    """ネットワーク接続エラー"""
    
class EncodingError(HolidayDataError):
    """文字エンコーディングエラー"""
    
class DataIntegrityError(HolidayDataError):
    """データ整合性エラー"""
```

**Performance Requirements**:
- 初回ダウンロード: 3秒以内
- キャッシュ読み込み: 50ms以内  
- メモリ使用量: 100KB以内（当年以降、内閣府CSVの最終年まで保持）

**Design Decisions and Rationales**:

1. **内閣府公式CSVを一次ソースとして採用**:
   - **決定**: https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv を唯一のデータソース
   - **理由**: 政府公式データの信頼性、法的根拠の確実性
   - **影響**: データ品質保証、法的コンプライアンス確保

2. **30日間キャッシュ戦略**:
   - **決定**: ローカルキャッシュ30日間有効期限
   - **理由**: 祝日データの更新頻度（年1-2回）とネットワーク効率のバランス
   - **影響**: パフォーマンス向上、ネットワーク負荷軽減

3. **エンコーディング自動検出順序**:
   - **決定**: Shift_JIS → CP932 → UTF-8 の順序で検出
   - **理由**: 内閣府CSVの実際のエンコーディング傾向に基づく最適化
   - **影響**: 文字化け防止、変換成功率向上

4. **当年以降フィルタリング**:
   - **決定**: システム実行時の現在年から内閣府CSVに含まれる最終年までの祝日を抽出
   - **理由**: Change Calendarの運用目的（将来の変更制御）に特化、利用可能な全期間のデータ活用
   - **影響**: データサイズ最適化、処理効率向上、運用目的との整合性、将来計画の包括的サポート

#### 4. AWS SSM Client (src/aws_client.py)

**Purpose**: Interfaces with AWS Systems Manager for Change Calendar data

**Key Methods**:
- `get_change_calendar()`: Retrieve calendar document
- `list_change_calendars()`: Enumerate available calendars
- `get_calendar_state()`: Check current calendar state

**Authentication**:
- AWS SDK credential chain
- Profile-based authentication
- Environment variable support
- IAM role assumption

**Required Permissions**:
```json
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
```

#### 5. DateTime Handler (src/datetime_handler.py)

**Purpose**: Manages timezone conversions and date formatting

**Key Methods**:
- `parse_datetime()`: Parse various datetime formats
- `convert_timezone()`: Convert between timezones
- `format_for_ics()`: Generate ICS-compliant datetime strings
- `parse_aws_datetime()`: Handle AWS-specific formats

**Timezone Support**:
- UTC as default timezone
- Configurable default timezone
- Automatic timezone detection
- ICS standard compliance

#### 6. Configuration Manager (src/config.py)

**Purpose**: Manages application configuration and settings

**Configuration Structure**:
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

## Data Models

### Holiday Data Model

```python
@dataclass
class Holiday:
    date: date
    name: str
    category: str = "national"
    
class HolidayCollection:
    holidays: Dict[date, Holiday]
    stats: HolidayStats
    cache_info: CacheInfo
```

### Change Window Data Model

```python
@dataclass
class ChangeWindow:
    title: str
    start_time: datetime
    end_time: datetime
    description: str
    location: str
    calendar_name: str
    
class ChangeCalendar:
    name: str
    windows: List[ChangeWindow]
    state: str  # 'OPEN' or 'CLOSED'
```

### ICS Event Data Model

```python
@dataclass
class ICSEvent:
    summary: str
    start: Union[datetime, date]
    end: Union[datetime, date]
    description: str
    uid: str
    categories: List[str]
    all_day: bool = False
```

## Error Handling

### Error Categories

#### 1. Network Errors
- **Connection Timeout**: Retry with exponential backoff
- **DNS Resolution**: Fallback to cached data
- **SSL Certificate**: Validate and report specific issues
- **HTTP Errors**: Handle 4xx/5xx responses appropriately

#### 2. Authentication Errors
- **AWS Credentials**: Provide clear setup instructions
- **Permission Denied**: List required IAM permissions
- **Token Expiry**: Automatic refresh when possible

#### 3. Data Processing Errors
- **Invalid CSV Format**: Skip malformed rows, continue processing
- **Date Parsing**: Use fallback parsers, log warnings
- **Encoding Issues**: Try multiple encodings automatically

#### 4. File System Errors
- **Permission Denied**: Attempt alternative locations
- **Disk Full**: Provide clear error message with space requirements
- **Path Not Found**: Create directories automatically when possible

### Error Recovery Strategies

```python
class ErrorHandler:
    def handle_network_error(self, error):
        if isinstance(error, TimeoutError):
            return self.use_cached_data()
        elif isinstance(error, ConnectionError):
            return self.use_fallback_data()
        else:
            raise error
    
    def handle_aws_error(self, error):
        if error.response['Error']['Code'] == 'AccessDenied':
            self.show_permission_help()
        elif error.response['Error']['Code'] == 'DocumentNotFound':
            self.suggest_calendar_names()
        raise error
```

## Testing Strategy

### Unit Testing

**Coverage Areas**:
- Holiday date calculations
- Timezone conversions
- ICS format generation
- Configuration management
- Error handling paths

**Test Data**:
- Known holiday dates (2020-2030)
- Various timezone scenarios
- Edge cases (leap years, DST transitions)
- Invalid input formats

### Integration Testing

**Test Scenarios**:
- End-to-end ICS generation
- AWS API integration (with mocking)
- File system operations
- CLI command execution

**Mock Strategies**:
- AWS API responses
- Network requests
- File system operations
- System time/timezone

### Performance Testing

**Benchmarks**:
- Holiday lookup: < 1ms per query
- ICS generation: < 100ms for yearly data
- Cache loading: < 50ms
- Memory usage: < 10MB total

**Load Testing**:
- Multiple concurrent holiday queries
- Large date range processing
- Bulk ICS file generation

## Security Considerations

### Data Protection

**Sensitive Data Handling**:
- AWS credentials stored securely
- No logging of authentication tokens
- Cache files with restricted permissions
- Input validation for all user data

**Network Security**:
- HTTPS-only connections
- Certificate validation enabled
- Timeout configurations
- No credential transmission in URLs

### Input Validation

```python
class InputValidator:
    def validate_date(self, date_string: str) -> date:
        """Validate and parse date input"""
        
    def validate_calendar_name(self, name: str) -> str:
        """Sanitize calendar name input"""
        
    def validate_file_path(self, path: str) -> Path:
        """Prevent path traversal attacks"""
```

### Access Control

**File Permissions**:
- Cache files: 600 (user read/write only)
- Configuration files: 600 (user read/write only)
- Output files: 644 (user read/write, others read)

**AWS Permissions**:
- Principle of least privilege
- Read-only access to required resources
- No write permissions to AWS resources

## Performance Optimization

### Caching Strategy

**Multi-Level Caching**:
1. **Memory Cache**: In-process holiday data
2. **File Cache**: Persistent holiday storage
3. **HTTP Cache**: Respect cache headers from Cabinet Office

**Cache Invalidation**:
- Time-based expiry (30 days)
- Manual refresh capability
- Automatic refresh on startup if expired

### Memory Management

**Optimization Techniques**:
- Lazy loading of holiday data
- Efficient data structures (dict for O(1) lookups)
- Minimal object creation in hot paths
- Garbage collection hints for large operations

### I/O Optimization

**File Operations**:
- Streaming for large files
- Atomic writes for cache updates
- Batch operations where possible
- Asynchronous I/O for network requests (future enhancement)

## Deployment and Distribution

### Package Structure

```
aws-ssm-calendar-generator/
├── src/
│   ├── __init__.py
│   ├── cli.py
│   ├── ics_generator.py
│   ├── japanese_holidays.py
│   ├── calendar_analyzer.py
│   ├── aws_client.py
│   ├── datetime_handler.py
│   └── config.py
├── docs/
├── tests/
├── setup.py
├── requirements.txt
└── README.md
```

### Installation Methods

**PyPI Package**:
```bash
pip install aws-ssm-calendar-ics
```

**Development Installation**:
```bash
git clone <repository>
cd aws-ssm-calendar-ics
pip install -e .
```

**Docker Container** (future enhancement):
```dockerfile
FROM python:3.11-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
ENTRYPOINT ["python", "main.py"]
```

### Configuration Management

**Configuration Hierarchy**:
1. Command-line arguments (highest priority)
2. Environment variables
3. User configuration file
4. System configuration file
5. Default values (lowest priority)

**Environment Variables**:
- `AWS_SSM_CALENDAR_CONFIG`: Configuration file path
- `AWS_SSM_CALENDAR_CACHE_DIR`: Cache directory override
- `AWS_SSM_CALENDAR_DEFAULT_TIMEZONE`: Default timezone

## Future Enhancements

### Planned Features

1. **Web Interface**: Browser-based calendar management
2. **API Server**: REST API for programmatic access
3. **Webhook Support**: Real-time calendar updates
4. **Multiple Holiday Sources**: Support for regional holidays
5. **Calendar Synchronization**: Two-way sync with calendar services
6. **Advanced Filtering**: Complex event filtering and transformation
7. **Notification System**: Email/SMS alerts for upcoming events
8. **Multi-language Support**: Internationalization for UI and holidays

### Technical Improvements

1. **Asynchronous Processing**: Non-blocking I/O operations
2. **Database Backend**: Optional database storage for large deployments
3. **Monitoring Integration**: Metrics and health checks
4. **Container Orchestration**: Kubernetes deployment support
5. **CI/CD Pipeline**: Automated testing and deployment
6. **Performance Monitoring**: Application performance metrics
##
#### 4.2 Event Semantic Diff Comparator (src/calendar_analyzer.py - 拡張)

**Purpose**: 要件4.2の実装 - イベント意味的Diff形式での比較表示

**Core Requirements Implementation**:
- **イベント意味的比較**: ICSイベント単位での構造化差分検出
- **多段階照合**: UID主キー + DTSTART/SUMMARY副キー照合
- **変更種別検出**: 追加・削除・変更・移動・期間変更の分類
- **日付順ソート**: DTSTART基準での時系列表示
- **統計情報**: 変更種別ごとの詳細統計
- **カラー出力**: 変更種別別のANSI カラーコード表示

**Key Methods**:
```python
class ICSAnalyzer:  # 既存クラスに追加
    def generate_event_semantic_diff(self, file1: str, file2: str) -> Dict:
        """イベント意味的Diff生成"""
        
    def detect_event_changes_detailed(self, events1: List[Dict], events2: List[Dict]) -> Dict:
        """詳細なイベント変更検出"""
        
    def classify_event_changes(self, event1: Dict, event2: Dict) -> str:
        """イベント変更種別分類"""
        
    def format_semantic_diff(self, diff_data: Dict, use_color: bool = False) -> str:
        """意味的Diff出力フォーマット"""
        
    def export_semantic_diff_file(self, diff_content: str, output_path: str) -> bool:
        """意味的Diff結果ファイル出力"""
```

**Event Matching Algorithm**:
```python
def detect_event_changes_detailed(self, events1: List[Dict], events2: List[Dict]) -> Dict:
    # UID主キー照合
    events1_by_uid = {event['uid']: event for event in events1 if event['uid']}
    events2_by_uid = {event['uid']: event for event in events2 if event['uid']}
    
    changes = {
        'added': [],      # ファイル2にのみ存在
        'deleted': [],    # ファイル1にのみ存在
        'modified': [],   # プロパティ変更
        'moved': [],      # 日時変更
        'duration_changed': []  # 期間変更
    }
    
    # 詳細変更分析
    for uid in events1_by_uid:
        if uid in events2_by_uid:
            change_type = self.classify_event_changes(
                events1_by_uid[uid], 
                events2_by_uid[uid]
            )
            if change_type != 'unchanged':
                changes[change_type].append({
                    'uid': uid,
                    'event1': events1_by_uid[uid],
                    'event2': events2_by_uid[uid],
                    'changes': self._get_property_changes(
                        events1_by_uid[uid], 
                        events2_by_uid[uid]
                    )
                })
    
    return changes
```

**Change Classification Logic**:
```python
def classify_event_changes(self, event1: Dict, event2: Dict) -> str:
    # 日時変更チェック
    if (event1['dtstart'] != event2['dtstart'] or 
        event1['dtend'] != event2['dtend']):
        
        # 期間長変更チェック
        duration1 = event1['dtend'] - event1['dtstart']
        duration2 = event2['dtend'] - event2['dtstart']
        
        if duration1 != duration2:
            return 'duration_changed'
        else:
            return 'moved'
    
    # プロパティ変更チェック
    if (event1['summary'] != event2['summary'] or
        event1['description'] != event2['description'] or
        event1['categories'] != event2['categories']):
        return 'modified'
    
    return 'unchanged'
```

**Semantic Diff Output Structure**:
```python
{
    'file1_info': {'filepath': str, 'events': int},
    'file2_info': {'filepath': str, 'events': int},
    'statistics': {
        'added': int,
        'deleted': int,
        'modified': int,
        'moved': int,
        'duration_changed': int,
        'unchanged': int
    },
    'changes': {
        'added': List[Dict],
        'deleted': List[Dict],
        'modified': List[Dict],
        'moved': List[Dict],
        'duration_changed': List[Dict]
    },
    'sorted_changes': List[Dict]  # 日付順ソート済み
}
```

**Color Scheme**:
```python
SEMANTIC_DIFF_COLORS = {
    'added': '\033[32m',      # Green (+)
    'deleted': '\033[31m',    # Red (-)
    'modified': '\033[33m',   # Yellow (~)
    'moved': '\033[34m',      # Blue (=)
    'duration_changed': '\033[35m',  # Magenta (Δ)
    'header': '\033[1m',      # Bold
    'reset': '\033[0m'        # Reset
}
```

**Expected Output Format**:
```
=== ICSイベント意味的差分 ===
ファイル1: japanese_holidays_2025.ics (37イベント)
ファイル2: japanese_holidays_2025_exclude_sunday.ics (33イベント)

=== 変更統計 ===
+ 追加: 0 イベント
- 削除: 4 イベント  
~ 変更: 0 イベント
= 移動: 0 イベント
Δ 期間変更: 0 イベント

=== 詳細差分（日付順） ===

- [削除] 2025-02-23 天皇誕生日
  UID: jp-holiday-20250223@aws-ssm-change-calendar
  期間: 2025-02-23 00:00 - 2025-02-24 00:00
  説明: 国民の祝日（日曜日）

- [削除] 2025-05-04 みどりの日  
  UID: jp-holiday-20250504@aws-ssm-change-calendar
  期間: 2025-05-04 00:00 - 2025-05-05 00:00
  説明: 国民の祝日（日曜日）
```

**CLI Integration**:
```bash
# イベント意味的diff比較
python -m src.cli compare --format=semantic file1.ics file2.ics

# カラー出力付き
python -m src.cli compare --format=semantic --color file1.ics file2.ics

# ファイル出力
python -m src.cli compare --format=semantic --output=semantic_diff.txt file1.ics file2.ics
```#### 4.3 AWS
 Change Calendar Integration Comparator (src/calendar_analyzer.py - 拡張)

**Purpose**: 要件4.3の実装 - AWS Change Calendar統合比較

**Core Requirements Implementation**:
- **AWS Change Calendar取得**: SSM GetDocumentによるカレンダー内容取得
- **データ正規化**: AWS Change Calendar → ICS形式変換
- **統合比較**: ローカルICSファイルとAWS Change Calendarの意味的比較
- **状態情報**: Change Calendarの現在状態（OPEN/CLOSED）取得
- **一括比較**: 複数のChange Calendarとの比較
- **AWS専用出力**: Change Calendar比較専用フォーマット

**Key Methods**:
```python
class ICSAnalyzer:  # 既存クラスに追加
    def compare_with_aws_change_calendar(self, local_file: str, calendar_name: str, region: str = 'us-east-1') -> Dict:
        """AWS Change Calendarとの比較"""
        
    def fetch_aws_change_calendar(self, calendar_name: str, region: str = 'us-east-1') -> Dict:
        """AWS Change Calendar取得"""
        
    def normalize_aws_calendar_to_ics(self, aws_calendar_data: str) -> List[Dict]:
        """AWS Change Calendar → ICS形式正規化"""
        
    def get_change_calendar_state(self, calendar_name: str, region: str = 'us-east-1') -> str:
        """Change Calendar状態取得"""
        
    def format_aws_comparison_result(self, comparison: Dict, use_color: bool = False) -> str:
        """AWS比較結果フォーマット"""
        
    def batch_compare_aws_calendars(self, local_file: str, calendar_names: List[str], region: str = 'us-east-1') -> Dict:
        """複数AWS Change Calendar一括比較"""
```

**AWS Integration Architecture**:
```python
# AWS SSM Client設定
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

class AWSChangeCalendarClient:
    def __init__(self, region: str = 'us-east-1'):
        self.region = region
        self.ssm_client = boto3.client('ssm', region_name=region)
    
    def get_calendar_document(self, calendar_name: str) -> Dict:
        """Change Calendarドキュメント取得"""
        
    def list_change_calendars(self) -> List[Dict]:
        """Change Calendar一覧取得"""
        
    def get_calendar_state(self, calendar_name: str) -> str:
        """Change Calendar状態取得"""
```

**Data Normalization Process**:
```python
def normalize_aws_calendar_to_ics(self, aws_calendar_data: str) -> List[Dict]:
    # AWS Change Calendar形式 → ICS Event形式変換
    # 1. AWS Change Calendar JSON解析
    # 2. イベント期間抽出
    # 3. ICS Event辞書形式に変換
    # 4. UID生成（AWS Change Calendar用）
    
    normalized_events = []
    calendar_data = json.loads(aws_calendar_data)
    
    for event in calendar_data.get('events', []):
        normalized_event = {
            'uid': f"aws-change-calendar-{event.get('id', uuid.uuid4())}",
            'summary': event.get('summary', 'AWS Change Calendar Event'),
            'dtstart': self._parse_aws_datetime(event.get('start')),
            'dtend': self._parse_aws_datetime(event.get('end')),
            'description': event.get('description', ''),
            'categories': 'AWS-Change-Calendar'
        }
        normalized_events.append(normalized_event)
    
    return normalized_events
```

**AWS Comparison Output Structure**:
```python
{
    'local_file_info': {'filepath': str, 'events': int},
    'aws_calendar_info': {
        'name': str,
        'region': str,
        'events': int,
        'state': str,  # 'OPEN' or 'CLOSED'
        'last_updated': str
    },
    'comparison_statistics': {
        'local_only': int,
        'aws_only': int,
        'different': int,
        'moved': int,
        'identical': int
    },
    'differences': {
        'local_only': List[Dict],
        'aws_only': List[Dict],
        'different': List[Dict],
        'moved': List[Dict]
    },
    'recommendations': List[str],
    'comparison_date': str
}
```

**Error Handling Strategy**:
```python
class AWSChangeCalendarError(Exception):
    """AWS Change Calendar関連エラー"""
    
class AWSAuthenticationError(AWSChangeCalendarError):
    """AWS認証エラー"""
    
class AWSPermissionError(AWSChangeCalendarError):
    """AWS権限エラー"""
    
class AWSNetworkError(AWSChangeCalendarError):
    """AWSネットワークエラー"""

def handle_aws_errors(self, error: Exception) -> str:
    if isinstance(error, NoCredentialsError):
        return "AWS認証情報が設定されていません。AWS CLIまたは環境変数を設定してください。"
    elif isinstance(error, ClientError):
        error_code = error.response['Error']['Code']
        if error_code == 'AccessDenied':
            return "AWS Change Calendarへのアクセス権限がありません。IAM権限を確認してください。"
        elif error_code == 'DocumentNotFound':
            return "指定されたChange Calendarが見つかりません。カレンダー名を確認してください。"
    return f"AWS API エラー: {error}"
```

**CLI Integration**:
```bash
# AWS Change Calendarとの比較
python -m src.cli compare --aws-calendar japanese-holidays-2025 --region us-east-1 local_file.ics

# 複数Change Calendarとの一括比較
python -m src.cli compare --aws-calendars japanese-holidays-2025,maintenance-windows --region us-east-1 local_file.ics

# Change Calendar状態確認
python -m src.cli aws-status --calendar japanese-holidays-2025 --region us-east-1
```

**Performance Optimization**:
- **Connection Pooling**: boto3セッション再利用
- **Caching**: Change Calendar内容の一時キャッシュ
- **Parallel Processing**: 複数カレンダー比較の並列処理
- **Rate Limiting**: AWS API制限への対応