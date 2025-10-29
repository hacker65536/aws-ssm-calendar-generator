#!/usr/bin/env python3
"""
シンプルな祝日判定スクリプト

このスクリプトは、指定された日付が日本の祝日かどうかを判定する
基本的な使用例を示します。

使用方法:
    python simple_holiday_check.py
    python simple_holiday_check.py --date 2024-01-01
    python simple_holiday_check.py --interactive
"""

import sys
import os
from datetime import date, datetime, timedelta
import argparse

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.japanese_holidays import JapaneseHolidays
from src.error_handler import handle_error, NetworkError, DataIntegrityError


class SimpleHolidayChecker:
    """シンプルな祝日チェッカー"""
    
    def __init__(self):
        """初期化"""
        print("祝日データを初期化中...")
        try:
            self.holidays = JapaneseHolidays()
            print("✓ 祝日データの初期化完了")
        except Exception as e:
            print(f"✗ 初期化エラー: {e}")
            sys.exit(1)
    
    def check_single_date(self, check_date: date) -> dict:
        """単一日付の祝日チェック"""
        
        result = {
            'date': check_date,
            'is_holiday': False,
            'holiday_name': None,
            'weekday': check_date.strftime('%A'),
            'weekday_jp': ['月', '火', '水', '木', '金', '土', '日'][check_date.weekday()]
        }
        
        try:
            result['is_holiday'] = self.holidays.is_holiday(check_date)
            if result['is_holiday']:
                result['holiday_name'] = self.holidays.get_holiday_name(check_date)
        except Exception as e:
            print(f"祝日チェックエラー: {e}")
            return result
        
        return result
    
    def check_date_range(self, start_date: date, end_date: date) -> list:
        """期間内の祝日チェック"""
        
        holidays_in_range = []
        current = start_date
        
        while current <= end_date:
            result = self.check_single_date(current)
            if result['is_holiday']:
                holidays_in_range.append(result)
            current += timedelta(days=1)
        
        return holidays_in_range
    
    def get_next_holidays(self, from_date: date, count: int = 5) -> list:
        """次の祝日を取得"""
        
        next_holidays = []
        current = from_date
        
        # 最大1年先まで検索
        end_date = from_date + timedelta(days=365)
        
        while current <= end_date and len(next_holidays) < count:
            if self.holidays.is_holiday(current):
                result = self.check_single_date(current)
                next_holidays.append(result)
            current += timedelta(days=1)
        
        return next_holidays
    
    def interactive_mode(self):
        """対話モード"""
        
        print("\n=== 対話モード ===")
        print("日付を入力してください (YYYY-MM-DD形式)")
        print("'quit' または 'exit' で終了")
        print("'next' で次の祝日を表示")
        print("'stats' で統計情報を表示")
        
        while True:
            try:
                user_input = input("\n日付を入力: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("終了します")
                    break
                
                elif user_input.lower() == 'next':
                    next_holidays = self.get_next_holidays(date.today(), 5)
                    print("\n次の祝日:")
                    for holiday in next_holidays:
                        print(f"  {holiday['date']} ({holiday['weekday_jp']}) - {holiday['holiday_name']}")
                
                elif user_input.lower() == 'stats':
                    stats = self.holidays.get_stats()
                    print(f"\n統計情報:")
                    print(f"  総祝日数: {stats['total']}")
                    print(f"  対象期間: {stats['min_year']} - {stats['max_year']}")
                    print(f"  対象年数: {stats['years']}")
                
                else:
                    # 日付として解析
                    check_date = datetime.strptime(user_input, '%Y-%m-%d').date()
                    result = self.check_single_date(check_date)
                    
                    print(f"\n結果:")
                    print(f"  日付: {result['date']} ({result['weekday_jp']}曜日)")
                    
                    if result['is_holiday']:
                        print(f"  ✓ 祝日です: {result['holiday_name']}")
                    else:
                        print(f"  ✗ 祝日ではありません")
            
            except ValueError:
                print("無効な日付形式です。YYYY-MM-DD形式で入力してください")
            except KeyboardInterrupt:
                print("\n終了します")
                break
            except Exception as e:
                print(f"エラー: {e}")


def main():
    """メイン関数"""
    
    parser = argparse.ArgumentParser(
        description='日本の祝日判定ツール',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  %(prog)s                           # 今日が祝日かチェック
  %(prog)s --date 2024-01-01         # 指定日をチェック
  %(prog)s --interactive             # 対話モード
  %(prog)s --range 2024-01-01 2024-01-31  # 期間内の祝日を表示
  %(prog)s --next 3                  # 次の3つの祝日を表示
        """
    )
    
    parser.add_argument(
        '--date', '-d',
        type=str,
        help='チェックする日付 (YYYY-MM-DD形式)'
    )
    
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='対話モードで実行'
    )
    
    parser.add_argument(
        '--range', '-r',
        nargs=2,
        metavar=('START', 'END'),
        help='期間内の祝日を表示 (開始日 終了日)'
    )
    
    parser.add_argument(
        '--next', '-n',
        type=int,
        default=5,
        metavar='COUNT',
        help='次のN個の祝日を表示 (デフォルト: 5)'
    )
    
    args = parser.parse_args()
    
    # 祝日チェッカーを初期化
    checker = SimpleHolidayChecker()
    
    try:
        if args.interactive:
            # 対話モード
            checker.interactive_mode()
        
        elif args.range:
            # 期間指定モード
            start_date = datetime.strptime(args.range[0], '%Y-%m-%d').date()
            end_date = datetime.strptime(args.range[1], '%Y-%m-%d').date()
            
            print(f"期間: {start_date} - {end_date}")
            holidays = checker.check_date_range(start_date, end_date)
            
            if holidays:
                print(f"\n期間内の祝日 ({len(holidays)}件):")
                for holiday in holidays:
                    print(f"  {holiday['date']} ({holiday['weekday_jp']}) - {holiday['holiday_name']}")
            else:
                print("期間内に祝日はありません")
        
        elif args.date:
            # 指定日チェックモード
            check_date = datetime.strptime(args.date, '%Y-%m-%d').date()
            result = checker.check_single_date(check_date)
            
            print(f"日付: {result['date']} ({result['weekday_jp']}曜日)")
            
            if result['is_holiday']:
                print(f"✓ 祝日です: {result['holiday_name']}")
            else:
                print("✗ 祝日ではありません")
        
        else:
            # デフォルト: 今日をチェック + 次の祝日表示
            today = date.today()
            result = checker.check_single_date(today)
            
            print(f"今日: {result['date']} ({result['weekday_jp']}曜日)")
            
            if result['is_holiday']:
                print(f"✓ 今日は祝日です: {result['holiday_name']}")
            else:
                print("✗ 今日は祝日ではありません")
            
            # 次の祝日も表示
            next_holidays = checker.get_next_holidays(today, args.next)
            if next_holidays:
                print(f"\n次の祝日 ({len(next_holidays)}件):")
                for holiday in next_holidays:
                    days_until = (holiday['date'] - today).days
                    print(f"  {holiday['date']} ({holiday['weekday_jp']}) - {holiday['holiday_name']} (あと{days_until}日)")
    
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