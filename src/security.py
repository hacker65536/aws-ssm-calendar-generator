"""
Security module for input validation and sanitization.

This module provides comprehensive input validation and sanitization
functions to protect against various security vulnerabilities including
path traversal attacks, injection attacks, and malformed input.
"""

import os
import re
import stat
from datetime import datetime, date
from pathlib import Path
from typing import Union, Optional
from urllib.parse import urlparse

from .error_handler import ValidationError


class InputValidator:
    """
    Comprehensive input validation and sanitization class.
    
    Provides methods for validating and sanitizing various types of input
    including dates, calendar names, file paths, and URLs to prevent
    security vulnerabilities.
    """
    
    # Regular expressions for validation
    CALENDAR_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')
    DATE_PATTERNS = [
        r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
        r'^\d{4}/\d{2}/\d{2}$',  # YYYY/MM/DD
        r'^\d{2}/\d{2}/\d{4}$',  # MM/DD/YYYY
        r'^\d{2}-\d{2}-\d{4}$',  # MM-DD-YYYY
    ]
    
    # Maximum lengths for various inputs
    MAX_CALENDAR_NAME_LENGTH = 64
    MAX_FILE_PATH_LENGTH = 260  # Windows MAX_PATH limit
    MAX_DATE_STRING_LENGTH = 20
    
    @classmethod
    def validate_date(cls, date_input: Union[str, date, datetime]) -> date:
        """
        Validate and parse date input with comprehensive format support.
        
        Args:
            date_input: Date input in various formats (string, date, datetime)
            
        Returns:
            date: Validated date object
            
        Raises:
            ValidationError: If date input is invalid or malformed
        """
        if isinstance(date_input, date):
            return date_input
        
        if isinstance(date_input, datetime):
            return date_input.date()
        
        if not isinstance(date_input, str):
            raise ValidationError(f"Invalid date input type: {type(date_input)}")
        
        # Check length to prevent DoS attacks
        if len(date_input) > cls.MAX_DATE_STRING_LENGTH:
            raise ValidationError(f"Date string too long: {len(date_input)} > {cls.MAX_DATE_STRING_LENGTH}")
        
        # Sanitize input - remove whitespace and common injection characters
        sanitized_input = date_input.strip()
        if not sanitized_input:
            raise ValidationError("Empty date input")
        
        # Check for suspicious characters that might indicate injection attempts
        suspicious_chars = ['<', '>', ';', '&', '|', '`', '$', '(', ')']
        if any(char in sanitized_input for char in suspicious_chars):
            raise ValidationError(f"Date input contains suspicious characters: {sanitized_input}")
        
        # Validate format using regex patterns
        format_matched = False
        for pattern in cls.DATE_PATTERNS:
            if re.match(pattern, sanitized_input):
                format_matched = True
                break
        
        if not format_matched:
            raise ValidationError(f"Date format not recognized: {sanitized_input}")
        
        # Try to parse the date using various formats
        date_formats = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%m/%d/%Y',
            '%m-%d-%Y',
        ]
        
        parsed_date = None
        for date_format in date_formats:
            try:
                parsed_date = datetime.strptime(sanitized_input, date_format).date()
                break
            except ValueError:
                continue
        
        if parsed_date is None:
            raise ValidationError(f"Unable to parse date: {sanitized_input}")
        
        # Validate date range (reasonable bounds)
        min_year = 1900
        max_year = 2100
        
        if parsed_date.year < min_year or parsed_date.year > max_year:
            raise ValidationError(f"Date year out of valid range ({min_year}-{max_year}): {parsed_date.year}")
        
        return parsed_date
    
    @classmethod
    def validate_calendar_name(cls, calendar_name: str) -> str:
        """
        Validate and sanitize calendar name input.
        
        Args:
            calendar_name: Calendar name to validate
            
        Returns:
            str: Sanitized calendar name
            
        Raises:
            ValidationError: If calendar name is invalid
        """
        if not isinstance(calendar_name, str):
            raise ValidationError(f"Calendar name must be string, got: {type(calendar_name)}")
        
        # Check length
        if len(calendar_name) > cls.MAX_CALENDAR_NAME_LENGTH:
            raise ValidationError(f"Calendar name too long: {len(calendar_name)} > {cls.MAX_CALENDAR_NAME_LENGTH}")
        
        # Remove leading/trailing whitespace
        sanitized_name = calendar_name.strip()
        
        if not sanitized_name:
            raise ValidationError("Calendar name cannot be empty")
        
        # Check for valid characters (alphanumeric, underscore, hyphen only)
        if not cls.CALENDAR_NAME_PATTERN.match(sanitized_name):
            raise ValidationError(f"Calendar name contains invalid characters: {sanitized_name}")
        
        # Additional security checks
        reserved_names = ['con', 'prn', 'aux', 'nul', 'com1', 'com2', 'com3', 'com4', 
                         'com5', 'com6', 'com7', 'com8', 'com9', 'lpt1', 'lpt2', 
                         'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9']
        
        if sanitized_name.lower() in reserved_names:
            raise ValidationError(f"Calendar name is reserved: {sanitized_name}")
        
        # Check for directory traversal attempts
        if '..' in sanitized_name or '/' in sanitized_name or '\\' in sanitized_name:
            raise ValidationError(f"Calendar name contains path traversal characters: {sanitized_name}")
        
        return sanitized_name
    
    @classmethod
    def validate_file_path(cls, file_path: Union[str, Path], 
                          allow_create: bool = True,
                          require_exists: bool = False) -> Path:
        """
        Validate file path and protect against path traversal attacks.
        
        Args:
            file_path: File path to validate
            allow_create: Whether to allow creation of new files
            require_exists: Whether the file must already exist
            
        Returns:
            Path: Validated and resolved file path
            
        Raises:
            ValidationError: If file path is invalid or unsafe
        """
        if not isinstance(file_path, (str, Path)):
            raise ValidationError(f"File path must be string or Path, got: {type(file_path)}")
        
        # Convert to string for validation
        path_str = str(file_path)
        
        # Check length
        if len(path_str) > cls.MAX_FILE_PATH_LENGTH:
            raise ValidationError(f"File path too long: {len(path_str)} > {cls.MAX_FILE_PATH_LENGTH}")
        
        # Check for null bytes (security vulnerability)
        if '\x00' in path_str:
            raise ValidationError("File path contains null bytes")
        
        # Convert to Path object for manipulation
        try:
            path_obj = Path(path_str)
        except (ValueError, OSError) as e:
            raise ValidationError(f"Invalid file path: {e}")
        
        # Resolve the path to get absolute path and resolve symlinks
        try:
            resolved_path = path_obj.resolve()
        except (OSError, RuntimeError) as e:
            raise ValidationError(f"Cannot resolve file path: {e}")
        
        # Check for path traversal attempts
        # Ensure the resolved path is within allowed directories
        cwd = Path.cwd().resolve()
        home_dir = Path.home().resolve()
        
        # Allow paths within current working directory or user home directory
        allowed_roots = [cwd, home_dir]
        
        # Check if the resolved path is under any allowed root
        is_allowed = False
        for allowed_root in allowed_roots:
            try:
                resolved_path.relative_to(allowed_root)
                is_allowed = True
                break
            except ValueError:
                continue
        
        if not is_allowed:
            raise ValidationError(f"File path outside allowed directories: {resolved_path}")
        
        # Check if file exists when required
        if require_exists and not resolved_path.exists():
            raise ValidationError(f"File does not exist: {resolved_path}")
        
        # Check if parent directory exists when creating new files
        if allow_create and not resolved_path.parent.exists():
            try:
                resolved_path.parent.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError) as e:
                raise ValidationError(f"Cannot create parent directory: {e}")
        
        # Check permissions
        if resolved_path.exists():
            if not os.access(resolved_path, os.R_OK):
                raise ValidationError(f"File not readable: {resolved_path}")
            
            if not allow_create and not os.access(resolved_path, os.W_OK):
                raise ValidationError(f"File not writable: {resolved_path}")
        
        return resolved_path
    
    @classmethod
    def validate_url(cls, url: str, require_https: bool = True) -> str:
        """
        Validate URL and enforce security requirements.
        
        Args:
            url: URL to validate
            require_https: Whether to require HTTPS protocol
            
        Returns:
            str: Validated URL
            
        Raises:
            ValidationError: If URL is invalid or insecure
        """
        if not isinstance(url, str):
            raise ValidationError(f"URL must be string, got: {type(url)}")
        
        url = url.strip()
        if not url:
            raise ValidationError("URL cannot be empty")
        
        try:
            parsed = urlparse(url)
        except Exception as e:
            raise ValidationError(f"Invalid URL format: {e}")
        
        # Check protocol
        if require_https and parsed.scheme != 'https':
            raise ValidationError(f"HTTPS required, got: {parsed.scheme}")
        
        if parsed.scheme not in ['http', 'https']:
            raise ValidationError(f"Invalid URL scheme: {parsed.scheme}")
        
        # Check for suspicious characters
        suspicious_chars = ['<', '>', '"', "'", '`']
        if any(char in url for char in suspicious_chars):
            raise ValidationError(f"URL contains suspicious characters: {url}")
        
        # Basic hostname validation
        if not parsed.netloc:
            raise ValidationError("URL missing hostname")
        
        return url


class SecureFileHandler:
    """
    Secure file operations with proper permissions and validation.
    """
    
    # File permission constants
    SECURE_FILE_PERMISSIONS = 0o600  # rw-------
    READABLE_FILE_PERMISSIONS = 0o644  # rw-r--r--
    SECURE_DIR_PERMISSIONS = 0o700   # rwx------
    
    @classmethod
    def create_secure_file(cls, file_path: Path, content: str = "", 
                          permissions: int = SECURE_FILE_PERMISSIONS) -> None:
        """
        Create file with secure permissions.
        
        Args:
            file_path: Path to create
            content: Initial file content
            permissions: File permissions (default: 600)
        """
        # Validate the file path first
        validated_path = InputValidator.validate_file_path(file_path, allow_create=True)
        
        # Create parent directories with secure permissions
        validated_path.parent.mkdir(parents=True, exist_ok=True, mode=cls.SECURE_DIR_PERMISSIONS)
        
        # Write file with secure permissions
        try:
            # Create file with restrictive permissions first
            validated_path.touch(mode=cls.SECURE_FILE_PERMISSIONS)
            
            # Write content
            validated_path.write_text(content, encoding='utf-8')
            
            # Set final permissions
            validated_path.chmod(permissions)
            
        except (OSError, PermissionError) as e:
            raise ValidationError(f"Cannot create secure file: {e}")
    
    @classmethod
    def read_secure_file(cls, file_path: Path) -> str:
        """
        Read file with security validation.
        
        Args:
            file_path: Path to read
            
        Returns:
            str: File content
        """
        # Validate the file path
        validated_path = InputValidator.validate_file_path(file_path, require_exists=True)
        
        # Check file permissions
        file_stat = validated_path.stat()
        file_mode = stat.filemode(file_stat.st_mode)
        
        # Warn if file is world-readable for sensitive files
        if file_stat.st_mode & stat.S_IROTH:
            # This is a warning, not an error, as some files may legitimately be world-readable
            pass
        
        try:
            return validated_path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError) as e:
            raise ValidationError(f"Cannot read file: {e}")
    
    @classmethod
    def write_secure_file(cls, file_path: Path, content: str,
                         permissions: int = SECURE_FILE_PERMISSIONS) -> None:
        """
        Write file with secure permissions.
        
        Args:
            file_path: Path to write
            content: File content
            permissions: File permissions
        """
        # Validate the file path
        validated_path = InputValidator.validate_file_path(file_path, allow_create=True)
        
        try:
            # Write content atomically
            temp_path = validated_path.with_suffix(validated_path.suffix + '.tmp')
            
            # Create temp file with secure permissions
            temp_path.write_text(content, encoding='utf-8')
            temp_path.chmod(permissions)
            
            # Atomic move
            temp_path.replace(validated_path)
            
        except (OSError, PermissionError) as e:
            # Clean up temp file if it exists
            if temp_path.exists():
                temp_path.unlink()
            raise ValidationError(f"Cannot write secure file: {e}")


# Convenience functions for common validation tasks
def validate_date_input(date_input: Union[str, date, datetime]) -> date:
    """Convenience function for date validation."""
    return InputValidator.validate_date(date_input)


def validate_calendar_name_input(calendar_name: str) -> str:
    """Convenience function for calendar name validation."""
    return InputValidator.validate_calendar_name(calendar_name)


def validate_file_path_input(file_path: Union[str, Path], **kwargs) -> Path:
    """Convenience function for file path validation."""
    return InputValidator.validate_file_path(file_path, **kwargs)


def validate_url_input(url: str, require_https: bool = True) -> str:
    """Convenience function for URL validation."""
    return InputValidator.validate_url(url, require_https)


class NetworkSecurityManager:
    """
    Network security manager for HTTPS-only connections and SSL validation.
    """
    
    @staticmethod
    def create_secure_session():
        """
        Create a secure HTTP session with SSL verification enabled.
        
        Returns:
            requests.Session: Configured secure session
        """
        import requests
        import ssl
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        session = requests.Session()
        
        # Configure SSL context for maximum security
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = True
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        # Set security headers
        session.headers.update({
            'User-Agent': 'aws-ssm-calendar-generator/1.0',
            'Accept': 'text/csv,application/json,text/plain,*/*',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache'
        })
        
        # Verify SSL certificates
        session.verify = True
        
        return session
    
    @staticmethod
    def validate_ssl_certificate(url: str) -> bool:
        """
        Validate SSL certificate for a given URL.
        
        Args:
            url: URL to validate
            
        Returns:
            bool: True if certificate is valid
            
        Raises:
            ValidationError: If certificate validation fails
        """
        import ssl
        import socket
        from urllib.parse import urlparse
        
        try:
            parsed_url = urlparse(url)
            hostname = parsed_url.hostname
            port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
            
            if parsed_url.scheme != 'https':
                raise ValidationError(f"SSL validation requires HTTPS URL: {url}")
            
            # Create SSL context with certificate verification
            context = ssl.create_default_context()
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED
            
            # Connect and verify certificate
            with socket.create_connection((hostname, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    
                    # Additional certificate validation
                    if not cert:
                        raise ValidationError(f"No SSL certificate found for: {hostname}")
                    
                    # Check certificate expiration
                    import datetime
                    not_after = datetime.datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                    if not_after < datetime.datetime.now():
                        raise ValidationError(f"SSL certificate expired for: {hostname}")
                    
                    return True
                    
        except socket.gaierror as e:
            raise ValidationError(f"DNS resolution failed for {hostname}: {e}")
        except socket.timeout as e:
            raise ValidationError(f"Connection timeout for {hostname}: {e}")
        except ssl.SSLError as e:
            raise ValidationError(f"SSL certificate validation failed for {hostname}: {e}")
        except Exception as e:
            raise ValidationError(f"SSL validation error for {url}: {e}")
    
    @staticmethod
    def secure_request(url: str, method: str = 'GET', **kwargs) -> 'requests.Response':
        """
        Make a secure HTTP request with SSL validation.
        
        Args:
            url: URL to request
            method: HTTP method
            **kwargs: Additional request parameters
            
        Returns:
            requests.Response: HTTP response
            
        Raises:
            ValidationError: If request fails security validation
        """
        # Validate URL first
        validated_url = InputValidator.validate_url(url, require_https=True)
        
        # Validate SSL certificate
        NetworkSecurityManager.validate_ssl_certificate(validated_url)
        
        # Create secure session
        session = NetworkSecurityManager.create_secure_session()
        
        try:
            # Set timeout if not provided
            if 'timeout' not in kwargs:
                kwargs['timeout'] = 30
            
            # Make request
            response = session.request(method, validated_url, **kwargs)
            
            # Validate response
            if response.status_code >= 400:
                raise ValidationError(f"HTTP request failed: {response.status_code} {response.reason}")
            
            return response
            
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(f"Secure request failed: {e}")
        finally:
            session.close()


class CredentialSecurityManager:
    """
    Secure credential storage and protection manager.
    """
    
    @staticmethod
    def store_credentials_securely(credentials: dict, file_path: Path) -> None:
        """
        Store credentials with secure file permissions.
        
        Args:
            credentials: Credential dictionary
            file_path: Path to store credentials
        """
        # Validate file path
        validated_path = InputValidator.validate_file_path(file_path, allow_create=True)
        
        # Ensure credentials don't contain sensitive data in plain text
        sanitized_credentials = CredentialSecurityManager._sanitize_credentials(credentials)
        
        # Store with secure permissions
        import json
        content = json.dumps(sanitized_credentials, indent=2)
        SecureFileHandler.create_secure_file(
            validated_path, 
            content, 
            permissions=SecureFileHandler.SECURE_FILE_PERMISSIONS
        )
    
    @staticmethod
    def _sanitize_credentials(credentials: dict) -> dict:
        """
        Sanitize credentials to remove or mask sensitive information.
        
        Args:
            credentials: Raw credentials
            
        Returns:
            dict: Sanitized credentials
        """
        sanitized = {}
        sensitive_keys = ['password', 'secret', 'key', 'token', 'credential']
        
        for key, value in credentials.items():
            key_lower = key.lower()
            
            # Check if key contains sensitive information
            is_sensitive = any(sensitive_word in key_lower for sensitive_word in sensitive_keys)
            
            if is_sensitive and isinstance(value, str) and len(value) > 4:
                # Mask sensitive values
                sanitized[key] = value[:2] + '*' * (len(value) - 4) + value[-2:]
            else:
                sanitized[key] = value
        
        return sanitized
    
    @staticmethod
    def validate_aws_credentials(credentials: dict) -> bool:
        """
        Validate AWS credentials format and security.
        
        Args:
            credentials: AWS credentials dictionary
            
        Returns:
            bool: True if credentials are valid
            
        Raises:
            ValidationError: If credentials are invalid
        """
        required_keys = ['aws_access_key_id', 'aws_secret_access_key']
        
        for key in required_keys:
            if key not in credentials:
                raise ValidationError(f"Missing required AWS credential: {key}")
            
            value = credentials[key]
            if not isinstance(value, str) or not value.strip():
                raise ValidationError(f"Invalid AWS credential value for: {key}")
            
            # Basic format validation
            if key == 'aws_access_key_id':
                if not value.startswith('AKIA') or len(value) != 20:
                    raise ValidationError(f"Invalid AWS Access Key ID format: {value}")
            
            elif key == 'aws_secret_access_key':
                if len(value) != 40:
                    raise ValidationError(f"Invalid AWS Secret Access Key length: {len(value)}")
        
        return True