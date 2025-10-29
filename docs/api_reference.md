# API リファレンス - 日本の祝日取得機能

## 概要

日本の祝日取得・管理機能のAPI仕様書です。プログラマティックな利用方法を詳しく説明します。

## JapaneseHolidays クラス

### インポート

```python
from src.japanese_holidays import JapaneseHolidays
```

### コンストラクタ

#### `__init__(cache_file: Optional[str] = None)`

日本の祝日管理オブジェクトを初期化します。

**パラメータ:**
- `cache_file` (Optional[str]): キャッシュファイルのパス。省略時はデフォルトパス使用

**例:**
```python
# デフォルトキャッシュパス使用
holidays = JapaneseHolidays()

# カスタムキャッシュパス指定
holidays = JapaneseHolidays("/path/to/custom_cache.csv")
```

**デフォルトキャッシュパス:**
`~/.aws-ssm-calendar/cache/japanese_holidays.csv`

---

### 祝日判定メソッド

#### `is_holiday(check_date: date) -> bool`

指定された日付が日本の祝日かどうかを判定します。

**パラメータ:**
- `check_date` (date): 判定対象の日付

**戻り値:**
- `bool`: 祝日の場合True、平日の場合False

**例:**
```python
from datetime import date

holidays = JapaneseHolidays()

# 元日をチェック
is_new_year = holidays.is_holiday(date(2024, 1, 1))  # True

# 平日をチェック
is_weekday = holidays.is_holiday(date(2024, 1, 2))   # False
```

#### `get_holiday_name(check_date: date) -> Optional[str]`

指定された日付の祝日名を取得します。

**パラメータ:**
- `check_date` (date): 対象日付

**戻り値:**
- `Optional[str]`: 祝日名（祝日でない場合はNone）

**例:**
```python
holidays = JapaneseHolidays()

# 祝日名を取得
name = holidays.get_holiday_name(date(2024, 1, 1))  # "元日"

# 平日の場合
name = holidays.get_holiday_name(date(2024, 1, 2))  # None
```

---

### 祝日検索メソッド

#### `get_holidays_in_range(start_date: date, end_date: date) -> List[Tuple[date, str]]`

指定された期間内の祝日一覧を取得します。

**パラメータ:**
- `start_date` (date): 開始日（含む）
- `end_date` (date): 終了日（含む）

**戻り値:**
- `List[Tuple[date, str]]`: (日付, 祝日名)のタプルリスト（日付順ソート済み）

**例:**
```python
holidays = JapaneseHolidays()

# 2024年1月の祝日を取得
jan_holidays = holidays.get_holidays_in_range(
    date(2024, 1, 1), 
    date(2024, 1, 31)
)
# [(date(2024, 1, 1), '元日'), (date(2024, 1, 8), '成人の日')]

# ゴールデンウィークの祝日を取得
gw_holidays = holidays.get_holidays_in_range(
    date(2024, 4, 29), 
    date(2024, 5, 5)
)
```

#### `get_holidays_by_year(year: int) -> List[Tuple[date, str]]`

指定された年の全祝日を取得します。

**パラメータ:**
- `year` (int): 対象年

**戻り値:**
- `List[Tuple[date, str]]`: (日付, 祝日名)のタプルリスト

**例:**
```python
holidays = JapaneseHolidays()

# 2024年の全祝日を取得
holidays_2024 = holidays.get_holidays_by_year(2024)

# 祝日数を確認
print(f"2024年の祝日数: {len(holidays_2024)}")

# 最初の5つの祝日を表示
for holiday_date, holiday_name in holidays_2024[:5]:
    print(f"{holiday_date}: {holiday_name}")
```

#### `get_next_holiday(from_date: Optional[date] = None) -> Optional[Tuple[date, str]]`

指定日以降の次の祝日を取得します。

**パラメータ:**
- `from_date` (Optional[date]): 基準日（省略時は今日）

**戻り値:**
- `Optional[Tuple[date, str]]`: 次の祝日の(日付, 祝日名)、見つからない場合None

**例:**
```python
holidays = JapaneseHolidays()

# 今日以降の次の祝日
next_holiday = holidays.get_next_holiday()
if next_holiday:
    next_date, next_name = next_holiday
    print(f"次の祝日: {next_date} ({next_name})")

# 特定日以降の次の祝日
next_from_date = holidays.get_next_holiday(date(2024, 6, 1))
```

---

### データ管理メソッド

#### `refresh_data() -> None`

祝日データを強制的に更新します。キャッシュを無視して内閣府から最新データを取得します。

**例:**
```python
holidays = JapaneseHolidays()

# データを強制更新
holidays.refresh_data()
print("祝日データを更新しました")
```

#### `get_stats() -> Dict[str, int]`

読み込み済み祝日データの統計情報を取得します。

**戻り値:**
- `Dict[str, int]`: 統計情報辞書

**統計情報の構造:**
```python
{
    'total': int,      # 総祝日数
    'years': int,      # 対象年数  
    'min_year': int,   # 最古年
    'max_year': int    # 最新年
}
```

**例:**
```python
holidays = JapaneseHolidays()

stats = holidays.get_stats()
print(f"総祝日数: {stats['total']}")
print(f"対象期間: {stats['min_year']}年 - {stats['max_year']}年")
print(f"対象年数: {stats['years']}年")
```

---

## ICSGenerator クラス拡張

### インポート

```python
from src.ics_generator import ICSGenerator
```

### 祝日統合機能

#### `__init__(include_japanese_holidays: bool = False)`

祝日統合機能付きICSジェネレータを初期化します。

**パラメータ:**
- `include_japanese_holidays` (bool): 祝日機能を有効にするかどうか

**例:**
```python
# 祝日機能有効
generator = ICSGenerator(include_japanese_holidays=True)

# 祝日機能無効（デフォルト）
generator = ICSGenerator()
```

#### `add_japanese_holidays(start_date: date, end_date: date) -> None`

指定期間の日本の祝日をカレンダーに追加します。

**パラメータ:**
- `start_date` (date): 開始日
- `end_date` (date): 終了日

**例:**
```python
from datetime import date

generator = ICSGenerator()

# 2024年の祝日を追加
generator.add_japanese_holidays(
    date(2024, 1, 1), 
    date(2024, 12, 31)
)

# ゴールデンウィークの祝日のみ追加
generator.add_japanese_holidays(
    date(2024, 4, 29), 
    date(2024, 5, 5)
)
```

#### `add_japanese_holidays_for_year(year: int) -> None`

指定年の全祝日をカレンダーに追加します。

**パラメータ:**
- `year` (int): 対象年

**例:**
```python
generator = ICSGenerator()

# 2024年の全祝日を追加
generator.add_japanese_holidays_for_year(2024)

# 複数年の祝日を追加
for year in [2024, 2025, 2026]:
    generator.add_japanese_holidays_for_year(year)
```

---

## CLI API

### コマンドライン使用例

#### 祝日表示・エクスポート

```bash
# 今年の祝日を表示
python main.py holidays

# 特定年の祝日を表示
python main.py holidays --year 2024

# 祝日をICSファイルにエクスポート
python main.py holidays --year 2024 --output holidays_2024.ics
```

#### 祝日判定

```bash
# 今日が祝日かチェック
python main.py check-holiday

# 特定日が祝日かチェック
python main.py check-holiday --date 2024-01-01

# 次の祝日も表示
python main.py check-holiday --date 2024-06-01
```

#### データ管理

```bash
# 祝日データを強制更新
python main.py refresh-holidays
```

#### Change Calendarとの統合

```bash
# Change Calendarに祝日を含めてエクスポート
python main.py export MyCalendar --include-holidays -o calendar.ics

# 特定年の祝日を含める
python main.py export MyCalendar --include-holidays --holidays-year 2024 -o calendar.ics
```

---

## 使用例とベストプラクティス

### 基本的な使用パターン

#### 1. 祝日判定システム

```python
from datetime import date, datetime
from src.japanese_holidays import JapaneseHolidays

class BusinessDayCalculator:
    def __init__(self):
        self.holidays = JapaneseHolidays()
    
    def is_business_day(self, check_date: date) -> bool:
        """営業日かどうかを判定"""
        # 土日をチェック
        if check_date.weekday() >= 5:  # 土曜=5, 日曜=6
            return False
        
        # 祝日をチェック
        if self.holidays.is_holiday(check_date):
            return False
        
        return True
    
    def next_business_day(self, from_date: date) -> date:
        """次の営業日を取得"""
        current = from_date
        while not self.is_business_day(current):
            current = current + timedelta(days=1)
        return current

# 使用例
calculator = BusinessDayCalculator()
today = date.today()

if calculator.is_business_day(today):
    print("今日は営業日です")
else:
    next_biz = calculator.next_business_day(today)
    print(f"次の営業日は {next_biz} です")
```

#### 2. 祝日カレンダー生成

```python
from src.ics_generator import ICSGenerator
from datetime import date

def create_holiday_calendar(year: int, filename: str):
    """指定年の祝日カレンダーを生成"""
    generator = ICSGenerator()
    
    # 祝日を追加
    generator.add_japanese_holidays_for_year(year)
    
    # ファイル保存
    generator.save_to_file(filename)
    
    # 統計情報表示
    content = generator.generate_ics_content()
    event_count = content.count('BEGIN:VEVENT')
    print(f"{year}年の祝日カレンダーを生成しました")
    print(f"ファイル: {filename}")
    print(f"祝日数: {event_count}")

# 使用例
create_holiday_calendar(2024, "holidays_2024.ics")
```

#### 3. 祝日統計分析

```python
from src.japanese_holidays import JapaneseHolidays
from collections import Counter
import calendar

def analyze_holidays(year: int):
    """祝日の統計分析"""
    holidays = JapaneseHolidays()
    year_holidays = holidays.get_holidays_by_year(year)
    
    # 月別祝日数
    monthly_count = Counter()
    weekday_count = Counter()
    
    for holiday_date, holiday_name in year_holidays:
        monthly_count[holiday_date.month] += 1
        weekday_count[calendar.day_name[holiday_date.weekday()]] += 1
    
    print(f"{year}年の祝日分析:")
    print(f"総祝日数: {len(year_holidays)}")
    
    print("\n月別祝日数:")
    for month in range(1, 13):
        month_name = calendar.month_name[month]
        count = monthly_count[month]
        print(f"  {month_name}: {count}日")
    
    print("\n曜日別祝日数:")
    for weekday, count in weekday_count.items():
        print(f"  {weekday}: {count}日")

# 使用例
analyze_holidays(2024)
```

### エラーハンドリングのベストプラクティス

```python
from src.japanese_holidays import JapaneseHolidays
import logging

def safe_holiday_check(check_date):
    """安全な祝日チェック"""
    try:
        holidays = JapaneseHolidays()
        return holidays.is_holiday(check_date)
    
    except Exception as e:
        logging.error(f"祝日チェックでエラー: {e}")
        # フォールバック: 基本的な祝日のみチェック
        basic_holidays = {
            (1, 1): "元日",
            (2, 11): "建国記念の日", 
            (4, 29): "昭和の日",
            (5, 3): "憲法記念日",
            (5, 4): "みどりの日",
            (5, 5): "こどもの日",
            (11, 3): "文化の日",
            (11, 23): "勤労感謝の日"
        }
        
        return (check_date.month, check_date.day) in basic_holidays
```

### パフォーマンス最適化

```python
from src.japanese_holidays import JapaneseHolidays
from functools import lru_cache

class OptimizedHolidayChecker:
    def __init__(self):
        self.holidays = JapaneseHolidays()
        # 年別祝日データをキャッシュ
        self._year_cache = {}
    
    @lru_cache(maxsize=128)
    def is_holiday_cached(self, check_date):
        """キャッシュ付き祝日判定"""
        return self.holidays.is_holiday(check_date)
    
    def get_year_holidays_cached(self, year):
        """年別祝日データのキャッシュ"""
        if year not in self._year_cache:
            self._year_cache[year] = self.holidays.get_holidays_by_year(year)
        return self._year_cache[year]
```

---

## トラブルシューティング

### よくある問題と解決方法

#### 1. ネットワーク接続エラー

```python
from src.japanese_holidays import JapaneseHolidays

try:
    holidays = JapaneseHolidays()
    holidays.refresh_data()
except Exception as e:
    print(f"ネットワークエラー: {e}")
    print("キャッシュデータまたはフォールバックデータを使用します")
```

#### 2. キャッシュファイルの問題

```python
import os
from src.japanese_holidays import JapaneseHolidays

# キャッシュファイルを削除して再初期化
cache_path = os.path.expanduser("~/.aws-ssm-calendar/cache/japanese_holidays.csv")
if os.path.exists(cache_path):
    os.remove(cache_path)

holidays = JapaneseHolidays()  # 自動的に再ダウンロード
```

#### 3. 文字エンコーディング問題

```python
# カスタムキャッシュファイルを使用
holidays = JapaneseHolidays(cache_file="/path/to/utf8_cache.csv")
```

### デバッグ用ユーティリティ

```python
def debug_holiday_system():
    """祝日システムのデバッグ情報を表示"""
    from src.japanese_holidays import JapaneseHolidays
    import os
    
    holidays = JapaneseHolidays()
    
    # 統計情報
    stats = holidays.get_stats()
    print("=== 祝日システム情報 ===")
    print(f"総祝日数: {stats['total']}")
    print(f"対象期間: {stats['min_year']}-{stats['max_year']}")
    
    # キャッシュファイル情報
    cache_path = holidays.cache_file
    print(f"\nキャッシュファイル: {cache_path}")
    if os.path.exists(cache_path):
        size = os.path.getsize(cache_path)
        mtime = os.path.getmtime(cache_path)
        print(f"ファイルサイズ: {size} bytes")
        print(f"最終更新: {datetime.fromtimestamp(mtime)}")
    else:
        print("キャッシュファイルが存在しません")
    
    # サンプル祝日
    current_year = datetime.now().year
    year_holidays = holidays.get_holidays_by_year(current_year)
    print(f"\n{current_year}年の祝日（最初の5つ）:")
    for date, name in year_holidays[:5]:
        print(f"  {date}: {name}")

# 実行
debug_holiday_system()
```