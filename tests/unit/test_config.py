"""
Unit tests for Configuration management.
"""

import pytest
from unittest.mock import patch, mock_open
import json
import os
import tempfile
from pathlib import Path

from src.config import Config


class TestConfig:
    """Test cases for Config class."""

    @pytest.fixture(autouse=True)
    def clean_environment(self, monkeypatch):
        """Clean environment variables for each test."""
        monkeypatch.delenv('AWS_PROFILE', raising=False)
        monkeypatch.delenv('AWS_DEFAULT_REGION', raising=False)
        monkeypatch.delenv('AWS_REGION', raising=False)

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        with patch('os.path.exists', return_value=False):
            config = Config()
            
            assert config.get('aws.region') == 'ap-northeast-1'
            assert config.get('aws.profile') is None
            assert config.get('calendar.default_timezone') == 'UTC'
            assert config.get('calendar.output_format') == 'ics'

    def test_init_with_custom_config_file(self):
        """Test initialization with custom config file path."""
        custom_path = '/custom/config.json'
        with patch('os.path.exists', return_value=False):
            config = Config(config_file=custom_path)
            assert config.config_file == custom_path

    def test_load_config_from_file_success(self):
        """Test loading configuration from file successfully."""
        config_data = {
            'aws': {
                'region': 'eu-west-1',
                'profile': 'production'
            },
            'calendar': {
                'default_timezone': 'Europe/London',
                'output_format': 'csv'
            }
        }
        
        mock_file_content = json.dumps(config_data)
        
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=mock_file_content)):
            config = Config()
            
            assert config.get('aws.region') == 'eu-west-1'
            assert config.get('aws.profile') == 'production'
            assert config.get('calendar.default_timezone') == 'Europe/London'
            assert config.get('calendar.output_format') == 'csv'

    def test_load_config_file_not_found(self):
        """Test loading configuration when file doesn't exist."""
        with patch('os.path.exists', return_value=False):
            config = Config()
            # Should use default values
            assert config.get('aws.region') == 'ap-northeast-1'

    def test_load_config_invalid_json(self):
        """Test loading configuration from invalid JSON file."""
        invalid_json = '{ invalid json }'
        
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=invalid_json)), \
             patch('builtins.print') as mock_print:
            config = Config()
            
            # Should use default values and print warning
            assert config.get('aws.region') == 'ap-northeast-1'
            mock_print.assert_called()

    def test_load_config_io_error(self):
        """Test loading configuration with IO error."""
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', side_effect=IOError("Permission denied")), \
             patch('builtins.print') as mock_print:
            config = Config()
            
            # Should use default values and print warning
            assert config.get('aws.region') == 'ap-northeast-1'
            mock_print.assert_called()

    def test_environment_variable_override_aws_profile(self, monkeypatch):
        """Test AWS_PROFILE environment variable override."""
        monkeypatch.setenv('AWS_PROFILE', 'test-profile')
        
        with patch('os.path.exists', return_value=False):
            config = Config()
            assert config.get('aws.profile') == 'test-profile'

    def test_environment_variable_override_aws_region(self, monkeypatch):
        """Test AWS_DEFAULT_REGION environment variable override."""
        monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-west-2')
        
        with patch('os.path.exists', return_value=False):
            config = Config()
            assert config.get('aws.region') == 'us-west-2'

    def test_environment_variable_override_both(self, monkeypatch):
        """Test both AWS environment variables override."""
        monkeypatch.setenv('AWS_PROFILE', 'dev-profile')
        monkeypatch.setenv('AWS_DEFAULT_REGION', 'eu-central-1')
        
        with patch('os.path.exists', return_value=False):
            config = Config()
            assert config.get('aws.profile') == 'dev-profile'
            assert config.get('aws.region') == 'eu-central-1'

    def test_merge_config_simple(self):
        """Test merging simple configuration."""
        with patch('os.path.exists', return_value=False):
            config = Config()
            
            new_config = {'aws': {'region': 'us-east-1'}}
            config._merge_config(new_config)
            
            assert config.get('aws.region') == 'us-east-1'
            # Other values should remain
            assert config.get('aws.profile') is None

    def test_merge_config_nested(self):
        """Test merging nested configuration."""
        with patch('os.path.exists', return_value=False):
            config = Config()
            
            new_config = {
                'aws': {'profile': 'new-profile'},
                'calendar': {'default_timezone': 'Asia/Tokyo'}
            }
            config._merge_config(new_config)
            
            assert config.get('aws.profile') == 'new-profile'
            assert config.get('calendar.default_timezone') == 'Asia/Tokyo'
            # Original values should remain
            assert config.get('aws.region') == 'ap-northeast-1'

    def test_merge_config_overwrite_existing(self):
        """Test merging configuration overwrites existing values."""
        with patch('os.path.exists', return_value=False):
            config = Config()
            
            new_config = {'output': {'directory': '/new/path'}}
            config._merge_config(new_config)
            
            assert config.get('output.directory') == '/new/path'
            # Other output values should remain
            assert config.get('output.filename_template') == '{calendar_name}_{date}.ics'

    def test_get_existing_key(self):
        """Test getting existing configuration key."""
        with patch('os.path.exists', return_value=False):
            config = Config()
            assert config.get('aws.region') == 'ap-northeast-1'

    def test_get_nonexistent_key_with_default(self):
        """Test getting non-existent key with default value."""
        with patch('os.path.exists', return_value=False):
            config = Config()
            assert config.get('nonexistent.key', 'default_value') == 'default_value'

    def test_get_nonexistent_key_without_default(self):
        """Test getting non-existent key without default value."""
        with patch('os.path.exists', return_value=False):
            config = Config()
            assert config.get('nonexistent.key') is None

    def test_get_invalid_key_path(self):
        """Test getting configuration with invalid key path."""
        with patch('os.path.exists', return_value=False):
            config = Config()
            # Try to access string as dict
            assert config.get('aws.region.invalid') is None

    def test_set_new_key(self):
        """Test setting new configuration key."""
        with patch('os.path.exists', return_value=False):
            config = Config()
            config.set('new.key', 'new_value')
            assert config.get('new.key') == 'new_value'

    def test_set_existing_key(self):
        """Test setting existing configuration key."""
        with patch('os.path.exists', return_value=False):
            config = Config()
            config.set('aws.region', 'us-west-1')
            assert config.get('aws.region') == 'us-west-1'

    def test_set_nested_new_key(self):
        """Test setting nested new configuration key."""
        with patch('os.path.exists', return_value=False):
            config = Config()
            config.set('new.nested.key', 'nested_value')
            assert config.get('new.nested.key') == 'nested_value'

    def test_get_aws_config(self):
        """Test getting AWS configuration section."""
        with patch('os.path.exists', return_value=False):
            config = Config()
            aws_config = config.get_aws_config()
            
            assert aws_config['region'] == 'ap-northeast-1'
            assert aws_config['profile'] is None

    def test_get_output_config(self):
        """Test getting output configuration section."""
        with patch('os.path.exists', return_value=False):
            config = Config()
            output_config = config.get_output_config()
            
            assert output_config['directory'] == './output'
            assert output_config['filename_template'] == '{calendar_name}_{date}.ics'

    def test_save_config_success(self):
        """Test saving configuration to file successfully."""
        with patch('os.path.exists', return_value=False):
            config = Config()
            
        with patch('os.makedirs') as mock_makedirs, \
             patch('builtins.open', mock_open()) as mock_file:
            config.save_config()
            
            mock_makedirs.assert_called_once()
            mock_file.assert_called_once()

    def test_save_config_io_error(self):
        """Test saving configuration with IO error."""
        with patch('os.path.exists', return_value=False):
            config = Config()
            
        with patch('os.makedirs'), \
             patch('builtins.open', side_effect=IOError("Permission denied")), \
             patch('builtins.print') as mock_print:
            config.save_config()
            
            mock_print.assert_called()

    def test_default_config_path_generation(self):
        """Test default configuration path generation."""
        with patch('pathlib.Path.home') as mock_home, \
             patch('os.path.exists', return_value=False), \
             patch('pathlib.Path.mkdir') as mock_mkdir:
            mock_home.return_value = Path('/home/user')
            
            config = Config()
            expected_path = '/home/user/.aws-ssm-calendar/config.json'
            assert config.config_file == expected_path
            mock_mkdir.assert_called_once_with(exist_ok=True)

    def test_file_and_env_merge_priority(self, monkeypatch):
        """Test that environment variables override file configuration."""
        # Set environment variable
        monkeypatch.setenv('AWS_PROFILE', 'env-profile')
        
        # Mock file with different value
        config_data = {'aws': {'profile': 'file-profile'}}
        mock_file_content = json.dumps(config_data)
        
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=mock_file_content)):
            config = Config()
            
            # Environment variable should take priority
            assert config.get('aws.profile') == 'env-profile'