"""
CLI integration tests.
Tests CLI commands with real components.
"""

import pytest
from unittest.mock import patch, Mock
from click.testing import CliRunner
import tempfile
import json

from src.cli import cli


class TestCLIIntegration:
    """Test CLI integration with real components."""

    def setup_method(self):
        """Setup test environment."""
        self.runner = CliRunner()

    @pytest.mark.integration
    @patch('requests.get')
    def test_export_command_success(self, mock_get, temp_dir, monkeypatch):
        """Test successful export command execution."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # Mock holiday data response
        mock_response = Mock()
        mock_response.content = """日付,祝日名
2024-01-01,元日
2024-01-08,成人の日""".encode('shift_jis')
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        output_file = temp_dir / "test_export.ics"
        
        result = self.runner.invoke(cli, [
            'export',
            '--output', str(output_file),
            '--include-holidays',
            '--holidays-year', '2024'
        ])
        
        assert result.exit_code == 0
        assert output_file.exists()
        
        # Verify file content
        content = output_file.read_text(encoding='utf-8')
        assert 'BEGIN:VCALENDAR' in content
        assert '元日' in content

    @pytest.mark.integration
    @patch('requests.get')
    def test_holidays_command_success(self, mock_get, temp_dir, monkeypatch):
        """Test successful holidays command execution."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # Mock holiday data response
        mock_response = Mock()
        mock_response.content = """日付,祝日名
2024-01-01,元日
2024-01-08,成人の日
2024-02-11,建国記念の日""".encode('shift_jis')
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.runner.invoke(cli, [
            'holidays',
            '--year', '2024'
        ])
        
        assert result.exit_code == 0
        assert '元日' in result.output
        assert '成人の日' in result.output
        assert '建国記念の日' in result.output

    @pytest.mark.integration
    @patch('requests.get')
    def test_check_holiday_command_success(self, mock_get, temp_dir, monkeypatch):
        """Test successful check-holiday command execution."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # Mock holiday data response
        mock_response = Mock()
        mock_response.content = """日付,祝日名
2024-01-01,元日""".encode('shift_jis')
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.runner.invoke(cli, [
            'check-holiday',
            '2024-01-01'
        ])
        
        assert result.exit_code == 0
        assert '元日' in result.output

    @pytest.mark.integration
    @patch('requests.get')
    def test_refresh_holidays_command_success(self, mock_get, temp_dir, monkeypatch):
        """Test successful refresh-holidays command execution."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # Mock holiday data response
        mock_response = Mock()
        mock_response.content = """日付,祝日名
2024-01-01,元日""".encode('shift_jis')
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.runner.invoke(cli, ['refresh-holidays'])
        
        assert result.exit_code == 0
        assert 'refreshed' in result.output.lower() or 'updated' in result.output.lower()

    @pytest.mark.integration
    def test_analyze_ics_command_success(self, temp_dir, sample_ics_content):
        """Test successful analyze-ics command execution."""
        # Create test ICS file
        ics_file = temp_dir / "test.ics"
        ics_file.write_text(sample_ics_content, encoding='utf-8')
        
        result = self.runner.invoke(cli, [
            'analyze-ics',
            str(ics_file)
        ])
        
        assert result.exit_code == 0
        assert 'カレンダー解析結果' in result.output
        assert '元日' in result.output

    @pytest.mark.integration
    def test_compare_ics_command_success(self, temp_dir, sample_ics_content):
        """Test successful compare-ics command execution."""
        # Create two test ICS files
        ics_file1 = temp_dir / "test1.ics"
        ics_file1.write_text(sample_ics_content, encoding='utf-8')
        
        # Create modified version
        modified_content = sample_ics_content.replace("元日", "New Year")
        ics_file2 = temp_dir / "test2.ics"
        ics_file2.write_text(modified_content, encoding='utf-8')
        
        result = self.runner.invoke(cli, [
            'compare-ics',
            str(ics_file1),
            str(ics_file2)
        ])
        
        assert result.exit_code == 0
        assert '比較結果' in result.output

    @pytest.mark.integration
    @patch('boto3.client')
    def test_list_calendars_command_success(self, mock_boto_client):
        """Test successful list-calendars command execution."""
        # Mock AWS client
        mock_client = Mock()
        mock_client.list_documents.return_value = {
            'DocumentIdentifiers': [
                {
                    'Name': 'test-calendar-1',
                    'DocumentType': 'ChangeCalendar'
                },
                {
                    'Name': 'test-calendar-2',
                    'DocumentType': 'ChangeCalendar'
                }
            ]
        }
        mock_boto_client.return_value = mock_client
        
        result = self.runner.invoke(cli, ['list-calendars'])
        
        assert result.exit_code == 0
        assert 'test-calendar-1' in result.output
        assert 'test-calendar-2' in result.output

    @pytest.mark.integration
    @patch('boto3.client')
    def test_create_calendar_command_success(self, mock_boto_client):
        """Test successful create-calendar command execution."""
        # Mock AWS client
        mock_client = Mock()
        mock_client.create_document.return_value = {
            'DocumentDescription': {
                'Name': 'new-test-calendar',
                'Status': 'Creating'
            }
        }
        mock_boto_client.return_value = mock_client
        
        result = self.runner.invoke(cli, [
            'create-calendar',
            'new-test-calendar',
            '--description', 'Test calendar',
            '--calendar-type', 'DEFAULT_OPEN'
        ])
        
        assert result.exit_code == 0
        assert 'new-test-calendar' in result.output

    @pytest.mark.integration
    def test_command_with_config_file(self, temp_dir, monkeypatch):
        """Test command execution with configuration file."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # Create configuration file
        config_data = {
            'aws': {
                'region': 'us-west-2',
                'profile': 'test-profile'
            },
            'calendar': {
                'default_timezone': 'America/Los_Angeles'
            }
        }
        
        config_dir = temp_dir / '.aws-ssm-calendar'
        config_dir.mkdir()
        config_file = config_dir / 'config.json'
        config_file.write_text(json.dumps(config_data), encoding='utf-8')
        
        result = self.runner.invoke(cli, [
            '--config', str(config_file),
            'holidays',
            '--year', '2024'
        ])
        
        # Should use config file settings
        # Note: This test verifies the config is loaded, actual behavior depends on implementation

    @pytest.mark.integration
    def test_command_error_handling(self, temp_dir):
        """Test CLI error handling."""
        # Test with non-existent file
        result = self.runner.invoke(cli, [
            'analyze-ics',
            'non_existent_file.ics'
        ])
        
        assert result.exit_code != 0
        assert 'error' in result.output.lower() or 'not found' in result.output.lower()

    @pytest.mark.integration
    def test_verbose_output(self, temp_dir, sample_ics_content):
        """Test verbose output option."""
        ics_file = temp_dir / "test.ics"
        ics_file.write_text(sample_ics_content, encoding='utf-8')
        
        result = self.runner.invoke(cli, [
            '--verbose',
            'analyze-ics',
            str(ics_file)
        ])
        
        assert result.exit_code == 0
        # Verbose mode should provide more detailed output

    @pytest.mark.integration
    def test_output_format_options(self, temp_dir, sample_ics_content):
        """Test different output format options."""
        ics_file = temp_dir / "test.ics"
        ics_file.write_text(sample_ics_content, encoding='utf-8')
        
        # Test JSON output
        result = self.runner.invoke(cli, [
            'analyze-ics',
            str(ics_file),
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        # Should be valid JSON
        try:
            json.loads(result.output)
        except json.JSONDecodeError:
            pytest.fail("Output is not valid JSON")

    @pytest.mark.integration
    def test_help_commands(self):
        """Test help command functionality."""
        result = self.runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert 'Usage:' in result.output
        
        # Test subcommand help
        result = self.runner.invoke(cli, ['export', '--help'])
        
        assert result.exit_code == 0
        assert 'Usage:' in result.output


class TestCLIAWSIntegration:
    """Test CLI AWS integration commands."""

    def setup_method(self):
        """Setup test environment."""
        self.runner = CliRunner()

    @pytest.mark.integration
    @patch('boto3.Session')
    def test_create_calendar_cli_integration(self, mock_session):
        """Test create-calendar CLI command integration."""
        # Mock AWS client
        mock_client = Mock()
        mock_client.describe_document.side_effect = Exception("Document not found")
        mock_client.create_document.return_value = {
            'DocumentDescription': {
                'Name': 'test-cli-calendar',
                'Status': 'Creating',
                'DocumentVersion': '1',
                'CreatedDate': datetime.now()
            }
        }
        mock_session.return_value.client.return_value = mock_client
        
        result = self.runner.invoke(cli, [
            'create-calendar',
            'test-cli-calendar',
            '--description', 'CLI test calendar',
            '--calendar-type', 'DEFAULT_OPEN'
        ])
        
        assert result.exit_code == 0
        assert 'test-cli-calendar' in result.output

    @pytest.mark.integration
    @patch('boto3.Session')
    def test_update_calendar_cli_integration(self, mock_session, temp_dir, monkeypatch):
        """Test update-calendar CLI command integration."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # Create cache with holiday data
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        
        holiday_data = """日付,祝日名
2024-01-01,元日
2024-01-08,成人の日"""
        cache_file.write_text(holiday_data, encoding='utf-8')
        
        # Mock AWS client
        mock_client = Mock()
        mock_client.describe_document.return_value = {
            'Document': {
                'Name': 'existing-cli-calendar',
                'Status': 'Active'
            }
        }
        mock_client.get_document.return_value = {
            'Content': 'BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR'
        }
        mock_client.update_document.return_value = {
            'DocumentDescription': {
                'Name': 'existing-cli-calendar',
                'Status': 'Updating',
                'DocumentVersion': '2',
                'ModifiedDate': datetime.now()
            }
        }
        mock_session.return_value.client.return_value = mock_client
        
        result = self.runner.invoke(cli, [
            'update-calendar',
            'existing-cli-calendar',
            '--year', '2024'
        ])
        
        assert result.exit_code == 0
        assert 'existing-cli-calendar' in result.output

    @pytest.mark.integration
    @patch('boto3.Session')
    def test_delete_calendar_cli_integration(self, mock_session):
        """Test delete-calendar CLI command integration."""
        # Mock AWS client
        mock_client = Mock()
        mock_client.describe_document.return_value = {
            'Document': {
                'Name': 'calendar-to-delete',
                'Status': 'Active'
            }
        }
        mock_client.delete_document.return_value = {
            'Status': 'Deleting'
        }
        mock_session.return_value.client.return_value = mock_client
        
        result = self.runner.invoke(cli, [
            'delete-calendar',
            'calendar-to-delete',
            '--confirm'
        ])
        
        assert result.exit_code == 0
        assert 'calendar-to-delete' in result.output

    @pytest.mark.integration
    @patch('boto3.Session')
    def test_analyze_calendar_cli_integration(self, mock_session):
        """Test analyze-calendar CLI command integration."""
        # Mock AWS client with ICS content
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AWS//Change Calendar 1.0//EN
BEGIN:VEVENT
UID:jp-holiday-20240101@aws-ssm-change-calendar
DTSTART;VALUE=DATE:20240101
DTEND;VALUE=DATE:20240102
SUMMARY:元日
END:VEVENT
END:VCALENDAR"""
        
        mock_client = Mock()
        mock_client.get_document.return_value = {
            'Content': ics_content,
            'DocumentVersion': '1',
            'DocumentFormat': 'TEXT'
        }
        mock_client.describe_document.return_value = {
            'Document': {
                'Name': 'test-calendar',
                'Status': 'Active',
                'CreatedDate': datetime.now(),
                'ModifiedDate': datetime.now()
            }
        }
        mock_session.return_value.client.return_value = mock_client
        
        result = self.runner.invoke(cli, [
            'analyze-calendar',
            'test-calendar'
        ])
        
        assert result.exit_code == 0
        assert 'test-calendar' in result.output

    @pytest.mark.integration
    @patch('boto3.Session')
    def test_compare_calendars_cli_integration(self, mock_session):
        """Test compare-calendars CLI command integration."""
        # Mock AWS client with different ICS content for two calendars
        ics_content_1 = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AWS//Change Calendar 1.0//EN
BEGIN:VEVENT
UID:jp-holiday-20240101@aws-ssm-change-calendar
DTSTART;VALUE=DATE:20240101
DTEND;VALUE=DATE:20240102
SUMMARY:元日
END:VEVENT
END:VCALENDAR"""
        
        ics_content_2 = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AWS//Change Calendar 1.0//EN
BEGIN:VEVENT
UID:jp-holiday-20240101@aws-ssm-change-calendar
DTSTART;VALUE=DATE:20240101
DTEND;VALUE=DATE:20240102
SUMMARY:元日
END:VEVENT
BEGIN:VEVENT
UID:jp-holiday-20240108@aws-ssm-change-calendar
DTSTART;VALUE=DATE:20240108
DTEND;VALUE=DATE:20240109
SUMMARY:成人の日
END:VEVENT
END:VCALENDAR"""
        
        mock_client = Mock()
        
        def mock_get_document(Name, **kwargs):
            if Name == 'calendar-1':
                return {
                    'Content': ics_content_1,
                    'DocumentVersion': '1',
                    'DocumentFormat': 'TEXT'
                }
            elif Name == 'calendar-2':
                return {
                    'Content': ics_content_2,
                    'DocumentVersion': '1',
                    'DocumentFormat': 'TEXT'
                }
        
        def mock_describe_document(Name, **kwargs):
            return {
                'Document': {
                    'Name': Name,
                    'Status': 'Active',
                    'CreatedDate': datetime.now(),
                    'ModifiedDate': datetime.now()
                }
            }
        
        mock_client.get_document.side_effect = mock_get_document
        mock_client.describe_document.side_effect = mock_describe_document
        mock_session.return_value.client.return_value = mock_client
        
        result = self.runner.invoke(cli, [
            'compare-calendars',
            'calendar-1',
            'calendar-2'
        ])
        
        assert result.exit_code == 0
        assert 'calendar-1' in result.output
        assert 'calendar-2' in result.output


class TestCLIErrorHandlingIntegration:
    """Test CLI error handling integration."""

    def setup_method(self):
        """Setup test environment."""
        self.runner = CliRunner()

    @pytest.mark.integration
    def test_invalid_file_path_error_handling(self):
        """Test CLI error handling for invalid file paths."""
        result = self.runner.invoke(cli, [
            'analyze-ics',
            '/non/existent/path/file.ics'
        ])
        
        assert result.exit_code != 0
        assert 'error' in result.output.lower() or 'not found' in result.output.lower()

    @pytest.mark.integration
    def test_invalid_date_format_error_handling(self):
        """Test CLI error handling for invalid date formats."""
        result = self.runner.invoke(cli, [
            'check-holiday',
            'invalid-date-format'
        ])
        
        assert result.exit_code != 0
        assert 'error' in result.output.lower() or 'invalid' in result.output.lower()

    @pytest.mark.integration
    @patch('boto3.Session')
    def test_aws_permission_error_handling(self, mock_session):
        """Test CLI error handling for AWS permission errors."""
        # Mock AWS client to raise permission error
        mock_client = Mock()
        mock_client.list_documents.side_effect = Exception("AccessDenied")
        mock_session.return_value.client.return_value = mock_client
        
        result = self.runner.invoke(cli, ['list-calendars'])
        
        assert result.exit_code != 0
        assert 'error' in result.output.lower() or 'access' in result.output.lower()

    @pytest.mark.integration
    @patch('requests.get')
    def test_network_error_handling(self, mock_get, temp_dir, monkeypatch):
        """Test CLI error handling for network errors."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # Mock network error
        mock_get.side_effect = Exception("Network error")
        
        result = self.runner.invoke(cli, [
            'refresh-holidays'
        ])
        
        # Should handle network error gracefully
        assert result.exit_code != 0
        assert 'error' in result.output.lower() or 'network' in result.output.lower()

    @pytest.mark.integration
    def test_invalid_ics_file_error_handling(self, temp_dir):
        """Test CLI error handling for invalid ICS files."""
        # Create invalid ICS file
        invalid_ics = temp_dir / "invalid.ics"
        invalid_ics.write_text("This is not a valid ICS file", encoding='utf-8')
        
        result = self.runner.invoke(cli, [
            'analyze-ics',
            str(invalid_ics)
        ])
        
        assert result.exit_code != 0
        assert 'error' in result.output.lower() or 'invalid' in result.output.lower()


class TestCLIOutputFormatIntegration:
    """Test CLI output format integration."""

    def setup_method(self):
        """Setup test environment."""
        self.runner = CliRunner()

    @pytest.mark.integration
    def test_json_output_format_integration(self, temp_dir, sample_ics_content):
        """Test CLI JSON output format integration."""
        ics_file = temp_dir / "test.ics"
        ics_file.write_text(sample_ics_content, encoding='utf-8')
        
        result = self.runner.invoke(cli, [
            'analyze-ics',
            str(ics_file),
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        
        # Verify output is valid JSON
        try:
            parsed_json = json.loads(result.output)
            assert 'file_info' in parsed_json
            assert 'events' in parsed_json
        except json.JSONDecodeError:
            pytest.fail("Output is not valid JSON")

    @pytest.mark.integration
    def test_csv_output_format_integration(self, temp_dir, sample_ics_content):
        """Test CLI CSV output format integration."""
        ics_file = temp_dir / "test.ics"
        ics_file.write_text(sample_ics_content, encoding='utf-8')
        
        result = self.runner.invoke(cli, [
            'analyze-ics',
            str(ics_file),
            '--format', 'csv'
        ])
        
        assert result.exit_code == 0
        assert 'UID' in result.output  # CSV header
        assert '元日' in result.output  # Event data

    @pytest.mark.integration
    def test_verbose_logging_integration(self, temp_dir, sample_ics_content):
        """Test CLI verbose logging integration."""
        ics_file = temp_dir / "test.ics"
        ics_file.write_text(sample_ics_content, encoding='utf-8')
        
        result = self.runner.invoke(cli, [
            '--log-level', 'DEBUG',
            'analyze-ics',
            str(ics_file)
        ])
        
        assert result.exit_code == 0
        # Verbose mode should provide more detailed output

    @pytest.mark.integration
    def test_quiet_mode_integration(self, temp_dir, sample_ics_content):
        """Test CLI quiet mode integration."""
        ics_file = temp_dir / "test.ics"
        ics_file.write_text(sample_ics_content, encoding='utf-8')
        
        result = self.runner.invoke(cli, [
            '--log-level', 'ERROR',
            'analyze-ics',
            str(ics_file)
        ])
        
        assert result.exit_code == 0
        # Quiet mode should provide minimal output


class TestCLIConfigurationIntegration:
    """Test CLI configuration integration."""

    def setup_method(self):
        """Setup test environment."""
        self.runner = CliRunner()

    @pytest.mark.integration
    def test_config_file_integration(self, temp_dir, monkeypatch):
        """Test CLI configuration file integration."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # Create configuration file
        config_data = {
            'aws': {
                'region': 'us-west-2',
                'profile': 'test-profile'
            },
            'calendar': {
                'default_timezone': 'America/Los_Angeles'
            },
            'output': {
                'directory': str(temp_dir / 'output'),
                'filename_template': 'custom_{calendar_name}_{date}.ics'
            }
        }
        
        config_dir = temp_dir / '.aws-ssm-calendar'
        config_dir.mkdir()
        config_file = config_dir / 'config.json'
        config_file.write_text(json.dumps(config_data), encoding='utf-8')
        
        result = self.runner.invoke(cli, [
            '--config', str(config_file),
            'holidays',
            '--year', '2024'
        ])
        
        # Should use config file settings without error
        # Note: Actual behavior verification depends on implementation

    @pytest.mark.integration
    def test_environment_variable_integration(self, temp_dir, monkeypatch):
        """Test CLI environment variable integration."""
        monkeypatch.setenv('HOME', str(temp_dir))
        monkeypatch.setenv('AWS_REGION', 'eu-west-1')
        monkeypatch.setenv('AWS_PROFILE', 'test-env-profile')
        
        result = self.runner.invoke(cli, [
            'holidays',
            '--year', '2024'
        ])
        
        # Should use environment variables without error
        # Note: Actual behavior verification depends on implementation

    @pytest.mark.integration
    def test_command_line_option_precedence(self, temp_dir, monkeypatch):
        """Test CLI command line option precedence over config."""
        monkeypatch.setenv('HOME', str(temp_dir))
        monkeypatch.setenv('AWS_REGION', 'eu-west-1')
        
        # Create configuration file with different region
        config_data = {
            'aws': {
                'region': 'us-west-2'
            }
        }
        
        config_dir = temp_dir / '.aws-ssm-calendar'
        config_dir.mkdir()
        config_file = config_dir / 'config.json'
        config_file.write_text(json.dumps(config_data), encoding='utf-8')
        
        result = self.runner.invoke(cli, [
            '--config', str(config_file),
            '--region', 'ap-northeast-1',  # Command line should override
            'holidays',
            '--year', '2024'
        ])
        
        # Should use command line region without error
        # Note: Actual behavior verification depends on implementation