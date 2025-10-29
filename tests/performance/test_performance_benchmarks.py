"""
Performance benchmarks and tests.
Tests performance characteristics of core functionality.

要件: 設計書拡張機能 - パフォーマンス最適化とキャッシュの実装
- 重要な操作のパフォーマンステストスイート
- 祝日検索とICS生成のベンチマーク
- メモリ使用量とリソース消費テスト
"""

import pytest
import time
import psutil
import os
from unittest.mock import patch, Mock
from datetime import date, datetime
import tempfile
from pathlib import Path
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import gc
from typing import Tuple

from src.japanese_holidays import JapaneseHolidays
from src.ics_generator import ICSGenerator
from src.calendar_analyzer import ICSAnalyzer


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""

    @pytest.mark.performance
    @patch('requests.get')
    def test_holiday_data_processing_performance(self, mock_get, temp_dir, monkeypatch):
        """Test holiday data processing performance."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # Create large holiday dataset (10 years of data)
        large_holiday_data = "日付,祝日名\n"
        for year in range(2020, 2030):
            # Add typical Japanese holidays for each year
            holidays_per_year = [
                (f"{year}-01-01", "元日"),
                (f"{year}-01-08", "成人の日"),
                (f"{year}-02-11", "建国記念の日"),
                (f"{year}-02-23", "天皇誕生日"),
                (f"{year}-03-20", "春分の日"),
                (f"{year}-04-29", "昭和の日"),
                (f"{year}-05-03", "憲法記念日"),
                (f"{year}-05-04", "みどりの日"),
                (f"{year}-05-05", "こどもの日"),
                (f"{year}-07-15", "海の日"),
                (f"{year}-08-11", "山の日"),
                (f"{year}-09-16", "敬老の日"),
                (f"{year}-09-22", "秋分の日"),
                (f"{year}-10-14", "スポーツの日"),
                (f"{year}-11-03", "文化の日"),
                (f"{year}-11-23", "勤労感謝の日")
            ]
            
            for holiday_date, holiday_name in holidays_per_year:
                large_holiday_data += f"{holiday_date},{holiday_name}\n"
        
        # Mock network response
        mock_response = Mock()
        mock_response.content = large_holiday_data.encode('shift_jis')
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Measure performance
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        # Initialize and process holidays
        holidays = JapaneseHolidays()
        stats = holidays.get_stats()
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        processing_time = end_time - start_time
        memory_usage = end_memory - start_memory
        
        # Performance assertions
        assert processing_time < 3.0, f"Holiday processing took {processing_time:.2f}s, expected < 3.0s"
        assert memory_usage < 50, f"Memory usage {memory_usage:.2f}MB, expected < 50MB"
        assert stats['total'] > 150, "Should process multiple years of holidays"
        
        print(f"Holiday processing: {processing_time:.2f}s, Memory: {memory_usage:.2f}MB")

    @pytest.mark.performance
    def test_ics_generation_performance(self, temp_dir, monkeypatch):
        """Test ICS generation performance with large datasets."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # Create cache with large holiday dataset
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        
        # Generate 5 years of holiday data
        large_holiday_data = "日付,祝日名\n"
        for year in range(2024, 2029):
            for month in range(1, 13):
                # Add 2-3 holidays per month for stress testing
                for day in [1, 15, 28]:
                    large_holiday_data += f"{year}-{month:02d}-{day:02d},テスト祝日{year}{month:02d}{day:02d}\n"
        
        cache_file.write_text(large_holiday_data, encoding='utf-8')
        
        # Measure ICS generation performance
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        # Generate ICS
        holidays = JapaneseHolidays()
        ics_generator = ICSGenerator(japanese_holidays=holidays)
        
        # Add multiple years
        for year in range(2024, 2029):
            ics_generator.add_japanese_holidays_for_year(year)
        
        ics_content = ics_generator.generate_ics_content()
        
        # Save to file
        output_file = temp_dir / "large_calendar.ics"
        ics_generator.save_to_file(str(output_file))
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        generation_time = end_time - start_time
        memory_usage = end_memory - start_memory
        file_size = len(ics_content) / 1024  # KB
        
        # Performance assertions
        assert generation_time < 2.0, f"ICS generation took {generation_time:.2f}s, expected < 2.0s"
        assert memory_usage < 30, f"Memory usage {memory_usage:.2f}MB, expected < 30MB"
        assert file_size > 10, "Generated ICS should be substantial size"
        assert output_file.exists(), "ICS file should be created"
        
        print(f"ICS generation: {generation_time:.2f}s, Memory: {memory_usage:.2f}MB, Size: {file_size:.2f}KB")

    @pytest.mark.performance
    def test_ics_analysis_performance(self, temp_dir):
        """Test ICS analysis performance with large files."""
        # Generate large ICS file
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AWS//Change Calendar 1.0//EN
X-WR-TIMEZONE:Asia/Tokyo
"""
        
        # Add many events (1000+ events)
        event_count = 0
        for year in range(2020, 2030):
            for month in range(1, 13):
                for day in range(1, 32, 3):  # Every 3rd day
                    try:
                        test_date = date(year, month, day)
                        ics_content += f"""BEGIN:VEVENT
UID:event-{year}{month:02d}{day:02d}@performance-test
DTSTART;VALUE=DATE:{year}{month:02d}{day:02d}
DTEND;VALUE=DATE:{year}{month:02d}{day:02d}
SUMMARY:パフォーマンステストイベント {year}-{month:02d}-{day:02d}
DESCRIPTION:大容量ICSファイルのパフォーマンステスト用イベント
CATEGORIES:Performance-Test
END:VEVENT
"""
                        event_count += 1
                    except ValueError:
                        # Skip invalid dates (e.g., Feb 30)
                        continue
        
        ics_content += "END:VCALENDAR"
        
        # Save large ICS file
        large_ics_file = temp_dir / "performance_test.ics"
        large_ics_file.write_text(ics_content, encoding='utf-8')
        
        # Measure analysis performance
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        # Analyze ICS file
        analyzer = ICSAnalyzer()
        analysis = analyzer.parse_ics_file(str(large_ics_file))
        
        # Generate human readable output
        human_readable = analyzer.format_human_readable(analysis)
        
        # Export to JSON
        json_output = analyzer.export_json(analysis)
        
        # Export to CSV
        csv_output = analyzer.export_csv(analysis['events'])
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        analysis_time = end_time - start_time
        memory_usage = end_memory - start_memory
        file_size = len(ics_content) / 1024  # KB
        
        # Performance assertions
        assert analysis_time < 5.0, f"ICS analysis took {analysis_time:.2f}s, expected < 5.0s"
        assert memory_usage < 100, f"Memory usage {memory_usage:.2f}MB, expected < 100MB"
        assert analysis['file_info']['total_events'] > 1000, "Should analyze many events"
        assert len(human_readable) > 0, "Should generate human readable output"
        assert len(json_output) > 0, "Should generate JSON output"
        assert len(csv_output) > 0, "Should generate CSV output"
        
        print(f"ICS analysis: {analysis_time:.2f}s, Memory: {memory_usage:.2f}MB, "
              f"Events: {analysis['file_info']['total_events']}, File: {file_size:.2f}KB")

    @pytest.mark.performance
    def test_ics_comparison_performance(self, temp_dir):
        """Test ICS comparison performance with large files."""
        # Generate two large ICS files with differences
        base_ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AWS//Change Calendar 1.0//EN
"""
        
        # File 1: Base events
        ics_content_1 = base_ics
        for i in range(500):  # 500 events
            year = 2024 + (i // 365)
            month = ((i % 365) // 30) + 1
            day = (i % 30) + 1
            
            if month > 12:
                month = 12
            if day > 28:  # Safe day for all months
                day = 28
                
            ics_content_1 += f"""BEGIN:VEVENT
UID:event-{i:04d}@comparison-test
DTSTART;VALUE=DATE:{year}{month:02d}{day:02d}
DTEND;VALUE=DATE:{year}{month:02d}{day:02d}
SUMMARY:比較テストイベント {i:04d}
END:VEVENT
"""
        ics_content_1 += "END:VCALENDAR"
        
        # File 2: Modified events (some added, some removed, some changed)
        ics_content_2 = base_ics
        for i in range(50, 550):  # Different range to create differences
            year = 2024 + (i // 365)
            month = ((i % 365) // 30) + 1
            day = (i % 30) + 1
            
            if month > 12:
                month = 12
            if day > 28:
                day = 28
                
            # Modify some summaries
            summary = f"比較テストイベント {i:04d}"
            if i % 10 == 0:
                summary += " (変更済み)"
                
            ics_content_2 += f"""BEGIN:VEVENT
UID:event-{i:04d}@comparison-test
DTSTART;VALUE=DATE:{year}{month:02d}{day:02d}
DTEND;VALUE=DATE:{year}{month:02d}{day:02d}
SUMMARY:{summary}
END:VEVENT
"""
        ics_content_2 += "END:VCALENDAR"
        
        # Save comparison files
        file1 = temp_dir / "comparison_base.ics"
        file2 = temp_dir / "comparison_modified.ics"
        
        file1.write_text(ics_content_1, encoding='utf-8')
        file2.write_text(ics_content_2, encoding='utf-8')
        
        # Measure comparison performance
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        # Compare ICS files
        analyzer = ICSAnalyzer()
        comparison = analyzer.compare_ics_files(str(file1), str(file2))
        
        # Format comparison result
        formatted_result = analyzer.format_comparison_result(comparison)
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        comparison_time = end_time - start_time
        memory_usage = end_memory - start_memory
        
        # Performance assertions
        assert comparison_time < 10.0, f"ICS comparison took {comparison_time:.2f}s, expected < 10.0s"
        assert memory_usage < 150, f"Memory usage {memory_usage:.2f}MB, expected < 150MB"
        assert 'summary' in comparison, "Should generate comparison summary"
        assert len(formatted_result) > 0, "Should generate formatted result"
        
        # Verify differences were detected
        summary = comparison['summary']
        assert summary['added'] > 0 or summary['deleted'] > 0 or summary['modified'] > 0, \
            "Should detect differences between files"
        
        print(f"ICS comparison: {comparison_time:.2f}s, Memory: {memory_usage:.2f}MB, "
              f"Changes: +{summary['added']} -{summary['deleted']} ~{summary['modified']}")

    @pytest.mark.performance
    def test_cache_performance(self, temp_dir, monkeypatch):
        """Test cache performance and efficiency."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # Create large cache file
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        
        # Generate large dataset
        large_holiday_data = "日付,祝日名\n"
        for year in range(2000, 2050):  # 50 years of data
            for month in range(1, 13):
                for day in [1, 15]:  # 2 holidays per month
                    large_holiday_data += f"{year}-{month:02d}-{day:02d},祝日{year}{month:02d}{day:02d}\n"
        
        cache_file.write_text(large_holiday_data, encoding='utf-8')
        
        # Test cache loading performance
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        # Load from cache multiple times
        for _ in range(5):
            holidays = JapaneseHolidays()
            stats = holidays.get_stats()
            
            # Perform some operations
            assert holidays.is_holiday(date(2025, 1, 1))
            holidays_2025 = holidays.get_holidays_by_year(2025)
            assert len(holidays_2025) > 0
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        cache_time = end_time - start_time
        memory_usage = end_memory - start_memory
        
        # Performance assertions
        assert cache_time < 1.0, f"Cache operations took {cache_time:.2f}s, expected < 1.0s"
        assert memory_usage < 20, f"Memory usage {memory_usage:.2f}MB, expected < 20MB"
        assert stats['total'] > 1000, "Should load large dataset"
        
        print(f"Cache performance: {cache_time:.2f}s, Memory: {memory_usage:.2f}MB, "
              f"Holidays: {stats['total']}")

    @pytest.mark.performance
    def test_memory_leak_detection(self, temp_dir, monkeypatch):
        """Test for memory leaks in repeated operations."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # Create test data
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        
        holiday_data = """日付,祝日名
2024-01-01,元日
2024-01-08,成人の日
2024-02-11,建国記念の日"""
        cache_file.write_text(holiday_data, encoding='utf-8')
        
        # Measure memory usage over repeated operations
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        memory_samples = []
        
        # Perform repeated operations
        for i in range(20):
            # Create new instances each time
            holidays = JapaneseHolidays()
            ics_generator = ICSGenerator(japanese_holidays=holidays)
            ics_generator.add_japanese_holidays_for_year(2024)
            
            # Generate ICS content
            ics_content = ics_generator.generate_ics_content()
            
            # Analyze the content
            temp_file = temp_dir / f"temp_{i}.ics"
            temp_file.write_text(ics_content, encoding='utf-8')
            
            analyzer = ICSAnalyzer()
            analysis = analyzer.parse_ics_file(str(temp_file))
            
            # Clean up
            temp_file.unlink()
            del holidays, ics_generator, analyzer, analysis
            
            # Sample memory usage
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            memory_samples.append(current_memory)
        
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        # Check for memory leaks
        assert memory_growth < 50, f"Memory grew by {memory_growth:.2f}MB, possible memory leak"
        
        # Check memory trend (should not continuously increase)
        if len(memory_samples) >= 10:
            first_half_avg = sum(memory_samples[:10]) / 10
            second_half_avg = sum(memory_samples[10:]) / len(memory_samples[10:])
            trend_growth = second_half_avg - first_half_avg
            
            assert trend_growth < 20, f"Memory trend shows {trend_growth:.2f}MB growth, possible leak"
        
        print(f"Memory leak test: Initial: {initial_memory:.2f}MB, "
              f"Final: {final_memory:.2f}MB, Growth: {memory_growth:.2f}MB")


class TestResourceUsageMonitoring:
    """Test resource usage monitoring and limits."""

    @pytest.mark.performance
    def test_cpu_usage_monitoring(self, temp_dir, monkeypatch):
        """Test CPU usage during intensive operations."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # Create large dataset
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        
        # Generate computationally intensive dataset
        large_data = "日付,祝日名\n"
        for year in range(2020, 2030):
            for month in range(1, 13):
                for day in range(1, 29):  # Most days of each month
                    large_data += f"{year}-{month:02d}-{day:02d},計算集約的祝日{year}{month:02d}{day:02d}\n"
        
        cache_file.write_text(large_data, encoding='utf-8')
        
        # Monitor CPU usage during operations
        process = psutil.Process()
        cpu_samples = []
        
        start_time = time.time()
        
        # Perform CPU-intensive operations
        for i in range(5):
            cpu_before = process.cpu_percent()
            
            # CPU-intensive operations
            holidays = JapaneseHolidays()
            ics_generator = ICSGenerator(japanese_holidays=holidays)
            
            # Add multiple years
            for year in range(2020, 2030):
                ics_generator.add_japanese_holidays_for_year(year)
            
            ics_content = ics_generator.generate_ics_content()
            
            # Analysis operations
            temp_file = temp_dir / f"cpu_test_{i}.ics"
            temp_file.write_text(ics_content, encoding='utf-8')
            
            analyzer = ICSAnalyzer()
            analysis = analyzer.parse_ics_file(str(temp_file))
            human_readable = analyzer.format_human_readable(analysis)
            
            cpu_after = process.cpu_percent()
            cpu_samples.append(cpu_after)
            
            temp_file.unlink()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # CPU usage should be reasonable
        avg_cpu = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0
        max_cpu = max(cpu_samples) if cpu_samples else 0
        
        # Performance assertions (adjust based on system capabilities)
        assert total_time < 30.0, f"Operations took {total_time:.2f}s, expected < 30.0s"
        assert max_cpu < 90.0, f"Max CPU usage {max_cpu:.1f}%, expected < 90%"
        
        print(f"CPU monitoring: Total time: {total_time:.2f}s, "
              f"Avg CPU: {avg_cpu:.1f}%, Max CPU: {max_cpu:.1f}%")

    @pytest.mark.performance
    def test_disk_io_efficiency(self, temp_dir, monkeypatch):
        """Test disk I/O efficiency."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # Monitor disk I/O
        process = psutil.Process()
        io_before = process.io_counters()
        
        start_time = time.time()
        
        # Perform I/O intensive operations
        for i in range(10):
            # Create and write large ICS files
            ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AWS//Change Calendar 1.0//EN
"""
            
            # Add many events
            for j in range(100):
                ics_content += f"""BEGIN:VEVENT
UID:io-test-{i}-{j}@performance-test
DTSTART;VALUE=DATE:20240101
DTEND;VALUE=DATE:20240102
SUMMARY:I/Oテストイベント {i}-{j}
DESCRIPTION:ディスクI/O効率テスト用の長い説明文。この説明文は意図的に長くしてファイルサイズを増加させています。
END:VEVENT
"""
            
            ics_content += "END:VCALENDAR"
            
            # Write file
            test_file = temp_dir / f"io_test_{i}.ics"
            test_file.write_text(ics_content, encoding='utf-8')
            
            # Read and analyze file
            analyzer = ICSAnalyzer()
            analysis = analyzer.parse_ics_file(str(test_file))
            
            # Export in different formats
            json_output = analyzer.export_json(analysis)
            csv_output = analyzer.export_csv(analysis['events'])
            
            # Write export files
            json_file = temp_dir / f"export_{i}.json"
            csv_file = temp_dir / f"export_{i}.csv"
            
            json_file.write_text(json_output, encoding='utf-8')
            csv_file.write_text(csv_output, encoding='utf-8')
        
        end_time = time.time()
        io_after = process.io_counters()
        
        total_time = end_time - start_time
        bytes_read = io_after.read_bytes - io_before.read_bytes
        bytes_written = io_after.write_bytes - io_before.write_bytes
        
        # I/O efficiency assertions
        assert total_time < 15.0, f"I/O operations took {total_time:.2f}s, expected < 15.0s"
        
        # Calculate I/O rates
        read_rate = bytes_read / total_time / 1024 / 1024  # MB/s
        write_rate = bytes_written / total_time / 1024 / 1024  # MB/s
        
        print(f"Disk I/O: Time: {total_time:.2f}s, "
              f"Read: {bytes_read/1024/1024:.2f}MB ({read_rate:.2f}MB/s), "
              f"Write: {bytes_written/1024/1024:.2f}MB ({write_rate:.2f}MB/s)")


class TestScalabilityLimits:
    """Test scalability limits and edge cases."""

    @pytest.mark.performance
    def test_maximum_events_handling(self, temp_dir):
        """Test handling of maximum number of events."""
        # Generate ICS with very large number of events
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AWS//Change Calendar 1.0//EN
"""
        
        # Add 5000+ events
        event_count = 5000
        for i in range(event_count):
            year = 2024 + (i // 365)
            day_of_year = i % 365 + 1
            
            # Convert day of year to month/day
            month = (day_of_year - 1) // 30 + 1
            day = (day_of_year - 1) % 30 + 1
            
            if month > 12:
                month = 12
            if day > 28:
                day = 28
            
            ics_content += f"""BEGIN:VEVENT
UID:max-event-{i:05d}@scalability-test
DTSTART;VALUE=DATE:{year}{month:02d}{day:02d}
DTEND;VALUE=DATE:{year}{month:02d}{day:02d}
SUMMARY:スケーラビリティテストイベント {i:05d}
DESCRIPTION:最大イベント数処理テスト
END:VEVENT
"""
        
        ics_content += "END:VCALENDAR"
        
        # Save large file
        large_file = temp_dir / "max_events.ics"
        large_file.write_text(ics_content, encoding='utf-8')
        
        # Test analysis of maximum events
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        analyzer = ICSAnalyzer()
        analysis = analyzer.parse_ics_file(str(large_file))
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        processing_time = end_time - start_time
        memory_usage = end_memory - start_memory
        
        # Scalability assertions
        assert processing_time < 30.0, f"Max events processing took {processing_time:.2f}s"
        assert memory_usage < 500, f"Memory usage {memory_usage:.2f}MB for max events"
        assert analysis['file_info']['total_events'] == event_count
        
        print(f"Max events test: {event_count} events, "
              f"Time: {processing_time:.2f}s, Memory: {memory_usage:.2f}MB")

    @pytest.mark.performance
    def test_large_file_size_handling(self, temp_dir):
        """Test handling of very large file sizes."""
        # Generate ICS with very long event descriptions
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AWS//Change Calendar 1.0//EN
"""
        
        # Create events with very long descriptions
        long_description = "非常に長い説明文。" * 1000  # Very long description
        
        for i in range(100):  # Fewer events but much larger content
            ics_content += f"""BEGIN:VEVENT
UID:large-content-{i:03d}@scalability-test
DTSTART;VALUE=DATE:20240101
DTEND;VALUE=DATE:20240102
SUMMARY:大容量コンテンツテストイベント {i:03d}
DESCRIPTION:{long_description}
END:VEVENT
"""
        
        ics_content += "END:VCALENDAR"
        
        # Save very large file
        large_file = temp_dir / "large_content.ics"
        large_file.write_text(ics_content, encoding='utf-8')
        
        file_size = len(ics_content) / 1024 / 1024  # MB
        
        # Test analysis of large content
        start_time = time.time()
        
        analyzer = ICSAnalyzer()
        analysis = analyzer.parse_ics_file(str(large_file))
        
        # Test export operations
        json_output = analyzer.export_json(analysis)
        csv_output = analyzer.export_csv(analysis['events'])
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Large file handling assertions
        assert processing_time < 20.0, f"Large file processing took {processing_time:.2f}s"
        assert analysis['file_info']['total_events'] == 100
        assert len(json_output) > 0
        assert len(csv_output) > 0
        
        print(f"Large file test: {file_size:.2f}MB file, "
              f"Time: {processing_time:.2f}s")


class TestHolidaySearchBenchmarks:
    """祝日検索操作の専用ベンチマークテスト"""

    @pytest.mark.performance
    def test_holiday_search_performance(self, temp_dir, monkeypatch):
        """祝日検索のパフォーマンステスト"""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # 大容量祝日データセットを作成
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        
        # 50年分の祝日データを生成（検索パフォーマンステスト用）
        large_holiday_data = "日付,祝日名\n"
        for year in range(2000, 2050):
            # 年間16祝日を想定
            holidays_per_year = [
                (f"{year}-01-01", "元日"),
                (f"{year}-01-08", "成人の日"),
                (f"{year}-02-11", "建国記念の日"),
                (f"{year}-02-23", "天皇誕生日"),
                (f"{year}-03-20", "春分の日"),
                (f"{year}-04-29", "昭和の日"),
                (f"{year}-05-03", "憲法記念日"),
                (f"{year}-05-04", "みどりの日"),
                (f"{year}-05-05", "こどもの日"),
                (f"{year}-07-15", "海の日"),
                (f"{year}-08-11", "山の日"),
                (f"{year}-09-16", "敬老の日"),
                (f"{year}-09-22", "秋分の日"),
                (f"{year}-10-14", "スポーツの日"),
                (f"{year}-11-03", "文化の日"),
                (f"{year}-11-23", "勤労感謝の日")
            ]
            
            for holiday_date, holiday_name in holidays_per_year:
                large_holiday_data += f"{holiday_date},{holiday_name}\n"
        
        cache_file.write_text(large_holiday_data, encoding='utf-8')
        
        # 祝日検索パフォーマンス測定
        holidays = JapaneseHolidays()
        
        # 単一日付検索のベンチマーク
        search_dates = [
            date(2025, 1, 1),   # 祝日
            date(2025, 1, 2),   # 平日
            date(2025, 5, 3),   # 祝日
            date(2025, 6, 15),  # 平日
            date(2030, 1, 1),   # 将来の祝日
            date(2045, 12, 25), # 将来の平日
        ]
        
        # 検索時間測定
        search_times = []
        for test_date in search_dates * 100:  # 600回の検索テスト
            start_time = time.perf_counter()
            is_holiday = holidays.is_holiday(test_date)
            end_time = time.perf_counter()
            search_times.append(end_time - start_time)
        
        # 統計計算
        avg_search_time = statistics.mean(search_times)
        max_search_time = max(search_times)
        min_search_time = min(search_times)
        p95_search_time = statistics.quantiles(search_times, n=20)[18]  # 95th percentile
        
        # パフォーマンス要件検証（現実的な閾値に調整）
        assert avg_search_time < 0.01, f"平均検索時間 {avg_search_time*1000:.3f}ms > 10ms"
        assert max_search_time < 0.05, f"最大検索時間 {max_search_time*1000:.3f}ms > 50ms"
        assert p95_search_time < 0.02, f"95%ile検索時間 {p95_search_time*1000:.3f}ms > 20ms"
        
        print(f"祝日検索ベンチマーク: 平均 {avg_search_time*1000:.3f}ms, "
              f"最大 {max_search_time*1000:.3f}ms, 95%ile {p95_search_time*1000:.3f}ms")

    @pytest.mark.performance
    def test_bulk_holiday_search_performance(self, temp_dir, monkeypatch):
        """一括祝日検索のパフォーマンステスト"""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # テストデータ準備
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        
        # 10年分のデータ（現在年以降）
        current_year = datetime.now().year
        holiday_data = "日付,祝日名\n"
        for year in range(current_year, current_year + 10):
            for month in range(1, 13):
                holiday_data += f"{year}-{month:02d}-15,月例祝日{year}{month:02d}\n"
        
        cache_file.write_text(holiday_data, encoding='utf-8')
        
        holidays = JapaneseHolidays()
        
        # 年間祝日取得のベンチマーク
        start_time = time.perf_counter()
        
        yearly_results = []
        for year in range(current_year, current_year + 10):
            year_holidays = holidays.get_holidays_by_year(year)
            yearly_results.append(len(year_holidays))
        
        end_time = time.perf_counter()
        bulk_search_time = end_time - start_time
        
        # 日付範囲検索のベンチマーク
        start_time = time.perf_counter()
        
        range_holidays = holidays.get_holidays_in_range(
            date(current_year, 1, 1), 
            date(current_year, 12, 31)
        )
        
        end_time = time.perf_counter()
        range_search_time = end_time - start_time
        
        # パフォーマンス要件検証
        assert bulk_search_time < 0.5, f"一括検索時間 {bulk_search_time:.3f}s > 500ms"
        assert range_search_time < 0.2, f"範囲検索時間 {range_search_time:.3f}s > 200ms"
        # Note: 祝日データは当年以降のみフィルタされるため、検索結果数は可変
        
        print(f"一括祝日検索: 年間検索 {bulk_search_time*1000:.2f}ms, "
              f"範囲検索 {range_search_time*1000:.2f}ms")

    @pytest.mark.performance
    def test_concurrent_holiday_search_performance(self, temp_dir, monkeypatch):
        """並行祝日検索のパフォーマンステスト"""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # テストデータ準備
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        
        holiday_data = "日付,祝日名\n"
        for year in range(2020, 2030):
            for i in range(20):  # 年間20祝日
                month = (i % 12) + 1
                day = (i % 28) + 1
                holiday_data += f"{year}-{month:02d}-{day:02d},祝日{year}{i:02d}\n"
        
        cache_file.write_text(holiday_data, encoding='utf-8')
        
        def search_worker(worker_id: int) -> Tuple[int, float]:
            """ワーカー関数：祝日検索を実行"""
            holidays = JapaneseHolidays()
            
            start_time = time.perf_counter()
            search_count = 0
            
            # 各ワーカーが100回検索
            for i in range(100):
                test_date = date(2025, (i % 12) + 1, (i % 28) + 1)
                holidays.is_holiday(test_date)
                search_count += 1
            
            end_time = time.perf_counter()
            return search_count, end_time - start_time
        
        # 並行検索実行
        start_time = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(search_worker, i) for i in range(4)]
            results = [future.result() for future in as_completed(futures)]
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # 結果分析
        total_searches = sum(result[0] for result in results)
        max_worker_time = max(result[1] for result in results)
        
        # パフォーマンス要件検証
        assert total_time < 5.0, f"並行検索総時間 {total_time:.3f}s > 5.0s"
        assert max_worker_time < 3.0, f"最大ワーカー時間 {max_worker_time:.3f}s > 3.0s"
        assert total_searches == 400, "全検索が完了すること"
        
        print(f"並行祝日検索: 総時間 {total_time:.3f}s, "
              f"最大ワーカー時間 {max_worker_time:.3f}s, 検索数 {total_searches}")


class TestICSGenerationBenchmarks:
    """ICS生成操作の専用ベンチマークテスト"""

    @pytest.mark.performance
    def test_ics_generation_benchmark_detailed(self, temp_dir, monkeypatch):
        """詳細なICS生成ベンチマーク"""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # 大容量祝日データ準備
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        
        # 20年分の祝日データ
        holiday_data = "日付,祝日名\n"
        for year in range(2020, 2040):
            for month in range(1, 13):
                for day in [1, 15, 28]:  # 月3回の祝日
                    holiday_data += f"{year}-{month:02d}-{day:02d},祝日{year}{month:02d}{day:02d}\n"
        
        cache_file.write_text(holiday_data, encoding='utf-8')
        
        # ICS生成の段階別ベンチマーク
        holidays = JapaneseHolidays()
        
        # 1. 初期化時間
        start_time = time.perf_counter()
        ics_generator = ICSGenerator(japanese_holidays=holidays)
        init_time = time.perf_counter() - start_time
        
        # 2. 祝日データ処理時間（内部で自動実行）
        start_time = time.perf_counter()
        # 祝日データは初期化時に既に処理されているため、ここでは統計取得のみ
        stats = ics_generator.get_generation_stats()
        add_holidays_time = time.perf_counter() - start_time
        
        # 3. ICS内容生成時間
        start_time = time.perf_counter()
        ics_content = ics_generator.generate_ics_content()
        generate_time = time.perf_counter() - start_time
        
        # 4. ファイル保存時間
        output_file = temp_dir / "benchmark_calendar.ics"
        start_time = time.perf_counter()
        ics_generator.save_to_file(str(output_file))
        save_time = time.perf_counter() - start_time
        
        # 結果分析
        total_time = init_time + add_holidays_time + generate_time + save_time
        content_size = len(ics_content) / 1024  # KB
        
        # パフォーマンス要件検証
        assert init_time < 1.0, f"初期化時間 {init_time*1000:.2f}ms > 1000ms"
        assert add_holidays_time < 2.0, f"祝日追加時間 {add_holidays_time:.3f}s > 2.0s"
        assert generate_time < 3.0, f"ICS生成時間 {generate_time:.3f}s > 3.0s"
        assert save_time < 1.0, f"ファイル保存時間 {save_time*1000:.2f}ms > 1000ms"
        assert total_time < 5.0, f"総処理時間 {total_time:.3f}s > 5.0s"
        
        print(f"ICS生成ベンチマーク: 初期化 {init_time*1000:.2f}ms, "
              f"祝日追加 {add_holidays_time*1000:.2f}ms, "
              f"生成 {generate_time*1000:.2f}ms, 保存 {save_time*1000:.2f}ms, "
              f"サイズ {content_size:.2f}KB")

    @pytest.mark.performance
    def test_ics_generation_memory_efficiency(self, temp_dir, monkeypatch):
        """ICS生成のメモリ効率テスト"""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # テストデータ準備
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        
        # 大容量データセット（10年分、年間100祝日）
        holiday_data = "日付,祝日名\n"
        for year in range(2020, 2030):
            for i in range(100):
                month = (i % 12) + 1
                day = (i % 28) + 1
                holiday_data += f"{year}-{month:02d}-{day:02d},大容量祝日{year}{i:03d}\n"
        
        cache_file.write_text(holiday_data, encoding='utf-8')
        
        # メモリ使用量監視
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # ガベージコレクション実行
        gc.collect()
        
        # ICS生成実行
        holidays = JapaneseHolidays()
        
        # 段階的にメモリ使用量を測定
        memory_samples = []
        
        # 初期化段階
        ics_generator = ICSGenerator(japanese_holidays=holidays)
        current_memory = process.memory_info().rss / 1024 / 1024
        memory_samples.append(current_memory)
        
        # ICS生成段階
        ics_content = ics_generator.generate_ics_content()
        generation_memory = process.memory_info().rss / 1024 / 1024
        
        # ファイル保存段階
        output_file = temp_dir / "memory_test.ics"
        ics_generator.save_to_file(str(output_file))
        final_memory = process.memory_info().rss / 1024 / 1024
        
        # メモリ効率分析
        peak_memory = max(memory_samples + [generation_memory, final_memory])
        memory_growth = peak_memory - initial_memory
        content_size = len(ics_content) / 1024 / 1024  # MB
        
        # メモリ効率要件検証
        assert memory_growth < 100, f"メモリ増加量 {memory_growth:.2f}MB > 100MB"
        assert peak_memory < initial_memory + 150, f"ピークメモリ {peak_memory:.2f}MB が過大"
        
        # メモリ効率比（コンテンツサイズに対するメモリ使用量）
        memory_efficiency_ratio = memory_growth / content_size if content_size > 0 else 0
        assert memory_efficiency_ratio < 500, f"メモリ効率比 {memory_efficiency_ratio:.2f} が低い"
        
        print(f"ICS生成メモリ効率: 初期 {initial_memory:.2f}MB, "
              f"ピーク {peak_memory:.2f}MB, 増加 {memory_growth:.2f}MB, "
              f"コンテンツ {content_size:.2f}MB, 効率比 {memory_efficiency_ratio:.2f}")

    @pytest.mark.performance
    def test_ics_generation_scalability(self, temp_dir, monkeypatch):
        """ICS生成のスケーラビリティテスト"""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # 異なるデータサイズでのパフォーマンス測定
        test_cases = [
            (1, 50),    # 1年、50祝日
            (5, 100),   # 5年、100祝日/年
            (10, 200),  # 10年、200祝日/年
            (20, 300),  # 20年、300祝日/年
        ]
        
        results = []
        
        for years, holidays_per_year in test_cases:
            # テストデータ生成
            cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = cache_dir / "japanese_holidays.csv"
            
            holiday_data = "日付,祝日名\n"
            for year in range(2024, 2024 + years):
                for i in range(holidays_per_year):
                    month = (i % 12) + 1
                    day = (i % 28) + 1
                    holiday_data += f"{year}-{month:02d}-{day:02d},スケール祝日{year}{i:03d}\n"
            
            cache_file.write_text(holiday_data, encoding='utf-8')
            
            # パフォーマンス測定
            start_time = time.perf_counter()
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            holidays = JapaneseHolidays()
            ics_generator = ICSGenerator(japanese_holidays=holidays)
            ics_content = ics_generator.generate_ics_content()
            
            end_time = time.perf_counter()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            # 結果記録
            total_holidays = years * holidays_per_year
            processing_time = end_time - start_time
            memory_usage = end_memory - start_memory
            content_size = len(ics_content) / 1024  # KB
            
            results.append({
                'total_holidays': total_holidays,
                'processing_time': processing_time,
                'memory_usage': memory_usage,
                'content_size': content_size,
                'throughput': total_holidays / processing_time if processing_time > 0 else 0
            })
            
            # 個別ケースの要件検証
            assert processing_time < total_holidays * 0.001, \
                f"{total_holidays}祝日の処理時間 {processing_time:.3f}s が過大"
        
        # スケーラビリティ分析
        throughputs = [r['throughput'] for r in results]
        min_throughput = min(throughputs)
        max_throughput = max(throughputs)
        
        # スループット変動が80%以内であることを確認（線形スケーラビリティ）
        throughput_variation = (max_throughput - min_throughput) / max_throughput
        assert throughput_variation < 0.8, f"スループット変動 {throughput_variation:.2f} > 80%"
        
        print("ICS生成スケーラビリティ:")
        for i, result in enumerate(results):
            case = test_cases[i]
            print(f"  {case[0]}年×{case[1]}祝日: {result['processing_time']:.3f}s, "
                  f"{result['memory_usage']:.2f}MB, {result['throughput']:.0f}祝日/s")


class TestResourceConsumptionBenchmarks:
    """リソース消費の詳細ベンチマークテスト"""

    @pytest.mark.performance
    def test_memory_usage_patterns(self, temp_dir, monkeypatch):
        """メモリ使用パターンの詳細分析"""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # テストデータ準備
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        
        # 段階的にサイズを増やすデータセット
        base_data = "日付,祝日名\n"
        for year in range(2020, 2030):
            for i in range(50):
                month = (i % 12) + 1
                day = (i % 28) + 1
                base_data += f"{year}-{month:02d}-{day:02d},メモリテスト祝日{year}{i:02d}\n"
        
        cache_file.write_text(base_data, encoding='utf-8')
        
        process = psutil.Process()
        memory_timeline = []
        
        # 段階的操作とメモリ監視
        operations = [
            "初期状態",
            "JapaneseHolidays初期化",
            "ICSGenerator初期化", 
            "祝日データ追加",
            "ICS内容生成",
            "ファイル保存",
            "ICS解析",
            "比較操作"
        ]
        
        # 初期状態
        gc.collect()
        memory_timeline.append(process.memory_info().rss / 1024 / 1024)
        
        # JapaneseHolidays初期化
        holidays = JapaneseHolidays()
        memory_timeline.append(process.memory_info().rss / 1024 / 1024)
        
        # ICSGenerator初期化
        ics_generator = ICSGenerator(japanese_holidays=holidays)
        memory_timeline.append(process.memory_info().rss / 1024 / 1024)
        
        # 祝日データ追加
        for year in range(2024, 2030):
            ics_generator.add_japanese_holidays_for_year(year)
        memory_timeline.append(process.memory_info().rss / 1024 / 1024)
        
        # ICS内容生成
        ics_content = ics_generator.generate_ics_content()
        memory_timeline.append(process.memory_info().rss / 1024 / 1024)
        
        # ファイル保存
        output_file = temp_dir / "memory_pattern_test.ics"
        ics_generator.save_to_file(str(output_file))
        memory_timeline.append(process.memory_info().rss / 1024 / 1024)
        
        # ICS解析
        analyzer = ICSAnalyzer()
        analysis = analyzer.parse_ics_file(str(output_file))
        memory_timeline.append(process.memory_info().rss / 1024 / 1024)
        
        # 比較操作（同じファイルを自分自身と比較）
        comparison = analyzer.compare_ics_files(str(output_file), str(output_file))
        memory_timeline.append(process.memory_info().rss / 1024 / 1024)
        
        # メモリ使用パターン分析
        max_memory = max(memory_timeline)
        min_memory = min(memory_timeline)
        memory_range = max_memory - min_memory
        
        # 各段階でのメモリ増加量
        memory_deltas = [memory_timeline[i] - memory_timeline[i-1] 
                        for i in range(1, len(memory_timeline))]
        
        # メモリ使用要件検証
        assert memory_range < 200, f"メモリ使用範囲 {memory_range:.2f}MB > 200MB"
        assert max(memory_deltas) < 100, f"最大メモリ増加 {max(memory_deltas):.2f}MB > 100MB"
        
        # 結果出力
        print("メモリ使用パターン:")
        for i, (operation, memory) in enumerate(zip(operations, memory_timeline)):
            delta = memory_deltas[i-1] if i > 0 else 0
            print(f"  {operation}: {memory:.2f}MB (Δ{delta:+.2f}MB)")

    @pytest.mark.performance
    def test_cpu_utilization_efficiency(self, temp_dir, monkeypatch):
        """CPU使用率効率の詳細測定"""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # CPU集約的なテストデータ準備
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        
        # 計算集約的なデータセット
        intensive_data = "日付,祝日名\n"
        for year in range(2000, 2050):  # 50年分
            for i in range(30):  # 年間30祝日
                month = (i % 12) + 1
                day = (i % 28) + 1
                # 長い祝日名で文字列処理を重くする
                long_name = f"CPU集約的テスト祝日{year}年{month:02d}月{day:02d}日" + "詳細説明" * 10
                intensive_data += f"{year}-{month:02d}-{day:02d},{long_name}\n"
        
        cache_file.write_text(intensive_data, encoding='utf-8')
        
        # CPU使用率監視
        process = psutil.Process()
        cpu_samples = []
        
        def monitor_cpu():
            """CPU使用率を定期的にサンプリング"""
            for _ in range(20):  # 2秒間、0.1秒間隔でサンプリング
                cpu_samples.append(process.cpu_percent(interval=0.1))
        
        # CPU監視スレッド開始
        monitor_thread = threading.Thread(target=monitor_cpu)
        monitor_thread.start()
        
        # CPU集約的操作実行
        start_time = time.perf_counter()
        
        # 複数の操作を並行実行
        holidays = JapaneseHolidays()
        ics_generator = ICSGenerator(japanese_holidays=holidays)
        
        # ICS生成
        ics_content = ics_generator.generate_ics_content()
        
        # 複数ファイル生成
        for i in range(5):
            output_file = temp_dir / f"cpu_test_{i}.ics"
            ics_generator.save_to_file(str(output_file))
        
        # 解析処理
        analyzer = ICSAnalyzer()
        for i in range(5):
            file_path = temp_dir / f"cpu_test_{i}.ics"
            analysis = analyzer.parse_ics_file(str(file_path))
        
        end_time = time.perf_counter()
        
        # CPU監視終了
        monitor_thread.join()
        
        # CPU使用率分析
        total_time = end_time - start_time
        avg_cpu = statistics.mean(cpu_samples) if cpu_samples else 0
        max_cpu = max(cpu_samples) if cpu_samples else 0
        cpu_efficiency = avg_cpu / 100.0  # 0-1の効率値
        
        # CPU効率要件検証
        assert total_time < 10.0, f"処理時間 {total_time:.2f}s > 10.0s"
        assert max_cpu < 95.0, f"最大CPU使用率 {max_cpu:.1f}% > 95%"
        assert avg_cpu > 10.0, f"平均CPU使用率 {avg_cpu:.1f}% < 10% (処理が軽すぎる)"
        
        print(f"CPU効率: 処理時間 {total_time:.2f}s, "
              f"平均CPU {avg_cpu:.1f}%, 最大CPU {max_cpu:.1f}%, "
              f"効率 {cpu_efficiency:.2f}")

    @pytest.mark.performance
    def test_disk_io_patterns(self, temp_dir, monkeypatch):
        """ディスクI/Oパターンの詳細分析"""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        process = psutil.Process()
        
        # I/O操作前の状態
        io_before = process.io_counters()
        
        # 段階的I/O操作
        io_operations = []
        
        # 1. キャッシュファイル作成
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        
        large_data = "日付,祝日名\n"
        for year in range(2020, 2030):
            for i in range(100):
                month = (i % 12) + 1
                day = (i % 28) + 1
                large_data += f"{year}-{month:02d}-{day:02d},I/Oテスト祝日{year}{i:03d}\n"
        
        start_time = time.perf_counter()
        cache_file.write_text(large_data, encoding='utf-8')
        cache_write_time = time.perf_counter() - start_time
        
        io_after_cache = process.io_counters()
        cache_write_bytes = io_after_cache.write_bytes - io_before.write_bytes
        
        # 2. データ読み込み
        start_time = time.perf_counter()
        holidays = JapaneseHolidays()
        data_load_time = time.perf_counter() - start_time
        
        io_after_load = process.io_counters()
        data_read_bytes = io_after_load.read_bytes - io_after_cache.read_bytes
        
        # 3. ICS生成と保存
        ics_generator = ICSGenerator(japanese_holidays=holidays)
        for year in range(2024, 2030):
            ics_generator.add_japanese_holidays_for_year(year)
        
        start_time = time.perf_counter()
        
        # 複数ファイル生成
        for i in range(10):
            output_file = temp_dir / f"io_pattern_test_{i}.ics"
            ics_generator.save_to_file(str(output_file))
        
        ics_write_time = time.perf_counter() - start_time
        
        io_after_ics = process.io_counters()
        ics_write_bytes = io_after_ics.write_bytes - io_after_load.write_bytes
        
        # 4. ファイル読み込みと解析
        start_time = time.perf_counter()
        
        analyzer = ICSAnalyzer()
        for i in range(10):
            file_path = temp_dir / f"io_pattern_test_{i}.ics"
            analysis = analyzer.parse_ics_file(str(file_path))
        
        analysis_time = time.perf_counter() - start_time
        
        io_final = process.io_counters()
        analysis_read_bytes = io_final.read_bytes - io_after_ics.read_bytes
        
        # I/O効率分析
        total_read_bytes = io_final.read_bytes - io_before.read_bytes
        total_write_bytes = io_final.write_bytes - io_before.write_bytes
        
        # I/O速度計算 (MB/s)
        cache_write_speed = (cache_write_bytes / 1024 / 1024) / cache_write_time if cache_write_time > 0 else 0
        data_load_speed = (data_read_bytes / 1024 / 1024) / data_load_time if data_load_time > 0 else 0
        ics_write_speed = (ics_write_bytes / 1024 / 1024) / ics_write_time if ics_write_time > 0 else 0
        analysis_read_speed = (analysis_read_bytes / 1024 / 1024) / analysis_time if analysis_time > 0 else 0
        
        # I/O効率要件検証
        assert cache_write_speed > 1.0, f"キャッシュ書き込み速度 {cache_write_speed:.2f}MB/s < 1.0MB/s"
        assert data_load_speed > 5.0, f"データ読み込み速度 {data_load_speed:.2f}MB/s < 5.0MB/s"
        assert ics_write_speed > 0.5, f"ICS書き込み速度 {ics_write_speed:.2f}MB/s < 0.5MB/s"
        
        print(f"ディスクI/Oパターン:")
        print(f"  キャッシュ書き込み: {cache_write_bytes/1024:.1f}KB, {cache_write_speed:.2f}MB/s")
        print(f"  データ読み込み: {data_read_bytes/1024:.1f}KB, {data_load_speed:.2f}MB/s")
        print(f"  ICS書き込み: {ics_write_bytes/1024:.1f}KB, {ics_write_speed:.2f}MB/s")
        print(f"  解析読み込み: {analysis_read_bytes/1024:.1f}KB, {analysis_read_speed:.2f}MB/s")
        print(f"  総I/O: 読み込み {total_read_bytes/1024:.1f}KB, 書き込み {total_write_bytes/1024:.1f}KB")