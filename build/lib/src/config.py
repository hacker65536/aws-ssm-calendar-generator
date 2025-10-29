"""Configuration management module."""

import os
import json
from typing import Dict, Optional, Any
from pathlib import Path


class Config:
    """Configuration management for the application."""
    
    DEFAULT_CONFIG = {
        'aws': {
            'region': 'ap-northeast-1',  # Tokyo region for Japanese holidays
            'profile': None
        },
        'calendar': {
            'default_timezone': 'UTC',
            'output_format': 'ics'
        },
        'output': {
            'directory': './output',
            'filename_template': '{calendar_name}_{date}.ics'
        }
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration.
        
        Args:
            config_file: Path to configuration file (optional)
        """
        self.config_file = config_file or self._get_default_config_path()
        self.config = self.DEFAULT_CONFIG.copy()
        self.load_config()
    
    def _get_default_config_path(self) -> str:
        """Get default configuration file path.
        
        Returns:
            Default config file path
        """
        home_dir = Path.home()
        config_dir = home_dir / '.aws-ssm-calendar'
        config_dir.mkdir(exist_ok=True)
        return str(config_dir / 'config.json')
    
    def load_config(self):
        """Load configuration from file and environment variables."""
        # Load from file
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                    self._merge_config(file_config)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Failed to load config file {self.config_file}: {e}")
        
        # Override with environment variables
        env_config = {}
        if os.getenv('AWS_PROFILE'):
            env_config['aws'] = {'profile': os.getenv('AWS_PROFILE')}
        if os.getenv('AWS_DEFAULT_REGION'):
            if 'aws' not in env_config:
                env_config['aws'] = {}
            env_config['aws']['region'] = os.getenv('AWS_DEFAULT_REGION')
        
        if env_config:
            self._merge_config(env_config)
    
    def save_config(self):
        """Save current configuration to file."""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except IOError as e:
            print(f"Warning: Failed to save config file {self.config_file}: {e}")
    
    def _merge_config(self, new_config: Dict[str, Any]):
        """Merge new configuration with existing config.
        
        Args:
            new_config: New configuration to merge
        """
        def merge_dict(base: Dict, update: Dict):
            for key, value in update.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    merge_dict(base[key], value)
                else:
                    base[key] = value
        
        merge_dict(self.config, new_config)
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value by key path.
        
        Args:
            key_path: Dot-separated key path (e.g., 'aws.region')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any):
        """Set configuration value by key path.
        
        Args:
            key_path: Dot-separated key path
            value: Value to set
        """
        keys = key_path.split('.')
        config = self.config
        
        # Navigate to the parent dictionary
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # Set the final value
        config[keys[-1]] = value
    
    def get_aws_config(self) -> Dict[str, Any]:
        """Get AWS configuration.
        
        Returns:
            AWS configuration dictionary
        """
        return self.config.get('aws', {})
    
    def get_output_config(self) -> Dict[str, Any]:
        """Get output configuration.
        
        Returns:
            Output configuration dictionary
        """
        return self.config.get('output', {})