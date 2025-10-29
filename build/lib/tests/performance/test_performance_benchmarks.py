"""
Performance benchmarks and tests.
Tests performance characteristics of core functionality.
"""

import pytest
import time
import psutil
import os
from unittest.mock import patch, Mock
from datetime import date, datetime
import tempfile
from pathlib import Path

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
        cache_dir.mkdir(parents=True)
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
        cache_dir.mkdir(parents=True)
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
        cache_dir.mkdir(parents=True)
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
        cache_dir.mkdir(parents=True)
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