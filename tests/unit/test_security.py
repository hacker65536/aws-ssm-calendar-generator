"""
Unit tests for Security module.

Task 10.4 Implementation: セキュリティテストの作成
- 入力検証テストを作成
- ファイル権限処理のテストを作成
- ネットワークセキュリティと認証情報保護をテスト
"""

import pytest
import os
import stat
import tempfile
import json
from unittest.mock import patch, mock_open, MagicMock
from pathlib import Path
from datetime import date, datetime
from urllib.parse import urlparse

from src.security import (
    InputValidator,
    SecureFileHandler,
    NetworkSecurityManager,
    CredentialSecurityManager,
    validate_date_input,
    validate_calendar_name_input,
    validate_file_path_input,
    validate_url_input
)
from src.error_handler import ValidationError


class TestInputValidator:
    """Test cases for InputValidator class."""

    def test_validate_date_with_date_object(self):
        """Test date validation with date object input."""
        test_date = date(2025, 1, 1)
        result = InputValidator.validate_date(test_date)
        assert result == test_date

    def test_validate_date_with_datetime_object(self):
        """Test date validation with datetime object input."""
        test_datetime = datetime(2025, 1, 1, 12, 30, 45)
        result = InputValidator.validate_date(test_datetime)
        # Note: datetime is a subclass of date, so isinstance(datetime, date) is True
        # The current implementation returns the datetime object itself
        assert result == test_datetime
        assert isinstance(result, datetime)

    def test_validate_date_with_valid_string_formats(self):
        """Test date validation with various valid string formats."""
        test_cases = [
            ('2025-01-01', date(2025, 1, 1)),
            ('2025/01/01', date(2025, 1, 1)),
            ('01/01/2025', date(2025, 1, 1)),
            ('01-01-2025', date(2025, 1, 1)),
        ]
        
        for date_string, expected_date in test_cases:
            result = InputValidator.validate_date(date_string)
            assert result == expected_date

    def test_validate_date_with_invalid_type(self):
        """Test date validation with invalid input type."""
        with pytest.raises(ValidationError, match="Invalid date input type"):
            InputValidator.validate_date(123)

    def test_validate_date_with_too_long_string(self):
        """Test date validation with excessively long string."""
        long_string = 'x' * 25  # Exceeds MAX_DATE_STRING_LENGTH
        with pytest.raises(ValidationError, match="Date string too long"):
            InputValidator.validate_date(long_string)

    def test_validate_date_with_empty_string(self):
        """Test date validation with empty string."""
        with pytest.raises(ValidationError, match="Empty date input"):
            InputValidator.validate_date("")

    def test_validate_date_with_suspicious_characters(self):
        """Test date validation with suspicious characters."""
        suspicious_inputs = [
            '2025-01-01<script>',
            '2025-01-01; rm -rf /',
            '2025-01-01`whoami`',
            '2025-01-01$(id)',
        ]
        
        for suspicious_input in suspicious_inputs:
            with pytest.raises(ValidationError, match="suspicious characters"):
                InputValidator.validate_date(suspicious_input)

    def test_validate_date_with_invalid_format(self):
        """Test date validation with invalid format."""
        with pytest.raises(ValidationError, match="Date format not recognized"):
            InputValidator.validate_date("invalid-date-format")

    def test_validate_date_with_unparseable_date(self):
        """Test date validation with unparseable date."""
        with pytest.raises(ValidationError, match="Unable to parse date"):
            InputValidator.validate_date("2025-13-45")  # Invalid month/day

    def test_validate_date_with_out_of_range_year(self):
        """Test date validation with year out of valid range."""
        with pytest.raises(ValidationError, match="Date year out of valid range"):
            InputValidator.validate_date("1800-01-01")  # Too old
        
        with pytest.raises(ValidationError, match="Date year out of valid range"):
            InputValidator.validate_date("2200-01-01")  # Too far in future

    def test_validate_calendar_name_with_valid_names(self):
        """Test calendar name validation with valid names."""
        valid_names = [
            'test-calendar',
            'calendar_2025',
            'MyCalendar123',
            'a',
            'test-calendar-with-hyphens',
            'calendar_with_underscores'
        ]
        
        for name in valid_names:
            result = InputValidator.validate_calendar_name(name)
            assert result == name

    def test_validate_calendar_name_with_invalid_type(self):
        """Test calendar name validation with invalid type."""
        with pytest.raises(ValidationError, match="Calendar name must be string"):
            InputValidator.validate_calendar_name(123)

    def test_validate_calendar_name_with_too_long_name(self):
        """Test calendar name validation with excessively long name."""
        long_name = 'x' * 70  # Exceeds MAX_CALENDAR_NAME_LENGTH
        with pytest.raises(ValidationError, match="Calendar name too long"):
            InputValidator.validate_calendar_name(long_name)

    def test_validate_calendar_name_with_empty_name(self):
        """Test calendar name validation with empty name."""
        with pytest.raises(ValidationError, match="Calendar name cannot be empty"):
            InputValidator.validate_calendar_name("")

    def test_validate_calendar_name_with_invalid_characters(self):
        """Test calendar name validation with invalid characters."""
        invalid_names = [
            'calendar with spaces',
            'calendar@domain.com',
            'calendar#123',
            'calendar$var',
            'calendar%encoded',
        ]
        
        for name in invalid_names:
            with pytest.raises(ValidationError, match="invalid characters"):
                InputValidator.validate_calendar_name(name)

    def test_validate_calendar_name_with_reserved_names(self):
        """Test calendar name validation with reserved names."""
        reserved_names = ['con', 'prn', 'aux', 'nul', 'com1', 'lpt1']
        
        for name in reserved_names:
            with pytest.raises(ValidationError, match="Calendar name is reserved"):
                InputValidator.validate_calendar_name(name)

    def test_validate_calendar_name_with_path_traversal(self):
        """Test calendar name validation with path traversal attempts."""
        traversal_names = [
            '../calendar',
            'calendar/../other',
            'calendar/subdir',
            'calendar\\windows',
        ]
        
        for name in traversal_names:
            with pytest.raises(ValidationError, match="invalid characters|path traversal"):
                InputValidator.validate_calendar_name(name)

    def test_validate_file_path_with_valid_paths(self):
        """Test file path validation with valid paths."""
        # Test with current working directory (which is allowed)
        cwd = Path.cwd()
        test_file = cwd / 'test_security_file.txt'
        test_file.write_text('test content')
        
        try:
            # Test existing file
            result = InputValidator.validate_file_path(test_file, require_exists=True)
            assert result.exists()
            
            # Test new file creation
            new_file = cwd / 'new_security_file.txt'
            result = InputValidator.validate_file_path(new_file, allow_create=True)
            assert result.parent.exists()
        finally:
            # Clean up
            if test_file.exists():
                test_file.unlink()
            if (cwd / 'new_security_file.txt').exists():
                (cwd / 'new_security_file.txt').unlink()

    def test_validate_file_path_with_invalid_type(self):
        """Test file path validation with invalid type."""
        with pytest.raises(ValidationError, match="File path must be string or Path"):
            InputValidator.validate_file_path(123)

    def test_validate_file_path_with_too_long_path(self):
        """Test file path validation with excessively long path."""
        long_path = 'x' * 300  # Exceeds MAX_FILE_PATH_LENGTH
        with pytest.raises(ValidationError, match="File path too long"):
            InputValidator.validate_file_path(long_path)

    def test_validate_file_path_with_null_bytes(self):
        """Test file path validation with null bytes."""
        with pytest.raises(ValidationError, match="null bytes"):
            InputValidator.validate_file_path("test\x00file.txt")

    def test_validate_file_path_outside_allowed_directories(self):
        """Test file path validation outside allowed directories."""
        # Try to access system directories
        with pytest.raises(ValidationError, match="outside allowed directories"):
            InputValidator.validate_file_path("/etc/passwd")

    def test_validate_file_path_nonexistent_required(self):
        """Test file path validation when file must exist but doesn't."""
        # Use a path within current directory that doesn't exist
        cwd = Path.cwd()
        nonexistent_file = cwd / "nonexistent_security_test_file.txt"
        with pytest.raises(ValidationError, match="File does not exist"):
            InputValidator.validate_file_path(nonexistent_file, require_exists=True)

    def test_validate_url_with_valid_urls(self):
        """Test URL validation with valid URLs."""
        valid_urls = [
            'https://example.com',
            'https://www.example.com/path',
            'https://api.example.com/v1/data?param=value',
        ]
        
        for url in valid_urls:
            result = InputValidator.validate_url(url)
            assert result == url

    def test_validate_url_with_invalid_type(self):
        """Test URL validation with invalid type."""
        with pytest.raises(ValidationError, match="URL must be string"):
            InputValidator.validate_url(123)

    def test_validate_url_with_empty_url(self):
        """Test URL validation with empty URL."""
        with pytest.raises(ValidationError, match="URL cannot be empty"):
            InputValidator.validate_url("")

    def test_validate_url_with_non_https_when_required(self):
        """Test URL validation with non-HTTPS when HTTPS is required."""
        with pytest.raises(ValidationError, match="HTTPS required"):
            InputValidator.validate_url("http://example.com", require_https=True)

    def test_validate_url_with_invalid_scheme(self):
        """Test URL validation with invalid scheme."""
        with pytest.raises(ValidationError, match="HTTPS required"):
            InputValidator.validate_url("ftp://example.com")

    def test_validate_url_with_suspicious_characters(self):
        """Test URL validation with suspicious characters."""
        suspicious_urls = [
            'https://example.com<script>',
            'https://example.com"onclick="alert(1)"',
            "https://example.com'onload='alert(1)'",
        ]
        
        for url in suspicious_urls:
            with pytest.raises(ValidationError, match="suspicious characters"):
                InputValidator.validate_url(url)

    def test_validate_url_without_hostname(self):
        """Test URL validation without hostname."""
        with pytest.raises(ValidationError, match="URL missing hostname"):
            InputValidator.validate_url("https://")


class TestSecureFileHandler:
    """Test cases for SecureFileHandler class."""

    def test_create_secure_file_with_default_permissions(self):
        """Test creating secure file with default permissions."""
        # Use current working directory for test
        cwd = Path.cwd()
        test_file = cwd / 'secure_test.txt'
        test_content = 'secure content'
        
        try:
            SecureFileHandler.create_secure_file(test_file, test_content)
            
            # Check file exists and has correct content
            assert test_file.exists()
            assert test_file.read_text() == test_content
            
            # Check file permissions (600 = rw-------)
            file_stat = test_file.stat()
            file_mode = file_stat.st_mode & 0o777
            assert file_mode == 0o600
        finally:
            # Clean up
            if test_file.exists():
                test_file.unlink()

    def test_create_secure_file_with_custom_permissions(self):
        """Test creating secure file with custom permissions."""
        # Use current working directory for test
        cwd = Path.cwd()
        test_file = cwd / 'readable_test.txt'
        test_content = 'readable content'
        
        try:
            SecureFileHandler.create_secure_file(
                test_file, 
                test_content, 
                permissions=SecureFileHandler.READABLE_FILE_PERMISSIONS
            )
            
            # Check file permissions (644 = rw-r--r--)
            file_stat = test_file.stat()
            file_mode = file_stat.st_mode & 0o777
            assert file_mode == 0o644
        finally:
            # Clean up
            if test_file.exists():
                test_file.unlink()

    def test_create_secure_file_creates_parent_directories(self):
        """Test that creating secure file creates parent directories."""
        # Use current working directory for test
        cwd = Path.cwd()
        nested_file = cwd / 'nested_security_test' / 'dir' / 'test.txt'
        
        try:
            SecureFileHandler.create_secure_file(nested_file, 'content')
            
            assert nested_file.exists()
            assert nested_file.parent.exists()
        finally:
            # Clean up
            if nested_file.exists():
                nested_file.unlink()
            # Remove created directories
            if (cwd / 'nested_security_test').exists():
                import shutil
                shutil.rmtree(cwd / 'nested_security_test')

    def test_read_secure_file_success(self):
        """Test reading secure file successfully."""
        # Use current working directory for test
        cwd = Path.cwd()
        test_file = cwd / 'read_test.txt'
        test_content = 'test content for reading'
        
        try:
            # Create file first
            SecureFileHandler.create_secure_file(test_file, test_content)
            
            # Read file
            result = SecureFileHandler.read_secure_file(test_file)
            assert result == test_content
        finally:
            # Clean up
            if test_file.exists():
                test_file.unlink()

    def test_read_secure_file_nonexistent(self):
        """Test reading non-existent secure file."""
        # Use current working directory for test
        cwd = Path.cwd()
        nonexistent_file = cwd / "nonexistent_read_test.txt"
        with pytest.raises(ValidationError, match="File does not exist"):
            SecureFileHandler.read_secure_file(nonexistent_file)

    def test_write_secure_file_atomic_operation(self):
        """Test that writing secure file is atomic."""
        # Use current working directory for test
        cwd = Path.cwd()
        test_file = cwd / 'atomic_test.txt'
        test_content = 'atomic write content'
        
        try:
            SecureFileHandler.write_secure_file(test_file, test_content)
            
            # Check file exists and has correct content
            assert test_file.exists()
            assert test_file.read_text() == test_content
            
            # Check no temporary files remain
            temp_files = list(cwd.glob('atomic_test.txt.tmp'))
            assert len(temp_files) == 0
        finally:
            # Clean up
            if test_file.exists():
                test_file.unlink()


class TestNetworkSecurityManager:
    """Test cases for NetworkSecurityManager class."""

    @patch('requests.Session')
    def test_create_secure_session(self, mock_session_class):
        """Test creating secure HTTP session."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        session = NetworkSecurityManager.create_secure_session()
        
        # Verify session configuration
        mock_session_class.assert_called_once()
        assert mock_session.verify is True
        mock_session.headers.update.assert_called_once()

    @patch('socket.create_connection')
    @patch('ssl.create_default_context')
    def test_validate_ssl_certificate_success(self, mock_ssl_context, mock_socket):
        """Test successful SSL certificate validation."""
        # Mock SSL context and socket
        mock_context = MagicMock()
        mock_ssl_context.return_value = mock_context
        
        mock_sock = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_sock
        
        mock_ssl_sock = MagicMock()
        mock_context.wrap_socket.return_value.__enter__.return_value = mock_ssl_sock
        
        # Mock valid certificate with proper format
        from datetime import datetime, timedelta
        future_date = datetime.now() + timedelta(days=365)
        # Use the exact format expected by strptime
        cert_date = future_date.strftime('%b %d %H:%M:%S %Y GMT')
        mock_ssl_sock.getpeercert.return_value = {
            'notAfter': cert_date
        }
        
        # Should not raise exception
        result = NetworkSecurityManager.validate_ssl_certificate('https://example.com')
        assert result is True

    def test_validate_ssl_certificate_non_https(self):
        """Test SSL certificate validation with non-HTTPS URL."""
        with pytest.raises(ValidationError, match="SSL validation requires HTTPS URL"):
            NetworkSecurityManager.validate_ssl_certificate('http://example.com')

    @patch('src.security.NetworkSecurityManager.validate_ssl_certificate')
    @patch('src.security.NetworkSecurityManager.create_secure_session')
    def test_secure_request_success(self, mock_create_session, mock_validate_ssl):
        """Test successful secure HTTP request."""
        # Mock SSL validation
        mock_validate_ssl.return_value = True
        
        # Mock session and response
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.request.return_value = mock_response
        mock_create_session.return_value = mock_session
        
        result = NetworkSecurityManager.secure_request('https://example.com')
        
        assert result == mock_response
        mock_validate_ssl.assert_called_once_with('https://example.com')
        mock_session.request.assert_called_once()
        mock_session.close.assert_called_once()

    @patch('src.security.NetworkSecurityManager.validate_ssl_certificate')
    @patch('src.security.NetworkSecurityManager.create_secure_session')
    def test_secure_request_http_error(self, mock_create_session, mock_validate_ssl):
        """Test secure HTTP request with HTTP error."""
        # Mock SSL validation
        mock_validate_ssl.return_value = True
        
        # Mock session and error response
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.reason = 'Not Found'
        mock_session.request.return_value = mock_response
        mock_create_session.return_value = mock_session
        
        with pytest.raises(ValidationError, match="HTTP request failed: 404"):
            NetworkSecurityManager.secure_request('https://example.com')


class TestCredentialSecurityManager:
    """Test cases for CredentialSecurityManager class."""

    def test_store_credentials_securely(self):
        """Test storing credentials with secure permissions."""
        # Use current working directory for test
        cwd = Path.cwd()
        cred_file = cwd / 'credentials.json'
        
        credentials = {
            'username': 'testuser',
            'password': 'secretpassword',
            'api_key': 'verylongapikey123456'
        }
        
        try:
            CredentialSecurityManager.store_credentials_securely(credentials, cred_file)
            
            # Check file exists
            assert cred_file.exists()
            
            # Check file permissions (600 = rw-------)
            file_stat = cred_file.stat()
            file_mode = file_stat.st_mode & 0o777
            assert file_mode == 0o600
            
            # Check content is sanitized
            content = json.loads(cred_file.read_text())
            assert content['username'] == 'testuser'
            assert '*' in content['password']  # Should be masked
            assert '*' in content['api_key']   # Should be masked
        finally:
            # Clean up
            if cred_file.exists():
                cred_file.unlink()

    def test_sanitize_credentials(self):
        """Test credential sanitization."""
        credentials = {
            'username': 'testuser',
            'password': 'secretpassword',
            'api_key': 'verylongapikey123456',
            'token': 'shorttoken',
            'short': 'abc',  # Too short to mask (<=4 chars)
            'region': 'us-east-1'  # Non-sensitive
        }
        
        sanitized = CredentialSecurityManager._sanitize_credentials(credentials)
        
        assert sanitized['username'] == 'testuser'  # Not sensitive
        assert sanitized['password'] == 'se**********rd'  # Masked
        assert sanitized['api_key'] == 've****************56'  # Masked (adjusted for actual length)
        assert sanitized['token'] == 'sh******en'  # Masked (>4 chars and sensitive)
        assert sanitized['short'] == 'abc'  # Too short to mask (<=4 chars)
        assert sanitized['region'] == 'us-east-1'  # Not sensitive

    def test_validate_aws_credentials_success(self):
        """Test successful AWS credentials validation."""
        valid_credentials = {
            'aws_access_key_id': 'AKIAIOSFODNN7EXAMPLE',
            'aws_secret_access_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
        }
        
        result = CredentialSecurityManager.validate_aws_credentials(valid_credentials)
        assert result is True

    def test_validate_aws_credentials_missing_key(self):
        """Test AWS credentials validation with missing key."""
        incomplete_credentials = {
            'aws_access_key_id': 'AKIAIOSFODNN7EXAMPLE'
            # Missing aws_secret_access_key
        }
        
        with pytest.raises(ValidationError, match="Missing required AWS credential"):
            CredentialSecurityManager.validate_aws_credentials(incomplete_credentials)

    def test_validate_aws_credentials_invalid_access_key_format(self):
        """Test AWS credentials validation with invalid access key format."""
        invalid_credentials = {
            'aws_access_key_id': 'INVALID_ACCESS_KEY',  # Wrong format
            'aws_secret_access_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
        }
        
        with pytest.raises(ValidationError, match="Invalid AWS Access Key ID format"):
            CredentialSecurityManager.validate_aws_credentials(invalid_credentials)

    def test_validate_aws_credentials_invalid_secret_key_length(self):
        """Test AWS credentials validation with invalid secret key length."""
        invalid_credentials = {
            'aws_access_key_id': 'AKIAIOSFODNN7EXAMPLE',
            'aws_secret_access_key': 'TOO_SHORT'  # Wrong length
        }
        
        with pytest.raises(ValidationError, match="Invalid AWS Secret Access Key length"):
            CredentialSecurityManager.validate_aws_credentials(invalid_credentials)


class TestConvenienceFunctions:
    """Test cases for convenience functions."""

    def test_validate_date_input_convenience(self):
        """Test validate_date_input convenience function."""
        result = validate_date_input('2025-01-01')
        assert result == date(2025, 1, 1)

    def test_validate_calendar_name_input_convenience(self):
        """Test validate_calendar_name_input convenience function."""
        result = validate_calendar_name_input('test-calendar')
        assert result == 'test-calendar'

    def test_validate_file_path_input_convenience(self):
        """Test validate_file_path_input convenience function."""
        # Use current working directory for test
        cwd = Path.cwd()
        test_file = cwd / 'convenience_test.txt'
        test_file.write_text('test')
        
        try:
            result = validate_file_path_input(test_file, require_exists=True)
            assert result.exists()
        finally:
            # Clean up
            if test_file.exists():
                test_file.unlink()

    def test_validate_url_input_convenience(self):
        """Test validate_url_input convenience function."""
        result = validate_url_input('https://example.com')
        assert result == 'https://example.com'


class TestSecurityIntegration:
    """Integration tests for security components."""

    def test_end_to_end_secure_file_operations(self):
        """Test end-to-end secure file operations."""
        # Use current working directory for test
        cwd = Path.cwd()
        
        # Validate file path
        secure_file = cwd / 'secure_data.json'
        validated_path = InputValidator.validate_file_path(secure_file, allow_create=True)
        
        try:
            # Create secure file
            test_data = {'sensitive': 'data', 'timestamp': '2025-01-01'}
            SecureFileHandler.create_secure_file(
                validated_path, 
                json.dumps(test_data),
                permissions=SecureFileHandler.SECURE_FILE_PERMISSIONS
            )
            
            # Read secure file
            content = SecureFileHandler.read_secure_file(validated_path)
            loaded_data = json.loads(content)
            
            assert loaded_data == test_data
            
            # Check permissions
            file_stat = validated_path.stat()
            file_mode = file_stat.st_mode & 0o777
            assert file_mode == 0o600
        finally:
            # Clean up
            if secure_file.exists():
                secure_file.unlink()

    def test_credential_security_workflow(self):
        """Test complete credential security workflow."""
        # Use current working directory for test
        cwd = Path.cwd()
        cred_file = cwd / 'aws_credentials.json'
        
        # Validate credentials
        credentials = {
            'aws_access_key_id': 'AKIAIOSFODNN7EXAMPLE',
            'aws_secret_access_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
        }
        
        try:
            # Validate AWS credentials format
            CredentialSecurityManager.validate_aws_credentials(credentials)
            
            # Store securely
            CredentialSecurityManager.store_credentials_securely(credentials, cred_file)
            
            # Verify file security
            assert cred_file.exists()
            file_stat = cred_file.stat()
            file_mode = file_stat.st_mode & 0o777
            assert file_mode == 0o600
            
            # Verify content is sanitized
            content = json.loads(cred_file.read_text())
            assert '*' in content['aws_secret_access_key']  # Should be masked
        finally:
            # Clean up
            if cred_file.exists():
                cred_file.unlink()

    def test_input_validation_security_chain(self):
        """Test security validation chain for various inputs."""
        # Test date validation chain
        validated_date = validate_date_input('2025-01-01')
        assert isinstance(validated_date, date)
        
        # Test calendar name validation chain
        validated_name = validate_calendar_name_input('secure-calendar-2025')
        assert validated_name == 'secure-calendar-2025'
        
        # Test URL validation chain
        validated_url = validate_url_input('https://secure.example.com/api')
        assert validated_url == 'https://secure.example.com/api'
        
        # Test that invalid inputs are properly rejected
        with pytest.raises(ValidationError):
            validate_date_input('invalid-date<script>')
        
        with pytest.raises(ValidationError):
            validate_calendar_name_input('../../../etc/passwd')
        
        with pytest.raises(ValidationError):
            validate_url_input('http://insecure.example.com')