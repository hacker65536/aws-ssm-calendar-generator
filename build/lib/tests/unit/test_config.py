"""
Unit tests for Configuration management.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
import json
import os
import tempfile

from src.config import Configuration, ConfigurationError


class TestConfiguration:
    """Test cases for Configuration class."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        config = Configuration()
        
        assert config.aws_region == 'us-east-1'
        assert config.aws_profile is None
        assert config.default_timezone == 'UTC'
        assert config.output_format == 'ics'

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        config = Configuration(
            aws_region='ap-northeast-1',
            aws_profile='test-profile',
            default_timezone='Asia/Tokyo',
            output_format='json'
        )
        
        assert config.aws_region == 'ap-northeast-1'
        assert config.aws_profile == 'test-profile'
        assert config.default_timezone == 'Asia/Tokyo'
        assert config.output_format == 'json'

    def test_load_from_file_success(self, temp_dir):
        """Test loading configuration from file."""
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
        
        config_file = temp_dir / 'config.json'
        config_file.write_text(json.dumps(config_data), encoding='utf-8')
        
        config = Configuration.load_from_file(str(config_file))
        
        assert config.aws_region == 'eu-west-1'
        assert config.aws_profile == 'production'
        assert config.default_timezone == 'Europe/London'
        assert config.output_format == 'csv'

    def test_load_from_file_not_found(self):
        """Test loading configuration from non-existent file."""
        with pytest.raises(ConfigurationError):
            Configuration.load_from_file('non_existent_config.json')

    def test_load_from_file_invalid_json(self, temp_dir):
        """Test loading configuration from invalid JSON file."""
        config_file = temp_dir / 'invalid_config.json'
        config_file.write_text('{ invalid json }', encoding='utf-8')
        
        with pytest.raises(ConfigurationError):
            Configuration.load_from_file(str(config_file))

    def test_load_from_env_variables(self, monkeypatch):
        """Test loading configuration from environment variables."""
        monkeypatch.setenv('AWS_REGION', 'us-west-2')
        monkeypatch.setenv('AWS_PROFILE', 'dev-profile')
        monkeypatch.setenv('DEFAULT_TIMEZONE', 'America/Los_Angeles')
        monkeypatch.setenv('OUTPUT_FORMAT', 'json')
        
        config = Configuration.load_from_env()
        
        assert config.aws_region == 'us-west-2'
        assert config.aws_profile == 'dev-profile'
        assert config.default_timezone == 'America/Los_Angeles'
        assert config.output_format == 'json'

    def test_load_from_env_partial(self, monkeypatch):
        """Test loading configuration from partial environment variables."""
        monkeypatch.setenv('AWS_REGION', 'us-west-2')
        # Other env vars not set
        
        config = Configuration.load_from_env()
        
        assert config.aws_region == 'us-west-2'
        assert config.aws_profile is None  # Default value
        assert config.default_timezone == 'UTC'  # Default value

    def test_save_to_file(self, temp_dir):
        """Test saving configuration to file."""
        config = Configuration(
            aws_region='ap-southeast-1',
            aws_profile='test-profile',
            default_timezone='Asia/Singapore'
        )
        
        config_file = temp_dir / 'saved_config.json'
        config.save_to_file(str(config_file))
        
        assert config_file.exists()
        
        # Verify saved content
        saved_data = json.loads(config_file.read_text(encoding='utf-8'))
        assert saved_data['aws']['region'] == 'ap-southeast-1'
        assert saved_data['aws']['profile'] == 'test-profile'
        assert saved_data['calendar']['default_timezone'] == 'Asia/Singapore'

    def test_validate_valid_config(self):
        """Test validation of valid configuration."""
        config = Configuration(
            aws_region='us-east-1',
            default_timezone='UTC',
            output_format='ics'
        )
        
        # Should not raise exception
        config.validate()

    def test_validate_invalid_region(self):
        """Test validation with invalid AWS region."""
        config = Configuration(aws_region='invalid-region')
        
        with pytest.raises(ConfigurationError):
            config.validate()

    def test_validate_invalid_timezone(self):
        """Test validation with invalid timezone."""
        config = Configuration(default_timezone='Invalid/Timezone')
        
        with pytest.raises(ConfigurationError):
            config.validate()

    def test_validate_invalid_output_format(self):
        """Test validation with invalid output format."""
        config = Configuration(output_format='invalid_format')
        
        with pytest.raises(ConfigurationError):
            config.validate()

    def test_merge_configurations(self):
        """Test merging multiple configurations."""
        base_config = Configuration(
            aws_region='us-east-1',
            aws_profile='base-profile'
        )
        
        override_config = Configuration(
            aws_region='us-west-2',
            default_timezone='America/Los_Angeles'
        )
        
        merged = Configuration.merge(base_config, override_config)
        
        assert merged.aws_region == 'us-west-2'  # Overridden
        assert merged.aws_profile == 'base-profile'  # From base
        assert merged.default_timezone == 'America/Los_Angeles'  # From override

    def test_to_dict(self):
        """Test converting configuration to dictionary."""
        config = Configuration(
            aws_region='eu-central-1',
            aws_profile='test-profile',
            default_timezone='Europe/Berlin'
        )
        
        config_dict = config.to_dict()
        
        assert config_dict['aws']['region'] == 'eu-central-1'
        assert config_dict['aws']['profile'] == 'test-profile'
        assert config_dict['calendar']['default_timezone'] == 'Europe/Berlin'

    def test_from_dict(self):
        """Test creating configuration from dictionary."""
        config_dict = {
            'aws': {
                'region': 'ca-central-1',
                'profile': 'canada-profile'
            },
            'calendar': {
                'default_timezone': 'America/Toronto',
                'output_format': 'csv'
            }
        }
        
        config = Configuration.from_dict(config_dict)
        
        assert config.aws_region == 'ca-central-1'
        assert config.aws_profile == 'canada-profile'
        assert config.default_timezone == 'America/Toronto'
        assert config.output_format == 'csv'

    def test_get_cache_directory(self, temp_dir, monkeypatch):
        """Test getting cache directory path."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        config = Configuration()
        cache_dir = config.get_cache_directory()
        
        expected_path = temp_dir / '.aws-ssm-calendar' / 'cache'
        assert cache_dir == expected_path

    def test_get_config_file_path(self, temp_dir, monkeypatch):
        """Test getting configuration file path."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        config = Configuration()
        config_path = config.get_config_file_path()
        
        expected_path = temp_dir / '.aws-ssm-calendar' / 'config.json'
        assert config_path == expected_path