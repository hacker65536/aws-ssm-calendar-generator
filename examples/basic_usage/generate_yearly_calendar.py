#!/usr/bin/env python3
"""
年間カレンダー生成スクリプト

このスクリプトは、指定された年の日本の祝日カレンダーを
ICS形式で生成する基本的な使用例を示します。

使用方法:
    python generate_yearly_calendar.py --year 2024
    python generate_yearly_calendar.py --year 2024 --exclude-sundays
    python generate_yearly_calendar.py --year 2024 --output custom_calendar.ics
"""

import sys
import os
from datetime import date, datetime
import argparse
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.japanese_holidays import JapaneseHolidays
from src.ics_generator import ICSGenerator
from src.error_handler import handle_error


class YearlyCalendarGenerator:
    """年間カレンダー生成器"""
    
    def __init__(self, exclude_sunday_holidays: bool = True):
        """初期化
        
        Args:
            exclude_sunday_holidays: 日曜祝日を除外するか
        """
        print("カレンダー生成器を初期化中...")
        
        try:
            self.holidays = JapaneseHolidays()
            self.generator = ICSGenerator(
                japanese_holidays=self.holidays,
                exclude_sunday_holidays=exclude_sunday_holidays
            )
            self.exclude_sundays = exclude_sunday_holidays
            print("✓ 初期化完了")
        except Exception as e:
            print(f"✗ 初期化エラー: {e}")
            raise
    
    def analyze_year_holidays(self, year: int) -> dict:
        """年間祝日の分析"""
        
        year_holidays = self.holidays.get_holidays_by_year(year)
        
        # 月別集計
        monthly_count = {}
        for month in range(1, 13):
            monthly_count[month] = 0
        
        # 曜日別集計
        weekday_count = {i: 0 for i in range(7)}
        weekday_names = ['月', '火', '水', '木', '金', '土', '日']
        
        # 日曜祝日の検出
        sunday_holidays = []
        
        for holiday_date, holiday_name in year_holidays:
            monthly_count[holiday_date.month] += 1
            weekday = holiday_date.weekday()
            weekday_count[weekday] += 1
            
            # 日曜日の祝日
            if weekday == 6:  # 日曜日
                sunday_holidays.append((holiday_date, holiday_name))
        
        analysis = {
            'year': year,
            'total_holidays': len(year_holidays),
            'sunday_holidays': sunday_holidays,
            'sunday_count': len(sunday_holidays),
            'monthly_distribution': monthly_count,
            'weekday_distribution': {
                weekday_names[i]: count for i, count in weekday_count.items()
            },
            'holidays_list': year_holidays
        }
        
        return analysis
    
    def generate_calendar(self, year: int, output_file: str = None) -> dict:
        """年間カレンダーの生成
        
        Args:
            year: 対象年
            output_file: 出力ファイル名（省略時は自動生成）
            
        Returns:
            生成結果の辞書
        """
        
        print(f"\n{year}年の祝日カレンダーを生成中...")
        
        # 年間祝日の分析
        analysis = self.analyze_year_holidays(year)
        
        # 出力ファイル名の決定
        if output_file is None:
            suffix = "_exclude_sunday" if self.exclude_sundays else "_include_sunday"
            output_file = f"japanese_holidays_{year}{suffix}.ics"
        
        # 出力ディレクトリの作成
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # ICSカレンダーの生成
            calendar = self.generator.create_aws_ssm_calendar()
            
            # 祝日イベントの追加
            holidays_to_include = analysis['holidays_list']
            
            # 日曜祝日の除外処理
            if self.exclude_sundays:
                holidays_to_include = [
                    (holiday_date, holiday_name) 
                    for holiday_date, holiday_name in analysis['holidays_list']
                    if holiday_date.weekday() != 6  # 日曜日以外
                ]
            
            events = self.generator.convert_holidays_to_events(holidays_to_include)
            
            for event in events:
                calendar.add_component(event)
            
            # ファイル保存
            self.generator.save_to_file(str(output_path))
            
            # 生成統計の取得
            stats = self.generator.get_generation_stats()
            
            result = {
                'success': True,
                'output_file': str(output_path),
                'year': year,
                'total_holidays': analysis['total_holidays'],
                'included_holidays': len(holidays_to_include),
                'excluded_holidays': analysis['total_holidays'] - len(holidays_to_include),
                'sunday_holidays': analysis['sunday_holidays'],
                'file_size': stats.get('file_size_bytes', 0),
                'generation_time': stats.get('generation_time_ms', 0),
                'analysis': analysis
            }
            
            print(f"✓ カレンダー生成完了: {output_path}")
            
            return result
            
        except Exception as e:
            print(f"✗ カレンダー生成エラー: {e}")
            return {
                'success': False,
                'error': str(e),
                'year': year,
                'analysis': analysis
            }
    
    def print_generation_summary(self, result: dict):
        """生成結果のサマリー表示"""
        
        if not result['success']:
            print(f"\n❌ 生成失敗: {result['error']}")
            return
        
        print(f"\n📅 {result['year']}年 祝日カレンダー生成結果")
        print("=" * 50)
        
        print(f"出力ファイル: {result['output_file']}")
        print(f"ファイルサイズ: {result['file_size']:,} bytes")
        print(f"生成時間: {result['generation_time']:.1f} ms")
        
        print(f"\n📊 祝日統計:")
        print(f"  総祝日数: {result['total_holidays']} 日")
        print(f"  含まれる祝日: {result['included_holidays']} 日")
        
        if result['excluded_holidays'] > 0:
            print(f"  除外された祝日: {result['excluded_holidays']} 日")
            print(f"  除外された日曜祝日:")
            for holiday_date, holiday_name in result['sunday_holidays']:
                print(f"    {holiday_date} - {holiday_name}")
        
        # 月別分布
        analysis = result['analysis']
        print(f"\n📈 月別祝日分布:")
        month_names = [
            '1月', '2月', '3月', '4月', '5月', '6月',
            '7月', '8月', '9月', '10月', '11月', '12月'
        ]
        
        for month, count in analysis['monthly_distribution'].items():
            if count > 0:
                print(f"  {month_names[month-1]}: {count} 日")
        
        # 曜日別分布
        print(f"\n📊 曜日別祝日分布:")
        for weekday, count in analysis['weekday_distribution'].items():
            if count > 0:
                print(f"  {weekday}曜日: {count} 日")
    
    def generate_multiple_years(self, start_year: int, end_year: int, output_dir: str = "output") -> list:
        """複数年のカレンダーを一括生成"""
        
        results = []
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        print(f"\n📅 {start_year}-{end_year}年の一括生成を開始...")
        
        for year in range(start_year, end_year + 1):
            suffix = "_exclude_sunday" if self.exclude_sundays else "_include_sunday"
            output_file = output_path / f"japanese_holidays_{year}{suffix}.ics"
            
            result = self.generate_calendar(year, str(output_file))
            results.append(result)
            
            if result['success']:
                print(f"  ✓ {year}年: {result['included_holidays']}祝日")
            else:
                print(f"  ✗ {year}年: エラー")
        
        # 一括生成サマリー
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        
        print(f"\n📊 一括生成結果:")
        print(f"  成功: {len(successful)} 年")
        print(f"  失敗: {len(failed)} 年")
        
        if successful:
            total_holidays = sum(r['included_holidays'] for r in successful)
            total_size = sum(r['file_size'] for r in successful)
            print(f"  総祝日数: {total_holidays} 日")
            print(f"  総ファイルサイズ: {total_size:,} bytes")
        
        return results


def main():
    """メイン関数"""
    
    parser = argparse.ArgumentParser(
        description='日本の祝日年間カレンダー生成ツール',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  %(prog)s --year 2024                    # 2024年のカレンダー生成
  %(prog)s --year 2024 --include-sundays  # 日曜祝日も含める
  %(prog)s --year 2024 --output my_cal.ics # 出力ファイル指定
  %(prog)s --range 2024 2026              # 複数年一括生成
        """
    )
    
    parser.add_argument(
        '--year', '-y',
        type=int,
        default=datetime.now().year,
        help='生成する年 (デフォルト: 今年)'
    )
    
    parser.add_argument(
        '--range', '-r',
        nargs=2,
        type=int,
        metavar=('START', 'END'),
        help='複数年の範囲指定 (開始年 終了年)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='出力ファイル名 (省略時は自動生成)'
    )
    
    parser.add_argument(
        '--include-sundays',
        action='store_true',
        help='日曜祝日も含める (デフォルト: 除外)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='output',
        help='出力ディレクトリ (複数年生成時)'
    )
    
    parser.add_argument(
        '--analyze-only',
        action='store_true',
        help='分析のみ実行 (ファイル生成しない)'
    )
    
    args = parser.parse_args()
    
    try:
        # カレンダー生成器の初期化
        generator = YearlyCalendarGenerator(
            exclude_sunday_holidays=not args.include_sundays
        )
        
        if args.analyze_only:
            # 分析のみモード
            year = args.year
            analysis = generator.analyze_year_holidays(year)
            
            print(f"\n📊 {year}年 祝日分析結果")
            print("=" * 40)
            print(f"総祝日数: {analysis['total_holidays']} 日")
            print(f"日曜祝日数: {analysis['sunday_count']} 日")
            
            print(f"\n祝日一覧:")
            for holiday_date, holiday_name in analysis['holidays_list']:
                weekday = ['月', '火', '水', '木', '金', '土', '日'][holiday_date.weekday()]
                sunday_mark = " (日曜)" if holiday_date.weekday() == 6 else ""
                print(f"  {holiday_date} ({weekday}) - {holiday_name}{sunday_mark}")
        
        elif args.range:
            # 複数年生成モード
            start_year, end_year = args.range
            results = generator.generate_multiple_years(start_year, end_year, args.output_dir)
            
            # 詳細結果表示
            for result in results:
                if result['success']:
                    generator.print_generation_summary(result)
        
        else:
            # 単年生成モード
            result = generator.generate_calendar(args.year, args.output)
            generator.print_generation_summary(result)
    
    except KeyboardInterrupt:
        print("\n処理を中断しました")
        sys.exit(0)
    
    except Exception as e:
        print(f"予期しないエラー: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()