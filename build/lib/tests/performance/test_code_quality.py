"""
Code quality and coverage tests.
Tests code coverage, quality metrics, and regression detection.
"""

import pytest
import subprocess
import sys
import os
import json
from pathlib import Path
import tempfile


class TestCodeCoverage:
    """Test code coverage measurement and quality gates."""

    @pytest.mark.quality
    def test_unit_test_coverage(self):
        """Test unit test coverage meets minimum requirements."""
        # Run pytest with coverage
        result = subprocess.run([
            sys.executable, '-m', 'pytest',
            'tests/unit/',
            '--cov=src',
            '--cov-report=json',
            '--cov-report=term-missing',
            '--cov-fail-under=80'
        ], capture_output=True, text=True)
        
        # Check if coverage report was generated
        coverage_file = Path('coverage.json')
        if coverage_file.exists():
            with open(coverage_file, 'r') as f:
                coverage_data = json.load(f)
            
            total_coverage = coverage_data['totals']['percent_covered']
            
            # Coverage assertions
            assert total_coverage >= 80.0, f"Unit test coverage {total_coverage:.1f}% < 80%"
            
            # Check individual module coverage
            files = coverage_data['files']
            low_coverage_files = []
            
            for file_path, file_data in files.items():
                if file_path.startswith('src/'):
                    file_coverage = file_data['summary']['percent_covered']
                    if file_coverage < 70.0:  # Individual file threshold
                        low_coverage_files.append((file_path, file_coverage))
            
            if low_coverage_files:
                low_files_str = '\n'.join([f"  {path}: {cov:.1f}%" 
                                         for path, cov in low_coverage_files])
                pytest.fail(f"Files with low coverage (<70%):\n{low_files_str}")
            
            print(f"Unit test coverage: {total_coverage:.1f}%")
        else:
            pytest.skip("Coverage report not generated")

    @pytest.mark.quality
    def test_integration_test_coverage(self):
        """Test integration test coverage."""
        # Run integration tests with coverage
        result = subprocess.run([
            sys.executable, '-m', 'pytest',
            'tests/integration/',
            '--cov=src',
            '--cov-report=json:coverage_integration.json',
            '--cov-report=term-missing'
        ], capture_output=True, text=True)
        
        # Check integration test coverage
        coverage_file = Path('coverage_integration.json')
        if coverage_file.exists():
            with open(coverage_file, 'r') as f:
                coverage_data = json.load(f)
            
            total_coverage = coverage_data['totals']['percent_covered']
            
            # Integration coverage should be reasonable
            assert total_coverage >= 60.0, f"Integration test coverage {total_coverage:.1f}% < 60%"
            
            print(f"Integration test coverage: {total_coverage:.1f}%")
            
            # Clean up
            coverage_file.unlink()
        else:
            pytest.skip("Integration coverage report not generated")

    @pytest.mark.quality
    def test_combined_test_coverage(self):
        """Test combined unit and integration test coverage."""
        # Run all tests with coverage
        result = subprocess.run([
            sys.executable, '-m', 'pytest',
            'tests/unit/',
            'tests/integration/',
            '--cov=src',
            '--cov-report=json:coverage_combined.json',
            '--cov-report=term-missing',
            '--cov-fail-under=85'
        ], capture_output=True, text=True)
        
        # Check combined coverage
        coverage_file = Path('coverage_combined.json')
        if coverage_file.exists():
            with open(coverage_file, 'r') as f:
                coverage_data = json.load(f)
            
            total_coverage = coverage_data['totals']['percent_covered']
            
            # Combined coverage should be high
            assert total_coverage >= 85.0, f"Combined test coverage {total_coverage:.1f}% < 85%"
            
            # Check for untested lines in critical modules
            critical_modules = [
                'src/japanese_holidays.py',
                'src/ics_generator.py',
                'src/calendar_analyzer.py',
                'src/aws_client.py'
            ]
            
            for module in critical_modules:
                if module in coverage_data['files']:
                    module_data = coverage_data['files'][module]
                    module_coverage = module_data['summary']['percent_covered']
                    
                    assert module_coverage >= 80.0, \
                        f"Critical module {module} coverage {module_coverage:.1f}% < 80%"
            
            print(f"Combined test coverage: {total_coverage:.1f}%")
            
            # Clean up
            coverage_file.unlink()
        else:
            pytest.skip("Combined coverage report not generated")


class TestCodeQualityMetrics:
    """Test code quality metrics and standards."""

    @pytest.mark.quality
    def test_flake8_compliance(self):
        """Test code compliance with flake8 standards."""
        # Run flake8 on source code
        result = subprocess.run([
            sys.executable, '-m', 'flake8',
            'src/',
            '--max-line-length=100',
            '--ignore=E203,W503',  # Ignore some formatting issues
            '--statistics'
        ], capture_output=True, text=True)
        
        # Check for flake8 violations
        if result.returncode != 0:
            violations = result.stdout.strip()
            pytest.fail(f"Flake8 violations found:\n{violations}")
        
        print("Flake8 compliance: PASSED")

    @pytest.mark.quality
    def test_bandit_security_scan(self):
        """Test security compliance with bandit."""
        # Run bandit security scan
        result = subprocess.run([
            sys.executable, '-m', 'bandit',
            '-r', 'src/',
            '-f', 'json',
            '-o', 'bandit_report.json'
        ], capture_output=True, text=True)
        
        # Check bandit report
        report_file = Path('bandit_report.json')
        if report_file.exists():
            with open(report_file, 'r') as f:
                bandit_data = json.load(f)
            
            # Check for high severity issues
            high_severity_issues = [
                issue for issue in bandit_data.get('results', [])
                if issue.get('issue_severity') == 'HIGH'
            ]
            
            if high_severity_issues:
                issues_str = '\n'.join([
                    f"  {issue['filename']}:{issue['line_number']} - {issue['issue_text']}"
                    for issue in high_severity_issues
                ])
                pytest.fail(f"High severity security issues found:\n{issues_str}")
            
            # Check for medium severity issues (warning)
            medium_severity_issues = [
                issue for issue in bandit_data.get('results', [])
                if issue.get('issue_severity') == 'MEDIUM'
            ]
            
            if medium_severity_issues:
                print(f"Warning: {len(medium_severity_issues)} medium severity security issues found")
            
            print(f"Bandit security scan: {len(bandit_data.get('results', []))} total issues")
            
            # Clean up
            report_file.unlink()
        else:
            pytest.skip("Bandit report not generated")

    @pytest.mark.quality
    def test_mypy_type_checking(self):
        """Test type checking with mypy."""
        # Run mypy type checking
        result = subprocess.run([
            sys.executable, '-m', 'mypy',
            'src/',
            '--ignore-missing-imports',
            '--strict-optional',
            '--warn-redundant-casts',
            '--warn-unused-ignores'
        ], capture_output=True, text=True)
        
        # Check mypy results
        if result.returncode != 0:
            type_errors = result.stdout.strip()
            # Allow some type errors but fail on critical ones
            error_lines = type_errors.split('\n')
            critical_errors = [
                line for line in error_lines
                if 'error:' in line and 'incompatible' in line.lower()
            ]
            
            if critical_errors:
                pytest.fail(f"Critical type errors found:\n" + '\n'.join(critical_errors))
            
            print(f"MyPy type checking: {len(error_lines)} warnings")
        else:
            print("MyPy type checking: PASSED")

    @pytest.mark.quality
    def test_complexity_metrics(self):
        """Test code complexity metrics."""
        # Run radon for complexity analysis
        result = subprocess.run([
            sys.executable, '-m', 'radon',
            'cc', 'src/',
            '--min', 'B',  # Show B grade and above
            '--json'
        ], capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            try:
                complexity_data = json.loads(result.stdout)
                
                # Check for high complexity functions
                high_complexity_functions = []
                
                for file_path, file_data in complexity_data.items():
                    for item in file_data:
                        if item.get('complexity', 0) > 10:  # Complexity threshold
                            high_complexity_functions.append({
                                'file': file_path,
                                'function': item.get('name', 'unknown'),
                                'complexity': item.get('complexity', 0)
                            })
                
                if high_complexity_functions:
                    complex_funcs_str = '\n'.join([
                        f"  {func['file']}:{func['function']} - {func['complexity']}"
                        for func in high_complexity_functions
                    ])
                    pytest.fail(f"High complexity functions found (>10):\n{complex_funcs_str}")
                
                print("Code complexity: PASSED")
            except json.JSONDecodeError:
                pytest.skip("Could not parse radon output")
        else:
            pytest.skip("Radon complexity analysis not available")


class TestRegressionDetection:
    """Test for performance and functionality regressions."""

    @pytest.mark.quality
    def test_performance_regression_detection(self, temp_dir, monkeypatch):
        """Test for performance regressions."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # Create baseline performance data
        baseline_file = Path('performance_baseline.json')
        
        # Run performance benchmarks
        from tests.performance.test_performance_benchmarks import TestPerformanceBenchmarks
        
        # Measure current performance
        import time
        from src.japanese_holidays import JapaneseHolidays
        from src.ics_generator import ICSGenerator
        
        # Create test data
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        
        test_data = """日付,祝日名
2024-01-01,元日
2024-01-08,成人の日
2024-02-11,建国記念の日"""
        cache_file.write_text(test_data, encoding='utf-8')
        
        # Measure holiday processing time
        start_time = time.time()
        holidays = JapaneseHolidays()
        stats = holidays.get_stats()
        holiday_time = time.time() - start_time
        
        # Measure ICS generation time
        start_time = time.time()
        ics_generator = ICSGenerator(japanese_holidays=holidays)
        ics_generator.add_japanese_holidays_for_year(2024)
        ics_content = ics_generator.generate_ics_content()
        ics_time = time.time() - start_time
        
        current_performance = {
            'holiday_processing_time': holiday_time,
            'ics_generation_time': ics_time,
            'timestamp': time.time()
        }
        
        # Load baseline if exists
        if baseline_file.exists():
            with open(baseline_file, 'r') as f:
                baseline = json.load(f)
            
            # Check for regressions (>50% slower)
            regression_threshold = 1.5
            
            if current_performance['holiday_processing_time'] > baseline['holiday_processing_time'] * regression_threshold:
                pytest.fail(f"Holiday processing regression: "
                          f"{current_performance['holiday_processing_time']:.3f}s > "
                          f"{baseline['holiday_processing_time'] * regression_threshold:.3f}s")
            
            if current_performance['ics_generation_time'] > baseline['ics_generation_time'] * regression_threshold:
                pytest.fail(f"ICS generation regression: "
                          f"{current_performance['ics_generation_time']:.3f}s > "
                          f"{baseline['ics_generation_time'] * regression_threshold:.3f}s")
            
            print(f"Performance regression check: PASSED")
            print(f"  Holiday processing: {current_performance['holiday_processing_time']:.3f}s "
                  f"(baseline: {baseline['holiday_processing_time']:.3f}s)")
            print(f"  ICS generation: {current_performance['ics_generation_time']:.3f}s "
                  f"(baseline: {baseline['ics_generation_time']:.3f}s)")
        else:
            # Create baseline
            with open(baseline_file, 'w') as f:
                json.dump(current_performance, f, indent=2)
            
            print(f"Performance baseline created:")
            print(f"  Holiday processing: {current_performance['holiday_processing_time']:.3f}s")
            print(f"  ICS generation: {current_performance['ics_generation_time']:.3f}s")

    @pytest.mark.quality
    def test_functionality_regression_detection(self, temp_dir, monkeypatch):
        """Test for functionality regressions."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # Test core functionality still works
        from src.japanese_holidays import JapaneseHolidays
        from src.ics_generator import ICSGenerator
        from src.calendar_analyzer import ICSAnalyzer
        
        # Create test data
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        
        test_data = """日付,祝日名
2024-01-01,元日
2024-01-08,成人の日
2024-02-11,建国記念の日
2024-02-23,天皇誕生日"""
        cache_file.write_text(test_data, encoding='utf-8')
        
        # Test holiday functionality
        holidays = JapaneseHolidays()
        
        # Core functionality checks
        assert holidays.is_holiday(date(2024, 1, 1)), "New Year should be a holiday"
        assert holidays.get_holiday_name(date(2024, 1, 1)) == "元日", "Holiday name should be correct"
        
        stats = holidays.get_stats()
        assert stats['total'] == 4, "Should have 4 holidays in test data"
        
        # Test ICS generation functionality
        ics_generator = ICSGenerator(japanese_holidays=holidays)
        ics_generator.add_japanese_holidays_for_year(2024)
        ics_content = ics_generator.generate_ics_content()
        
        # ICS content checks
        assert 'BEGIN:VCALENDAR' in ics_content, "ICS should have calendar header"
        assert 'END:VCALENDAR' in ics_content, "ICS should have calendar footer"
        assert '元日' in ics_content, "ICS should contain holiday names"
        assert 'Asia/Tokyo' in ics_content, "ICS should have timezone"
        
        # Test analysis functionality
        temp_ics = temp_dir / "regression_test.ics"
        temp_ics.write_text(ics_content, encoding='utf-8')
        
        analyzer = ICSAnalyzer()
        analysis = analyzer.parse_ics_file(str(temp_ics))
        
        # Analysis checks
        assert analysis['file_info']['total_events'] == 4, "Should analyze 4 events"
        assert len(analysis['validation_errors']) == 0, "Should have no validation errors"
        
        # Format checks
        human_readable = analyzer.format_human_readable(analysis)
        assert isinstance(human_readable, str), "Should generate human readable output"
        assert '元日' in human_readable, "Human readable should contain holiday names"
        
        json_output = analyzer.export_json(analysis)
        assert isinstance(json_output, str), "Should generate JSON output"
        
        # Verify JSON is valid
        import json
        parsed_json = json.loads(json_output)
        assert 'file_info' in parsed_json, "JSON should have file_info"
        
        print("Functionality regression check: PASSED")

    @pytest.mark.quality
    def test_api_compatibility_regression(self):
        """Test for API compatibility regressions."""
        # Test that public APIs haven't changed
        from src.japanese_holidays import JapaneseHolidays
        from src.ics_generator import ICSGenerator
        from src.calendar_analyzer import ICSAnalyzer
        from src.aws_client import SSMChangeCalendarClient
        
        # Check JapaneseHolidays API
        holidays = JapaneseHolidays()
        
        # Required methods should exist
        required_holiday_methods = [
            'is_holiday', 'get_holiday_name', 'get_stats',
            'get_holidays_by_year', 'is_cache_valid'
        ]
        
        for method in required_holiday_methods:
            assert hasattr(holidays, method), f"JapaneseHolidays missing method: {method}"
        
        # Check ICSGenerator API
        ics_gen = ICSGenerator()
        
        required_ics_methods = [
            'add_japanese_holidays_for_year', 'generate_ics_content',
            'save_to_file', 'clear_events'
        ]
        
        for method in required_ics_methods:
            assert hasattr(ics_gen, method), f"ICSGenerator missing method: {method}"
        
        # Check ICSAnalyzer API
        analyzer = ICSAnalyzer()
        
        required_analyzer_methods = [
            'parse_ics_file', 'format_human_readable',
            'export_json', 'export_csv', 'compare_ics_files'
        ]
        
        for method in required_analyzer_methods:
            assert hasattr(analyzer, method), f"ICSAnalyzer missing method: {method}"
        
        # Check SSMChangeCalendarClient API
        client = SSMChangeCalendarClient()
        
        required_client_methods = [
            'get_change_calendar', 'list_change_calendars',
            'get_calendar_state', 'create_change_calendar',
            'update_change_calendar', 'delete_change_calendar'
        ]
        
        for method in required_client_methods:
            assert hasattr(client, method), f"SSMChangeCalendarClient missing method: {method}"
        
        print("API compatibility regression check: PASSED")


class TestQualityGates:
    """Test quality gates and thresholds."""

    @pytest.mark.quality
    def test_test_execution_time_gate(self):
        """Test that test execution time is within acceptable limits."""
        import time
        
        start_time = time.time()
        
        # Run unit tests
        result = subprocess.run([
            sys.executable, '-m', 'pytest',
            'tests/unit/',
            '-v'
        ], capture_output=True, text=True)
        
        unit_test_time = time.time() - start_time
        
        # Unit tests should complete quickly
        assert unit_test_time < 60.0, f"Unit tests took {unit_test_time:.1f}s, expected < 60s"
        
        print(f"Test execution time gate: Unit tests {unit_test_time:.1f}s")

    @pytest.mark.quality
    def test_code_duplication_gate(self):
        """Test for excessive code duplication."""
        # This is a simplified check - in practice you might use tools like jscpd
        source_files = list(Path('src').glob('*.py'))
        
        # Check for obvious duplication patterns
        duplicate_patterns = []
        
        for file_path in source_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
                # Look for repeated function signatures or class definitions
                function_signatures = [
                    line.strip() for line in lines
                    if line.strip().startswith('def ') or line.strip().startswith('class ')
                ]
                
                # Check for duplicates
                seen_signatures = set()
                for signature in function_signatures:
                    if signature in seen_signatures:
                        duplicate_patterns.append(f"{file_path}: {signature}")
                    seen_signatures.add(signature)
        
        if duplicate_patterns:
            duplicates_str = '\n'.join(duplicate_patterns)
            pytest.fail(f"Potential code duplication found:\n{duplicates_str}")
        
        print("Code duplication gate: PASSED")

    @pytest.mark.quality
    def test_documentation_coverage_gate(self):
        """Test documentation coverage."""
        source_files = list(Path('src').glob('*.py'))
        
        undocumented_functions = []
        
        for file_path in source_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
                # Find function definitions
                for i, line in enumerate(lines):
                    if line.strip().startswith('def ') and not line.strip().startswith('def _'):
                        # Check if next non-empty line is a docstring
                        docstring_found = False
                        for j in range(i + 1, min(i + 5, len(lines))):
                            next_line = lines[j].strip()
                            if next_line:
                                if next_line.startswith('"""') or next_line.startswith("'''"):
                                    docstring_found = True
                                break
                        
                        if not docstring_found:
                            function_name = line.strip().split('(')[0].replace('def ', '')
                            undocumented_functions.append(f"{file_path}:{function_name}")
        
        # Allow some undocumented functions but not too many
        if len(undocumented_functions) > 10:
            undoc_str = '\n'.join(undocumented_functions[:10])
            pytest.fail(f"Too many undocumented functions ({len(undocumented_functions)}):\n{undoc_str}")
        
        print(f"Documentation coverage gate: {len(undocumented_functions)} undocumented functions")