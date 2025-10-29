#!/usr/bin/env python3
"""
営業日計算スクリプト

このスクリプトは、日本の祝日を考慮した営業日計算の
基本的な使用例を示します。

使用方法:
    python business_day_calculator.py --add-days 5
    python business_day_calculator.py --range 2024-01-01 2024-01-31
    python business_day_calculator.py --next-business-day
"""

import sys
import os
from datetime import date, datetime, timedelta
import argparse
from typing import List, Tuple

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.japanese_holidays import JapaneseHolidays


class BusinessDayCalculator:
    """営業日計算器"""
    
    def __init__(self):
        """初期化"""
        print("営業日計算器を初期化中...")
        
        try:
            self.holidays = JapaneseHolidays()
            print("✓ 祝日データの読み込み完了")
        except Exception as e:
            print(f"✗ 初期化エラー: {e}")
            raise
    
    def is_business_day(self, check_date: date) -> bool:
        """営業日判定
        
        Args:
            check_date: 判定する日付
            
        Returns:
            営業日の場合True（土日祝を除く平日）
        """
        # 土日チェック
        if check_date.weekday() >= 5:  # 土曜=5, 日曜=6
            return False
        
        # 祝日チェック
        return not self.holidays.is_holiday(check_date)
    
    def next_business_day(self, from_date: date) -> date:
        """次の営業日を取得
        
        Args:
            from_date: 基準日
            
        Returns:
            次の営業日
        """
        current = from_date + timedelta(days=1)
        
        while not self.is_business_day(current):
            current += timedelta(days=1)
        
        return current
    
    def previous_business_day(self, from_date: date) -> date:
        """前の営業日を取得
        
        Args:
            from_date: 基準日
            
        Returns:
            前の営業日
        """
        current = from_date - timedelta(days=1)
        
        while not self.is_business_day(current):
            current -= timedelta(days=1)
        
        return current
    
    def add_business_days(self, start_date: date, business_days: int) -> date:
        """営業日を加算
        
        Args:
            start_date: 開始日
            business_days: 加算する営業日数
            
        Returns:
            加算後の日付
        """
        if business_days == 0:
            return start_date
        
        current = start_date
        remaining = abs(business_days)
        direction = 1 if business_days > 0 else -1
        
        while remaining > 0:
            current += timedelta(days=direction)
            
            if self.is_business_day(current):
                remaining -= 1
        
        return current
    
    def business_days_between(self, start_date: date, end_date: date) -> int:
        """期間内の営業日数を計算
        
        Args:
            start_date: 開始日（含む）
            end_date: 終了日（含む）
            
        Returns:
            営業日数
        """
        if start_date > end_date:
            start_date, end_date = end_date, start_date
        
        count = 0
        current = start_date
        
        while current <= end_date:
            if self.is_business_day(current):
                count += 1
            current += timedelta(days=1)
        
        return count
    
    def get_business_days_in_range(self, start_date: date, end_date: date) -> List[date]:
        """期間内の営業日一覧を取得
        
        Args:
            start_date: 開始日
            end_date: 終了日
            
        Returns:
            営業日のリスト
        """
        business_days = []
        current = start_date
        
        while current <= end_date:
            if self.is_business_day(current):
                business_days.append(current)
            current += timedelta(days=1)
        
        return business_days
    
    def get_non_business_days_in_range(self, start_date: date, end_date: date) -> List[Tuple[date, str]]:
        """期間内の非営業日一覧を取得
        
        Args:
            start_date: 開始日
            end_date: 終了日
            
        Returns:
            (日付, 理由)のタプルリスト
        """
        non_business_days = []
        current = start_date
        
        while current <= end_date:
            if not self.is_business_day(current):
                reason = ""
                
                if current.weekday() == 5:
                    reason = "土曜日"
                elif current.weekday() == 6:
                    reason = "日曜日"
                elif self.holidays.is_holiday(current):
                    holiday_name = self.holidays.get_holiday_name(current)
                    reason = f"祝日 ({holiday_name})"
                
                non_business_days.append((current, reason))
            
            current += timedelta(days=1)
        
        return non_business_days
    
    def calculate_deadline(self, start_date: date, business_days: int) -> dict:
        """期限計算（詳細情報付き）
        
        Args:
            start_date: 開始日
            business_days: 営業日数
            
        Returns:
            計算結果の詳細辞書
        """
        deadline = self.add_business_days(start_date, business_days)
        
        # 経過する非営業日を計算
        non_business_days = self.get_non_business_days_in_range(
            start_date + timedelta(days=1), deadline
        )
        
        total_calendar_days = (deadline - start_date).days
        
        result = {
            'start_date': start_date,
            'deadline': deadline,
            'business_days': business_days,
            'total_calendar_days': total_calendar_days,
            'non_business_days': non_business_days,
            'non_business_count': len(non_business_days)
        }
        
        return result
    
    def monthly_business_day_analysis(self, year: int, month: int) -> dict:
        """月次営業日分析
        
        Args:
            year: 年
            month: 月
            
        Returns:
            月次分析結果
        """
        from calendar import monthrange
        
        # 月の範囲を取得
        first_day = date(year, month, 1)
        last_day_num = monthrange(year, month)[1]
        last_day = date(year, month, last_day_num)
        
        # 営業日と非営業日を取得
        business_days = self.get_business_days_in_range(first_day, last_day)
        non_business_days = self.get_non_business_days_in_range(first_day, last_day)
        
        # 種類別集計
        weekends = len([d for d, reason in non_business_days if "曜日" in reason])
        holidays = len([d for d, reason in non_business_days if "祝日" in reason])
        
        analysis = {
            'year': year,
            'month': month,
            'total_days': last_day_num,
            'business_days': len(business_days),
            'non_business_days': len(non_business_days),
            'weekends': weekends,
            'holidays': holidays,
            'business_day_ratio': len(business_days) / last_day_num * 100,
            'business_days_list': business_days,
            'non_business_days_list': non_business_days
        }
        
        return analysis


def main():
    """メイン関数"""
    
    parser = argparse.ArgumentParser(
        description='営業日計算ツール',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  %(prog)s --today                       # 今日が営業日かチェック
  %(prog)s --next-business-day           # 次の営業日を表示
  %(prog)s --add-days 5                  # 5営業日後を計算
  %(prog)s --add-days -3                 # 3営業日前を計算
  %(prog)s --range 2024-01-01 2024-01-31 # 期間内の営業日数
  %(prog)s --deadline 2024-01-01 10      # 期限計算（詳細）
  %(prog)s --monthly 2024 1              # 月次分析
        """
    )
    
    parser.add_argument(
        '--today',
        action='store_true',
        help='今日が営業日かチェック'
    )
    
    parser.add_argument(
        '--next-business-day',
        action='store_true',
        help='次の営業日を表示'
    )
    
    parser.add_argument(
        '--add-days',
        type=int,
        metavar='DAYS',
        help='指定営業日数を加算（負数で減算）'
    )
    
    parser.add_argument(
        '--from-date',
        type=str,
        default=None,
        help='計算の基準日 (YYYY-MM-DD形式、省略時は今日)'
    )
    
    parser.add_argument(
        '--range',
        nargs=2,
        metavar=('START', 'END'),
        help='期間内の営業日数を計算'
    )
    
    parser.add_argument(
        '--deadline',
        nargs=2,
        metavar=('START_DATE', 'BUSINESS_DAYS'),
        help='期限計算（開始日 営業日数）'
    )
    
    parser.add_argument(
        '--monthly',
        nargs=2,
        type=int,
        metavar=('YEAR', 'MONTH'),
        help='月次営業日分析'
    )
    
    parser.add_argument(
        '--list-days',
        action='store_true',
        help='営業日/非営業日の詳細リストを表示'
    )
    
    args = parser.parse_args()
    
    try:
        # 営業日計算器の初期化
        calculator = BusinessDayCalculator()
        
        # 基準日の設定
        if args.from_date:
            base_date = datetime.strptime(args.from_date, '%Y-%m-%d').date()
        else:
            base_date = date.today()
        
        if args.today:
            # 今日の営業日チェック
            today = date.today()
            is_biz_day = calculator.is_business_day(today)
            weekday = ['月', '火', '水', '木', '金', '土', '日'][today.weekday()]
            
            print(f"今日: {today} ({weekday}曜日)")
            
            if is_biz_day:
                print("✓ 今日は営業日です")
            else:
                print("✗ 今日は営業日ではありません")
                
                if today.weekday() >= 5:
                    print("  理由: 土日")
                elif calculator.holidays.is_holiday(today):
                    holiday_name = calculator.holidays.get_holiday_name(today)
                    print(f"  理由: 祝日 ({holiday_name})")
                
                # 次の営業日も表示
                next_biz = calculator.next_business_day(today)
                days_until = (next_biz - today).days
                print(f"  次の営業日: {next_biz} (あと{days_until}日)")
        
        elif args.next_business_day:
            # 次の営業日
            next_biz = calculator.next_business_day(base_date)
            days_until = (next_biz - base_date).days
            
            print(f"基準日: {base_date}")
            print(f"次の営業日: {next_biz} (あと{days_until}日)")
        
        elif args.add_days is not None:
            # 営業日加算/減算
            result_date = calculator.add_business_days(base_date, args.add_days)
            calendar_days = abs((result_date - base_date).days)
            
            direction = "後" if args.add_days > 0 else "前"
            
            print(f"基準日: {base_date}")
            print(f"{abs(args.add_days)}営業日{direction}: {result_date}")
            print(f"実際の日数: {calendar_days}日")
            
            # 詳細計算結果
            if args.add_days != 0:
                detail = calculator.calculate_deadline(base_date, args.add_days)
                print(f"経過する非営業日: {detail['non_business_count']}日")
        
        elif args.range:
            # 期間内営業日数
            start_date = datetime.strptime(args.range[0], '%Y-%m-%d').date()
            end_date = datetime.strptime(args.range[1], '%Y-%m-%d').date()
            
            business_days_count = calculator.business_days_between(start_date, end_date)
            total_days = (end_date - start_date).days + 1
            
            print(f"期間: {start_date} - {end_date}")
            print(f"総日数: {total_days}日")
            print(f"営業日数: {business_days_count}日")
            print(f"非営業日数: {total_days - business_days_count}日")
            print(f"営業日率: {business_days_count / total_days * 100:.1f}%")
            
            if args.list_days:
                # 詳細リスト表示
                business_days = calculator.get_business_days_in_range(start_date, end_date)
                non_business_days = calculator.get_non_business_days_in_range(start_date, end_date)
                
                print(f"\n営業日一覧 ({len(business_days)}日):")
                for biz_date in business_days[:10]:  # 最初の10日のみ表示
                    weekday = ['月', '火', '水', '木', '金', '土', '日'][biz_date.weekday()]
                    print(f"  {biz_date} ({weekday})")
                
                if len(business_days) > 10:
                    print(f"  ... 他{len(business_days) - 10}日")
                
                print(f"\n非営業日一覧 ({len(non_business_days)}日):")
                for non_biz_date, reason in non_business_days:
                    weekday = ['月', '火', '水', '木', '金', '土', '日'][non_biz_date.weekday()]
                    print(f"  {non_biz_date} ({weekday}) - {reason}")
        
        elif args.deadline:
            # 期限計算
            start_date = datetime.strptime(args.deadline[0], '%Y-%m-%d').date()
            business_days = int(args.deadline[1])
            
            detail = calculator.calculate_deadline(start_date, business_days)
            
            print(f"📅 期限計算結果")
            print("=" * 30)
            print(f"開始日: {detail['start_date']}")
            print(f"期限: {detail['deadline']}")
            print(f"営業日数: {detail['business_days']}日")
            print(f"実際の日数: {detail['total_calendar_days']}日")
            print(f"経過する非営業日: {detail['non_business_count']}日")
            
            if detail['non_business_days']:
                print(f"\n経過する非営業日:")
                for non_biz_date, reason in detail['non_business_days']:
                    weekday = ['月', '火', '水', '木', '金', '土', '日'][non_biz_date.weekday()]
                    print(f"  {non_biz_date} ({weekday}) - {reason}")
        
        elif args.monthly:
            # 月次分析
            year, month = args.monthly
            analysis = calculator.monthly_business_day_analysis(year, month)
            
            month_names = [
                '1月', '2月', '3月', '4月', '5月', '6月',
                '7月', '8月', '9月', '10月', '11月', '12月'
            ]
            
            print(f"📊 {year}年{month_names[month-1]} 営業日分析")
            print("=" * 40)
            print(f"総日数: {analysis['total_days']}日")
            print(f"営業日数: {analysis['business_days']}日 ({analysis['business_day_ratio']:.1f}%)")
            print(f"非営業日数: {analysis['non_business_days']}日")
            print(f"  土日: {analysis['weekends']}日")
            print(f"  祝日: {analysis['holidays']}日")
            
            if args.list_days and analysis['non_business_days_list']:
                print(f"\n非営業日一覧:")
                for non_biz_date, reason in analysis['non_business_days_list']:
                    weekday = ['月', '火', '水', '木', '金', '土', '日'][non_biz_date.weekday()]
                    print(f"  {non_biz_date} ({weekday}) - {reason}")
        
        else:
            # デフォルト: 基本情報表示
            today = date.today()
            is_biz_day = calculator.is_business_day(today)
            
            print(f"📅 営業日情報 ({today})")
            print("=" * 30)
            
            if is_biz_day:
                print("✓ 今日は営業日です")
            else:
                print("✗ 今日は営業日ではありません")
            
            # 次の営業日
            next_biz = calculator.next_business_day(today)
            print(f"次の営業日: {next_biz}")
            
            # 前の営業日
            prev_biz = calculator.previous_business_day(today)
            print(f"前の営業日: {prev_biz}")
    
    except ValueError as e:
        print(f"日付形式エラー: {e}")
        print("YYYY-MM-DD形式で入力してください")
        sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n処理を中断しました")
        sys.exit(0)
    
    except Exception as e:
        print(f"予期しないエラー: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()