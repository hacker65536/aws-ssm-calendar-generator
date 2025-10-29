# 使用ガイドとベストプラクティス

## 概要

AWS SSM Change Calendar 休業日スケジュール管理ツールの効果的な使用方法とベストプラクティスを説明します。

## 目次

1. [クイックスタート](#クイックスタート)
2. [基本的な使用パターン](#基本的な使用パターン)
3. [高度な使用例](#高度な使用例)
4. [パフォーマンス最適化](#パフォーマンス最適化)
5. [セキュリティベストプラクティス](#セキュリティベストプラクティス)
6. [運用ガイドライン](#運用ガイドライン)
7. [統合パターン](#統合パターン)

---

## クイックスタート

### 1. 基本セットアップ

```bash
# 依存関係のインストール
pip install -r requirements.txt

# AWS認証情報の設定
aws configure

# 祝日データの初期化
python main.py refresh-holidays
```

### 2. 最初のICSファイル生成

```bash
# 2024年の祝日カレンダーを生成
python main.py holidays --year 2024 --output holidays_2024.ics

# 生成されたファイルを確認
python main.py analyze-ics holidays_2024.ics
```

### 3. AWS Change Calendarとの統合

```bash
# Change Calendarのエクスポート
python main.py export MyChangeCalendar --include-holidays -o calendar.ics

# AWS環境での確認
aws ssm get-calendar-state --calendar-names MyChangeCalendar
```

---

## 基本的な使用パターン

### パターン1: 営業日管理システム

企業の営業日計算に祝日情報を活用する例です。

```python
from datetime import date, timedelta
from src.japanese_holidays import JapaneseHolidays

class BusinessCalendar:
    def __init__(self):
        self.holidays = JapaneseHolidays()
    
    def is_business_day(self, check_date: date) -> bool:
        """営業日判定（土日祝を除く）"""
        # 土日チェック
        if check_date.weekday() >= 5:
            return False
        
        # 祝日チェック
        return not self.holidays.is_holiday(check_date)
    
    def next_business_day(self, from_date: date) -> date:
        """次の営業日を取得"""
        current = from_date + timedelta(days=1)
        while not self.is_business_day(current):
            current += timedelta(days=1)
        return current
    
    def business_days_between(self, start_date: date, end_date: date) -> int:
        """期間内の営業日数を計算"""
        count = 0
        current = start_date
        
        while current <= end_date:
            if self.is_business_day(current):
                count += 1
            current += timedelta(days=1)
        
        return count

# 使用例
calendar = BusinessCalendar()

# 今日が営業日かチェック
today = date.today()
if calendar.is_business_day(today):
    print("今日は営業日です")
else:
    next_biz = calendar.next_business_day(today)
    print(f"次の営業日は {next_biz} です")

# 月末までの営業日数
from calendar import monthrange
year, month = today.year, today.month
last_day = monthrange(year, month)[1]
month_end = date(year, month, last_day)
biz_days = calendar.business_days_between(today, month_end)
print(f"今月残りの営業日数: {biz_days}日")
```

### パターン2: 定期レポート生成

毎月の祝日レポートを自動生成する例です。

```python
from datetime import date, datetime
from calendar import monthrange
from src.japanese_holidays import JapaneseHolidays
from src.ics_generator import ICSGenerator

class MonthlyHolidayReporter:
    def __init__(self):
        self.holidays = JapaneseHolidays()
        self.generator = ICSGenerator()
    
    def generate_monthly_report(self, year: int, month: int) -> dict:
        """月次祝日レポート生成"""
        # 月の範囲を取得
        first_day = date(year, month, 1)
        last_day_num = monthrange(year, month)[1]
        last_day = date(year, month, last_day_num)
        
        # 月内の祝日を取得
        month_holidays = self.holidays.get_holidays_in_range(first_day, last_day)
        
        # 統計計算
        total_days = last_day_num
        holiday_count = len(month_holidays)
        weekends = sum(1 for day in range(1, last_day_num + 1) 
                      if date(year, month, day).weekday() >= 5)
        business_days = total_days - holiday_count - weekends
        
        # レポートデータ
        report = {
            'year': year,
            'month': month,
            'total_days': total_days,
            'holidays': month_holidays,
            'holiday_count': holiday_count,
            'weekend_days': weekends,
            'business_days': business_days,
            'holiday_ratio': holiday_count / total_days * 100
        }
        
        return report
    
    def export_monthly_calendar(self, year: int, month: int, filename: str):
        """月次カレンダーをICSファイルにエクスポート"""
        first_day = date(year, month, 1)
        last_day_num = monthrange(year, month)[1]
        last_day = date(year, month, last_day_num)
        
        month_holidays = self.holidays.get_holidays_in_range(first_day, last_day)
        
        # ICSファイル生成
        events = self.generator.convert_holidays_to_events(month_holidays)
        calendar = self.generator.create_aws_ssm_calendar()
        
        for event in events:
            calendar.add_component(event)
        
        self.generator.save_to_file(filename)
        
        return len(month_holidays)

# 使用例
reporter = MonthlyHolidayReporter()

# 今月のレポート生成
today = date.today()
report = reporter.generate_monthly_report(today.year, today.month)

print(f"{report['year']}年{report['month']}月の祝日レポート")
print(f"総日数: {report['total_days']}日")
print(f"祝日数: {report['holiday_count']}日 ({report['holiday_ratio']:.1f}%)")
print(f"営業日数: {report['business_days']}日")

print("\n祝日一覧:")
for holiday_date, holiday_name in report['holidays']:
    weekday = ['月', '火', '水', '木', '金', '土', '日'][holiday_date.weekday()]
    print(f"  {holiday_date} ({weekday}) - {holiday_name}")

# 月次カレンダーをエクスポート
filename = f"holidays_{today.year}_{today.month:02d}.ics"
count = reporter.export_monthly_calendar(today.year, today.month, filename)
print(f"\nカレンダーファイル生成: {filename} ({count}件の祝日)")
```

### パターン3: システムメンテナンス計画

祝日を考慮したシステムメンテナンス計画の例です。

```python
from datetime import date, timedelta
from src.japanese_holidays import JapaneseHolidays

class MaintenancePlanner:
    def __init__(self):
        self.holidays = JapaneseHolidays()
    
    def find_maintenance_windows(self, start_date: date, days_ahead: int = 30) -> list:
        """メンテナンス可能な期間を検索"""
        windows = []
        current = start_date
        end_date = start_date + timedelta(days=days_ahead)
        
        while current <= end_date:
            # 土日祝日をメンテナンス候補とする
            if (current.weekday() >= 5 or  # 土日
                self.holidays.is_holiday(current)):  # 祝日
                
                # 連続する休日期間を検出
                window_start = current
                window_end = current
                
                # 連続する休日を探す
                next_day = current + timedelta(days=1)
                while (next_day <= end_date and 
                       (next_day.weekday() >= 5 or self.holidays.is_holiday(next_day))):
                    window_end = next_day
                    next_day += timedelta(days=1)
                
                # 期間の長さを計算
                duration = (window_end - window_start).days + 1
                
                # 祝日名を取得
                holiday_names = []
                check_date = window_start
                while check_date <= window_end:
                    if self.holidays.is_holiday(check_date):
                        name = self.holidays.get_holiday_name(check_date)
                        if name:
                            holiday_names.append(name)
                    check_date += timedelta(days=1)
                
                windows.append({
                    'start': window_start,
                    'end': window_end,
                    'duration': duration,
                    'type': 'holiday' if holiday_names else 'weekend',
                    'holidays': holiday_names
                })
                
                current = window_end + timedelta(days=1)
            else:
                current += timedelta(days=1)
        
        return windows
    
    def recommend_maintenance_date(self, min_duration: int = 2) -> dict:
        """推奨メンテナンス日を提案"""
        windows = self.find_maintenance_windows(date.today(), 90)
        
        # 最小期間以上の窓を抽出
        suitable_windows = [w for w in windows if w['duration'] >= min_duration]
        
        if not suitable_windows:
            return None
        
        # 最も長い期間を推奨
        best_window = max(suitable_windows, key=lambda x: x['duration'])
        
        return {
            'recommended_date': best_window['start'],
            'duration': best_window['duration'],
            'end_date': best_window['end'],
            'reason': f"{best_window['duration']}日間の連続休日期間",
            'holidays': best_window['holidays']
        }

# 使用例
planner = MaintenancePlanner()

# 今後30日のメンテナンス可能期間を検索
windows = planner.find_maintenance_windows(date.today(), 30)

print("=== メンテナンス可能期間 ===")
for window in windows:
    print(f"{window['start']} - {window['end']} ({window['duration']}日間)")
    if window['holidays']:
        print(f"  祝日: {', '.join(window['holidays'])}")
    print()

# 推奨メンテナンス日を取得
recommendation = planner.recommend_maintenance_date(min_duration=2)
if recommendation:
    print("=== 推奨メンテナンス日 ===")
    print(f"開始日: {recommendation['recommended_date']}")
    print(f"期間: {recommendation['duration']}日間")
    print(f"理由: {recommendation['reason']}")
    if recommendation['holidays']:
        print(f"含まれる祝日: {', '.join(recommendation['holidays'])}")
else:
    print("適切なメンテナンス期間が見つかりませんでした")
```

---

## 高度な使用例

### 例1: 複数年度の祝日分析

```python
from collections import defaultdict, Counter
from datetime import date
from src.japanese_holidays import JapaneseHolidays
import matplotlib.pyplot as plt

class HolidayAnalyzer:
    def __init__(self):
        self.holidays = JapaneseHolidays()
    
    def analyze_multi_year_trends(self, start_year: int, end_year: int) -> dict:
        """複数年度の祝日トレンド分析"""
        yearly_data = {}
        monthly_totals = defaultdict(int)
        weekday_totals = Counter()
        
        for year in range(start_year, end_year + 1):
            year_holidays = self.holidays.get_holidays_by_year(year)
            
            # 年別統計
            monthly_count = Counter()
            weekday_count = Counter()
            
            for holiday_date, holiday_name in year_holidays:
                monthly_count[holiday_date.month] += 1
                weekday_count[holiday_date.weekday()] += 1
                monthly_totals[holiday_date.month] += 1
                weekday_totals[holiday_date.weekday()] += 1
            
            yearly_data[year] = {
                'total': len(year_holidays),
                'monthly': dict(monthly_count),
                'weekday': dict(weekday_count),
                'holidays': year_holidays
            }
        
        return {
            'yearly_data': yearly_data,
            'monthly_averages': {month: count / (end_year - start_year + 1) 
                               for month, count in monthly_totals.items()},
            'weekday_totals': dict(weekday_totals),
            'total_years': end_year - start_year + 1
        }
    
    def find_holiday_patterns(self, analysis: dict) -> dict:
        """祝日パターンの発見"""
        patterns = {}
        
        # 最も祝日が多い月
        monthly_avg = analysis['monthly_averages']
        busiest_month = max(monthly_avg.keys(), key=lambda k: monthly_avg[k])
        
        # 最も祝日が少ない月
        quietest_month = min(monthly_avg.keys(), key=lambda k: monthly_avg[k])
        
        # 曜日分布
        weekday_names = ['月', '火', '水', '木', '金', '土', '日']
        weekday_dist = {weekday_names[day]: count 
                       for day, count in analysis['weekday_totals'].items()}
        
        patterns = {
            'busiest_month': {
                'month': busiest_month,
                'average_holidays': monthly_avg[busiest_month]
            },
            'quietest_month': {
                'month': quietest_month,
                'average_holidays': monthly_avg[quietest_month]
            },
            'weekday_distribution': weekday_dist,
            'most_common_weekday': max(weekday_dist.keys(), 
                                     key=lambda k: weekday_dist[k])
        }
        
        return patterns

# 使用例
analyzer = HolidayAnalyzer()

# 2020-2025年の分析
analysis = analyzer.analyze_multi_year_trends(2020, 2025)
patterns = analyzer.find_holiday_patterns(analysis)

print("=== 祝日トレンド分析 (2020-2025) ===")
print(f"分析期間: {analysis['total_years']}年間")

print(f"\n最も祝日が多い月: {patterns['busiest_month']['month']}月")
print(f"平均祝日数: {patterns['busiest_month']['average_holidays']:.1f}日")

print(f"\n最も祝日が少ない月: {patterns['quietest_month']['month']}月")
print(f"平均祝日数: {patterns['quietest_month']['average_holidays']:.1f}日")

print(f"\n最も多い曜日: {patterns['most_common_weekday']}")

print("\n曜日別祝日数:")
for weekday, count in patterns['weekday_distribution'].items():
    print(f"  {weekday}曜日: {count}日")
```

### 例2: AWS Change Calendar自動同期システム

```python
import json
from datetime import date, datetime
from src.aws_client import SSMChangeCalendarClient
from src.calendar_analyzer import ICSAnalyzer
from src.ics_generator import ICSGenerator
from src.japanese_holidays import JapaneseHolidays

class ChangeCalendarSyncManager:
    def __init__(self, region: str = 'us-east-1', profile: str = None):
        self.aws_client = SSMChangeCalendarClient(region, profile)
        self.analyzer = ICSAnalyzer()
        self.holidays = JapaneseHolidays()
        self.generator = ICSGenerator(self.holidays)
    
    def sync_holiday_calendar(self, calendar_name: str, year: int) -> dict:
        """祝日カレンダーをAWS Change Calendarと同期"""
        
        # ローカル祝日カレンダー生成
        local_filename = f"holidays_{year}_local.ics"
        year_holidays = self.holidays.get_holidays_by_year(year)
        
        events = self.generator.convert_holidays_to_events(year_holidays)
        calendar = self.generator.create_aws_ssm_calendar()
        
        for event in events:
            calendar.add_component(event)
        
        self.generator.save_to_file(local_filename)
        
        # AWS Change Calendarと比較
        try:
            comparison = self.analyzer.compare_with_aws_change_calendar(
                local_filename, calendar_name
            )
            
            sync_result = {
                'status': 'success',
                'local_file': local_filename,
                'aws_calendar': calendar_name,
                'comparison': comparison,
                'sync_needed': (comparison['summary']['added'] > 0 or 
                              comparison['summary']['deleted'] > 0 or 
                              comparison['summary']['modified'] > 0),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            sync_result = {
                'status': 'error',
                'error': str(e),
                'local_file': local_filename,
                'aws_calendar': calendar_name,
                'timestamp': datetime.now().isoformat()
            }
        
        return sync_result
    
    def generate_sync_report(self, sync_results: list) -> str:
        """同期レポート生成"""
        report_lines = []
        report_lines.append("=== AWS Change Calendar 同期レポート ===")
        report_lines.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        success_count = sum(1 for r in sync_results if r['status'] == 'success')
        error_count = len(sync_results) - success_count
        
        report_lines.append(f"同期対象: {len(sync_results)}カレンダー")
        report_lines.append(f"成功: {success_count}件")
        report_lines.append(f"エラー: {error_count}件")
        report_lines.append("")
        
        for result in sync_results:
            if result['status'] == 'success':
                comparison = result['comparison']
                summary = comparison['summary']
                
                report_lines.append(f"カレンダー: {result['aws_calendar']}")
                report_lines.append(f"  ローカルファイル: {result['local_file']}")
                report_lines.append(f"  同期必要: {'はい' if result['sync_needed'] else 'いいえ'}")
                
                if result['sync_needed']:
                    report_lines.append(f"  追加: {summary['added']}件")
                    report_lines.append(f"  削除: {summary['deleted']}件")
                    report_lines.append(f"  変更: {summary['modified']}件")
                
                report_lines.append("")
            else:
                report_lines.append(f"エラー - {result['aws_calendar']}: {result['error']}")
                report_lines.append("")
        
        return "\n".join(report_lines)
    
    def auto_sync_multiple_calendars(self, calendar_configs: list) -> dict:
        """複数カレンダーの自動同期"""
        results = []
        
        for config in calendar_configs:
            calendar_name = config['name']
            year = config.get('year', date.today().year)
            
            try:
                sync_result = self.sync_holiday_calendar(calendar_name, year)
                results.append(sync_result)
                
            except Exception as e:
                results.append({
                    'status': 'error',
                    'aws_calendar': calendar_name,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        # レポート生成
        report = self.generate_sync_report(results)
        
        return {
            'results': results,
            'report': report,
            'summary': {
                'total': len(results),
                'success': sum(1 for r in results if r['status'] == 'success'),
                'errors': sum(1 for r in results if r['status'] == 'error'),
                'sync_needed': sum(1 for r in results 
                                 if r['status'] == 'success' and r.get('sync_needed', False))
            }
        }

# 使用例
sync_manager = ChangeCalendarSyncManager(region='us-east-1')

# 複数カレンダーの設定
calendar_configs = [
    {'name': 'japanese-holidays-2024', 'year': 2024},
    {'name': 'japanese-holidays-2025', 'year': 2025},
    {'name': 'maintenance-calendar', 'year': 2024}
]

# 自動同期実行
sync_summary = sync_manager.auto_sync_multiple_calendars(calendar_configs)

print(sync_summary['report'])

# 同期が必要なカレンダーがある場合の処理
if sync_summary['summary']['sync_needed'] > 0:
    print(f"\n{sync_summary['summary']['sync_needed']}個のカレンダーで同期が必要です")
    print("手動でAWS Change Calendarを更新してください")
```

---

## パフォーマンス最適化

### 1. メモリ使用量の最適化

```python
from src.japanese_holidays import JapaneseHolidays

# 監視機能を無効にしてメモリ使用量を削減
holidays = JapaneseHolidays(enable_monitoring=False)

# 必要な年のデータのみ保持
current_year = date.today().year
for year in range(current_year, current_year + 3):
    year_holidays = holidays.get_holidays_by_year(year)
    # 年ごとに処理して即座に解放
```

### 2. キャッシュ戦略の最適化

```python
from functools import lru_cache
from src.japanese_holidays import JapaneseHolidays

class OptimizedHolidayManager:
    def __init__(self):
        self.holidays = JapaneseHolidays()
        self._year_cache = {}
    
    @lru_cache(maxsize=1000)
    def is_holiday_cached(self, check_date: date) -> bool:
        """LRUキャッシュ付き祝日判定"""
        return self.holidays.is_holiday(check_date)
    
    def get_year_holidays_cached(self, year: int) -> list:
        """年別祝日データのキャッシュ"""
        if year not in self._year_cache:
            self._year_cache[year] = self.holidays.get_holidays_by_year(year)
        return self._year_cache[year]
    
    def clear_cache(self):
        """キャッシュクリア"""
        self.is_holiday_cached.cache_clear()
        self._year_cache.clear()

# 使用例
manager = OptimizedHolidayManager()

# 高速な祝日判定
for i in range(1000):
    result = manager.is_holiday_cached(date(2024, 1, 1))
```

### 3. バッチ処理の最適化

```python
from concurrent.futures import ThreadPoolExecutor
from src.ics_generator import ICSGenerator

def generate_multiple_calendars(years: list) -> dict:
    """複数年のカレンダーを並列生成"""
    
    def generate_year_calendar(year: int) -> tuple:
        generator = ICSGenerator()
        filename = f"holidays_{year}.ics"
        
        # 年別祝日を追加
        year_holidays = generator.japanese_holidays.get_holidays_by_year(year)
        events = generator.convert_holidays_to_events(year_holidays)
        
        calendar = generator.create_aws_ssm_calendar()
        for event in events:
            calendar.add_component(event)
        
        generator.save_to_file(filename)
        
        return year, filename, len(events)
    
    results = {}
    
    # 並列処理で複数年のカレンダーを生成
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(generate_year_calendar, year): year 
                  for year in years}
        
        for future in futures:
            year, filename, event_count = future.result()
            results[year] = {
                'filename': filename,
                'event_count': event_count
            }
    
    return results

# 使用例
years = [2024, 2025, 2026, 2027]
results = generate_multiple_calendars(years)

for year, info in results.items():
    print(f"{year}年: {info['filename']} ({info['event_count']}イベント)")
```

---

## セキュリティベストプラクティス

### 1. AWS認証情報の安全な管理

```python
import os
from src.aws_client import SSMChangeCalendarClient

# 環境変数を使用した認証
os.environ['AWS_PROFILE'] = 'production'
os.environ['AWS_REGION'] = 'us-east-1'

# IAMロールを使用（推奨）
client = SSMChangeCalendarClient()

# 最小権限の原則
required_permissions = [
    "ssm:GetDocument",
    "ssm:ListDocuments", 
    "ssm:GetCalendarState"
]
```

### 2. 入力検証とサニタイゼーション

```python
from datetime import date
import re

def validate_calendar_name(name: str) -> str:
    """カレンダー名の検証"""
    if not name or len(name) > 128:
        raise ValueError("カレンダー名は1-128文字である必要があります")
    
    # 英数字、ハイフン、アンダースコアのみ許可
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        raise ValueError("カレンダー名に無効な文字が含まれています")
    
    return name

def validate_date_input(date_str: str) -> date:
    """日付入力の検証"""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError("日付はYYYY-MM-DD形式で入力してください")

# 使用例
try:
    calendar_name = validate_calendar_name("my-holiday-calendar")
    check_date = validate_date_input("2024-01-01")
except ValueError as e:
    print(f"入力エラー: {e}")
```

### 3. ファイル操作のセキュリティ

```python
import os
from pathlib import Path

def secure_file_path(filename: str, base_dir: str = "./output") -> Path:
    """安全なファイルパスの生成"""
    base_path = Path(base_dir).resolve()
    file_path = (base_path / filename).resolve()
    
    # パストラバーサル攻撃を防ぐ
    if not str(file_path).startswith(str(base_path)):
        raise ValueError("無効なファイルパスです")
    
    # ディレクトリが存在しない場合は作成
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    return file_path

# 使用例
try:
    safe_path = secure_file_path("holidays_2024.ics")
    print(f"安全なパス: {safe_path}")
except ValueError as e:
    print(f"セキュリティエラー: {e}")
```

---

## 運用ガイドライン

### 1. 定期メンテナンス

```python
from datetime import date, timedelta
from src.japanese_holidays import JapaneseHolidays

class MaintenanceScheduler:
    def __init__(self):
        self.holidays = JapaneseHolidays()
    
    def should_refresh_data(self) -> bool:
        """データ更新が必要かチェック"""
        # 月初めまたは祝日データが古い場合
        today = date.today()
        
        # 月初めチェック
        if today.day == 1:
            return True
        
        # 内閣府の祝日発表時期（2月）
        if today.month == 2 and today.day <= 7:
            return True
        
        # キャッシュの有効期限チェック
        try:
            stats = self.holidays.get_stats()
            if stats['max_year'] < today.year + 1:
                return True
        except:
            return True
        
        return False
    
    def perform_maintenance(self) -> dict:
        """定期メンテナンス実行"""
        maintenance_log = {
            'timestamp': date.today().isoformat(),
            'actions': []
        }
        
        # データ更新チェック
        if self.should_refresh_data():
            try:
                self.holidays.refresh_data()
                maintenance_log['actions'].append('祝日データを更新しました')
            except Exception as e:
                maintenance_log['actions'].append(f'データ更新エラー: {e}')
        
        # 統計情報取得
        try:
            stats = self.holidays.get_stats()
            maintenance_log['stats'] = stats
            maintenance_log['actions'].append('統計情報を取得しました')
        except Exception as e:
            maintenance_log['actions'].append(f'統計取得エラー: {e}')
        
        return maintenance_log

# 使用例（cronジョブなどで実行）
scheduler = MaintenanceScheduler()
log = scheduler.perform_maintenance()

print("=== 定期メンテナンス結果 ===")
print(f"実行日: {log['timestamp']}")
for action in log['actions']:
    print(f"- {action}")

if 'stats' in log:
    stats = log['stats']
    print(f"\n統計情報:")
    print(f"- 総祝日数: {stats['total']}")
    print(f"- 対象期間: {stats['min_year']}-{stats['max_year']}")
```

### 2. 監視とアラート

```python
import logging
from datetime import date, datetime
from src.japanese_holidays import JapaneseHolidays
from src.error_handler import handle_error

class HolidaySystemMonitor:
    def __init__(self):
        self.holidays = JapaneseHolidays()
        self.logger = logging.getLogger(__name__)
    
    @handle_error
    def health_check(self) -> dict:
        """システムヘルスチェック"""
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'status': 'healthy',
            'checks': {}
        }
        
        # 祝日データの健全性チェック
        try:
            current_year = date.today().year
            year_holidays = self.holidays.get_holidays_by_year(current_year)
            
            health_status['checks']['holiday_data'] = {
                'status': 'ok',
                'count': len(year_holidays),
                'message': f'{current_year}年の祝日データ正常'
            }
        except Exception as e:
            health_status['checks']['holiday_data'] = {
                'status': 'error',
                'message': str(e)
            }
            health_status['status'] = 'unhealthy'
        
        # キャッシュファイルの存在チェック
        try:
            cache_path = self.holidays.cache_file
            if os.path.exists(cache_path):
                cache_size = os.path.getsize(cache_path)
                health_status['checks']['cache_file'] = {
                    'status': 'ok',
                    'size': cache_size,
                    'message': 'キャッシュファイル正常'
                }
            else:
                health_status['checks']['cache_file'] = {
                    'status': 'warning',
                    'message': 'キャッシュファイルが存在しません'
                }
        except Exception as e:
            health_status['checks']['cache_file'] = {
                'status': 'error',
                'message': str(e)
            }
            health_status['status'] = 'unhealthy'
        
        return health_status
    
    def send_alert_if_needed(self, health_status: dict):
        """必要に応じてアラート送信"""
        if health_status['status'] == 'unhealthy':
            self.logger.error(f"システム異常検出: {health_status}")
            # ここで実際のアラート送信処理を実装
            # 例: メール送信、Slack通知、SNS発行など

# 使用例（定期実行）
monitor = HolidaySystemMonitor()
health = monitor.health_check()

print("=== システムヘルスチェック ===")
print(f"全体ステータス: {health['status']}")
print(f"チェック時刻: {health['timestamp']}")

for check_name, check_result in health['checks'].items():
    status_icon = "✓" if check_result['status'] == 'ok' else "⚠" if check_result['status'] == 'warning' else "✗"
    print(f"{status_icon} {check_name}: {check_result['message']}")

monitor.send_alert_if_needed(health)
```

---

## 統合パターン

### 1. CI/CDパイプライン統合

```yaml
# .github/workflows/holiday-calendar-sync.yml
name: Holiday Calendar Sync

on:
  schedule:
    - cron: '0 2 1 * *'  # 毎月1日の午前2時
  workflow_dispatch:

jobs:
  sync-calendars:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1
    
    - name: Sync holiday calendars
      run: |
        python scripts/sync_calendars.py
    
    - name: Upload artifacts
      uses: actions/upload-artifact@v3
      with:
        name: holiday-calendars
        path: output/*.ics
```

### 2. Terraform統合

```hcl
# terraform/change_calendar.tf
resource "aws_ssm_document" "japanese_holidays" {
  name          = "japanese-holidays-${var.year}"
  document_type = "ChangeCalendar"
  document_format = "TEXT"
  
  content = file("../output/holidays_${var.year}.ics")
  
  tags = {
    Environment = var.environment
    Purpose     = "Japanese Holidays"
    Year        = var.year
  }
}

# 生成スクリプトの実行
resource "null_resource" "generate_calendar" {
  triggers = {
    year = var.year
  }
  
  provisioner "local-exec" {
    command = "python ../main.py holidays --year ${var.year} --output ../output/holidays_${var.year}.ics"
  }
}
```

### 3. Docker統合

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY main.py .

# 定期実行用のcronジョブ
COPY scripts/crontab /etc/cron.d/holiday-sync
RUN chmod 0644 /etc/cron.d/holiday-sync
RUN crontab /etc/cron.d/holiday-sync

CMD ["python", "main.py"]
```

```bash
# Docker使用例
docker build -t holiday-calendar-tool .

# 祝日カレンダー生成
docker run -v $(pwd)/output:/app/output holiday-calendar-tool \
  python main.py holidays --year 2024 --output /app/output/holidays_2024.ics

# AWS統合（認証情報をマウント）
docker run -v ~/.aws:/root/.aws -v $(pwd)/output:/app/output holiday-calendar-tool \
  python main.py export MyCalendar --include-holidays -o /app/output/calendar.ics
```

これらのベストプラクティスを参考に、効率的で安全な祝日管理システムを構築してください。