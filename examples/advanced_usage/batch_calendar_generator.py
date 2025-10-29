#!/usr/bin/env python3
"""
バッチカレンダー生成スクリプト

このスクリプトは、複数年度のカレンダーを効率的に一括生成する
高度な使用例を示します。パフォーマンス最適化とエラーハンドリングを含みます。

使用方法:
    python batch_calendar_generator.py --years 2024 2025 2026
    python batch_calendar_generator.py --range 2020 2030 --parallel
    python batch_calendar_generator.py --config batch_config.json
"""

import sys
import os
import json
import time
from datetime import date, datetime
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
import logging

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.japanese_holidays import JapaneseHolidays
from src.ics_generator import ICSGenerator
from src.error_handler import handle_error


class BatchCalendarGenerator:
    """バッチカレンダー生成器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """初期化
        
        Args:
            config: 設定辞書
        """
        self.config = config or self._default_config()
        self.logger = self._setup_logging()
        
        # パフォーマンス監視設定
        self.enable_monitoring = self.config.get('enable_monitoring', False)
        
        self.logger.info("バッチカレンダー生成器を初期化中...")
        
        try:
            self.holidays = JapaneseHolidays(enable_monitoring=self.enable_monitoring)
            self.logger.info("✓ 祝日データの初期化完了")
        except Exception as e:
            self.logger.error(f"✗ 初期化エラー: {e}")
            raise
    
    def _default_config(self) -> Dict[str, Any]:
        """デフォルト設定"""
        return {
            'output_directory': 'output/batch_calendars',
            'exclude_sunday_holidays': True,
            'parallel_processing': True,
            'max_workers': 4,
            'enable_monitoring': False,
            'file_format': 'ics',
            'compression': False,
            'backup_existing': True,
            'generate_summary': True,
            'log_level': 'INFO'
        }
    
    def _setup_logging(self) -> logging.Logger:
        """ログ設定"""
        logger = logging.getLogger('BatchCalendarGenerator')
        logger.setLevel(getattr(logging, self.config.get('log_level', 'INFO')))
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def generate_single_calendar(self, year: int) -> Dict[str, Any]:
        """単一年のカレンダー生成
        
        Args:
            year: 対象年
            
        Returns:
            生成結果辞書
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"📅 {year}年のカレンダー生成開始")
            
            # ICSジェネレーター初期化
            generator = ICSGenerator(
                japanese_holidays=self.holidays,
                exclude_sunday_holidays=self.config['exclude_sunday_holidays']
            )
            
            # 出力ファイルパス
            output_dir = Path(self.config['output_directory'])
            output_dir.mkdir(parents=True, exist_ok=True)
            
            suffix = "_exclude_sunday" if self.config['exclude_sunday_holidays'] else "_include_sunday"
            filename = f"japanese_holidays_{year}{suffix}.ics"
            output_path = output_dir / filename
            
            # 既存ファイルのバックアップ
            if output_path.exists() and self.config['backup_existing']:
                backup_path = output_path.with_suffix(f'.backup_{int(time.time())}.ics')
                output_path.rename(backup_path)
                self.logger.info(f"既存ファイルをバックアップ: {backup_path}")
            
            # 祝日データ取得
            year_holidays = self.holidays.get_holidays_by_year(year)
            
            # 日曜祝日の処理
            holidays_to_include = year_holidays
            sunday_holidays = []
            
            if self.config['exclude_sunday_holidays']:
                holidays_to_include = []
                for holiday_date, holiday_name in year_holidays:
                    if holiday_date.weekday() == 6:  # 日曜日
                        sunday_holidays.append((holiday_date, holiday_name))
                    else:
                        holidays_to_include.append((holiday_date, holiday_name))
            
            # ICSカレンダー生成
            calendar = generator.create_aws_ssm_calendar()
            events = generator.convert_holidays_to_events(holidays_to_include)
            
            for event in events:
                calendar.add_component(event)
            
            # ファイル保存
            generator.save_to_file(str(output_path))
            
            # 統計情報取得
            stats = generator.get_generation_stats()
            generation_time = time.time() - start_time
            
            result = {
                'year': year,
                'success': True,
                'output_file': str(output_path),
                'total_holidays': len(year_holidays),
                'included_holidays': len(holidays_to_include),
                'excluded_holidays': len(sunday_holidays),
                'sunday_holidays': sunday_holidays,
                'file_size': stats.get('file_size_bytes', 0),
                'generation_time': generation_time,
                'ics_generation_time': stats.get('generation_time_ms', 0)
            }
            
            self.logger.info(f"✓ {year}年完了: {len(holidays_to_include)}祝日, {generation_time:.2f}秒")
            
            return result
            
        except Exception as e:
            generation_time = time.time() - start_time
            
            self.logger.error(f"✗ {year}年エラー: {e}")
            
            return {
                'year': year,
                'success': False,
                'error': str(e),
                'generation_time': generation_time
            }
    
    def generate_batch_sequential(self, years: List[int]) -> List[Dict[str, Any]]:
        """順次バッチ生成
        
        Args:
            years: 対象年のリスト
            
        Returns:
            生成結果のリスト
        """
        self.logger.info(f"📊 順次バッチ生成開始: {len(years)}年分")
        
        results = []
        
        for i, year in enumerate(years, 1):
            self.logger.info(f"進捗: {i}/{len(years)} ({i/len(years)*100:.1f}%)")
            
            result = self.generate_single_calendar(year)
            results.append(result)
            
            # メモリ管理
            if i % 5 == 0:  # 5年ごとにガベージコレクション
                import gc
                gc.collect()
        
        return results
    
    def generate_batch_parallel(self, years: List[int]) -> List[Dict[str, Any]]:
        """並列バッチ生成
        
        Args:
            years: 対象年のリスト
            
        Returns:
            生成結果のリスト
        """
        max_workers = min(self.config['max_workers'], len(years))
        self.logger.info(f"🚀 並列バッチ生成開始: {len(years)}年分, {max_workers}ワーカー")
        
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 全タスクを投入
            future_to_year = {
                executor.submit(self.generate_single_calendar, year): year 
                for year in years
            }
            
            # 完了順に結果を収集
            completed = 0
            for future in as_completed(future_to_year):
                year = future_to_year[future]
                
                try:
                    result = future.result()
                    results.append(result)
                    
                    completed += 1
                    progress = completed / len(years) * 100
                    self.logger.info(f"進捗: {completed}/{len(years)} ({progress:.1f}%)")
                    
                except Exception as e:
                    self.logger.error(f"年{year}の処理でエラー: {e}")
                    results.append({
                        'year': year,
                        'success': False,
                        'error': str(e),
                        'generation_time': 0
                    })
        
        # 年順にソート
        results.sort(key=lambda x: x['year'])
        
        return results
    
    def generate_batch(self, years: List[int]) -> Dict[str, Any]:
        """バッチ生成メイン処理
        
        Args:
            years: 対象年のリスト
            
        Returns:
            バッチ生成結果
        """
        batch_start_time = time.time()
        
        self.logger.info(f"🎯 バッチカレンダー生成開始")
        self.logger.info(f"対象年: {min(years)}-{max(years)} ({len(years)}年分)")
        self.logger.info(f"並列処理: {'有効' if self.config['parallel_processing'] else '無効'}")
        
        # バッチ生成実行
        if self.config['parallel_processing'] and len(years) > 1:
            results = self.generate_batch_parallel(years)
        else:
            results = self.generate_batch_sequential(years)
        
        batch_time = time.time() - batch_start_time
        
        # 結果集計
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        
        total_holidays = sum(r.get('included_holidays', 0) for r in successful)
        total_size = sum(r.get('file_size', 0) for r in successful)
        avg_time = sum(r.get('generation_time', 0) for r in successful) / len(successful) if successful else 0
        
        batch_result = {
            'batch_start_time': batch_start_time,
            'batch_duration': batch_time,
            'total_years': len(years),
            'successful_years': len(successful),
            'failed_years': len(failed),
            'total_holidays': total_holidays,
            'total_file_size': total_size,
            'average_generation_time': avg_time,
            'results': results,
            'config': self.config
        }
        
        # サマリー生成
        if self.config['generate_summary']:
            self._generate_summary_report(batch_result)
        
        self.logger.info(f"🎉 バッチ生成完了: {len(successful)}成功, {len(failed)}失敗, {batch_time:.2f}秒")
        
        return batch_result
    
    def _generate_summary_report(self, batch_result: Dict[str, Any]):
        """サマリーレポート生成"""
        
        output_dir = Path(self.config['output_directory'])
        summary_file = output_dir / f"batch_summary_{int(time.time())}.json"
        
        # 人間可読サマリー
        readable_summary = self._format_readable_summary(batch_result)
        readable_file = output_dir / f"batch_summary_{int(time.time())}.txt"
        
        try:
            # JSON形式で保存
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(batch_result, f, indent=2, ensure_ascii=False, default=str)
            
            # 人間可読形式で保存
            with open(readable_file, 'w', encoding='utf-8') as f:
                f.write(readable_summary)
            
            self.logger.info(f"📄 サマリーレポート生成: {summary_file}")
            self.logger.info(f"📄 可読サマリー生成: {readable_file}")
            
        except Exception as e:
            self.logger.error(f"サマリー生成エラー: {e}")
    
    def _format_readable_summary(self, batch_result: Dict[str, Any]) -> str:
        """人間可読サマリーフォーマット"""
        
        lines = []
        lines.append("=" * 60)
        lines.append("バッチカレンダー生成サマリーレポート")
        lines.append("=" * 60)
        
        # 基本情報
        lines.append(f"生成日時: {datetime.fromtimestamp(batch_result['batch_start_time'])}")
        lines.append(f"処理時間: {batch_result['batch_duration']:.2f}秒")
        lines.append(f"対象年数: {batch_result['total_years']}年")
        lines.append("")
        
        # 結果サマリー
        lines.append("📊 処理結果:")
        lines.append(f"  成功: {batch_result['successful_years']}年")
        lines.append(f"  失敗: {batch_result['failed_years']}年")
        lines.append(f"  成功率: {batch_result['successful_years']/batch_result['total_years']*100:.1f}%")
        lines.append("")
        
        # 統計情報
        if batch_result['successful_years'] > 0:
            lines.append("📈 統計情報:")
            lines.append(f"  総祝日数: {batch_result['total_holidays']:,}日")
            lines.append(f"  総ファイルサイズ: {batch_result['total_file_size']:,} bytes")
            lines.append(f"  平均生成時間: {batch_result['average_generation_time']:.3f}秒/年")
            lines.append("")
        
        # 設定情報
        config = batch_result['config']
        lines.append("⚙️ 設定:")
        lines.append(f"  出力ディレクトリ: {config['output_directory']}")
        lines.append(f"  日曜祝日除外: {'有効' if config['exclude_sunday_holidays'] else '無効'}")
        lines.append(f"  並列処理: {'有効' if config['parallel_processing'] else '無効'}")
        if config['parallel_processing']:
            lines.append(f"  最大ワーカー数: {config['max_workers']}")
        lines.append("")
        
        # 詳細結果
        lines.append("📋 詳細結果:")
        for result in batch_result['results']:
            if result['success']:
                lines.append(f"  ✓ {result['year']}年: {result['included_holidays']}祝日, "
                           f"{result['file_size']:,}bytes, {result['generation_time']:.3f}秒")
            else:
                lines.append(f"  ✗ {result['year']}年: エラー - {result['error']}")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    @classmethod
    def load_config_from_file(cls, config_file: str) -> Dict[str, Any]:
        """設定ファイルから設定を読み込み"""
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # デフォルト設定とマージ
            default_config = cls()._default_config()
            default_config.update(config)
            
            return default_config
            
        except Exception as e:
            raise ValueError(f"設定ファイル読み込みエラー: {e}")


def main():
    """メイン関数"""
    
    parser = argparse.ArgumentParser(
        description='バッチカレンダー生成ツール',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  %(prog)s --years 2024 2025 2026           # 指定年のカレンダー生成
  %(prog)s --range 2020 2030                # 範囲指定
  %(prog)s --range 2020 2030 --parallel     # 並列処理
  %(prog)s --config batch_config.json       # 設定ファイル使用
  %(prog)s --years 2024 --include-sundays   # 日曜祝日も含める
        """
    )
    
    parser.add_argument(
        '--years',
        nargs='+',
        type=int,
        help='生成する年のリスト'
    )
    
    parser.add_argument(
        '--range',
        nargs=2,
        type=int,
        metavar=('START', 'END'),
        help='年の範囲指定 (開始年 終了年)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='設定ファイルのパス'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        help='出力ディレクトリ'
    )
    
    parser.add_argument(
        '--parallel',
        action='store_true',
        help='並列処理を有効にする'
    )
    
    parser.add_argument(
        '--max-workers',
        type=int,
        default=4,
        help='最大ワーカー数'
    )
    
    parser.add_argument(
        '--include-sundays',
        action='store_true',
        help='日曜祝日も含める'
    )
    
    parser.add_argument(
        '--no-summary',
        action='store_true',
        help='サマリーレポートを生成しない'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='ログレベル'
    )
    
    args = parser.parse_args()
    
    try:
        # 設定の準備
        if args.config:
            config = BatchCalendarGenerator.load_config_from_file(args.config)
        else:
            config = BatchCalendarGenerator()._default_config()
        
        # コマンドライン引数で設定を上書き
        if args.output_dir:
            config['output_directory'] = args.output_dir
        
        if args.parallel:
            config['parallel_processing'] = True
        
        config['max_workers'] = args.max_workers
        config['exclude_sunday_holidays'] = not args.include_sundays
        config['generate_summary'] = not args.no_summary
        config['log_level'] = args.log_level
        
        # 対象年の決定
        if args.years:
            years = sorted(args.years)
        elif args.range:
            start_year, end_year = args.range
            years = list(range(start_year, end_year + 1))
        else:
            # デフォルト: 今年から3年分
            current_year = datetime.now().year
            years = [current_year, current_year + 1, current_year + 2]
        
        # バッチ生成器の初期化と実行
        generator = BatchCalendarGenerator(config)
        batch_result = generator.generate_batch(years)
        
        # 結果表示
        print(f"\n🎉 バッチ生成完了!")
        print(f"成功: {batch_result['successful_years']}/{batch_result['total_years']}年")
        print(f"処理時間: {batch_result['batch_duration']:.2f}秒")
        
        if batch_result['failed_years'] > 0:
            print(f"\n❌ 失敗した年:")
            for result in batch_result['results']:
                if not result['success']:
                    print(f"  {result['year']}年: {result['error']}")
    
    except KeyboardInterrupt:
        print("\n処理を中断しました")
        sys.exit(0)
    
    except Exception as e:
        print(f"予期しないエラー: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()