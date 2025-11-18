"""
API Key Manager
==============
Utility for managing API keys across the application
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

# Define constants
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".drumtrackai")
CONFIG_FILE = os.path.join(CONFIG_DIR, "api_keys.json")


class ApiKeyManager:
    """Manager for API keys across the application."""
    
    # Singleton instance
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'ApiKeyManager':
        """Get or create the ApiKeyManager singleton instance."""
        if cls._instance is None:
            cls._instance = ApiKeyManager()
        return cls._instance
    
    def __init__(self):
        """Initialize the API key manager."""
        # Ensure we have the config directory
        os.makedirs(CONFIG_DIR, exist_ok=True)
        
        # Load existing keys or create empty config
        self._api_keys = {}
        self._load_keys()
        
        # Apply keys to environment
        self._apply_keys_to_environment()
        
        logger.info("API key manager initialized")
    
    def _load_keys(self):
        """Load API keys from the config file."""
        try:
            if not os.path.exists(CONFIG_FILE):
                # Create empty config if it doesn't exist
                with open(CONFIG_FILE, 'w') as f:
                    json.dump({}, f)
                return
            
            with open(CONFIG_FILE, 'r') as f:
                self._api_keys = json.load(f)
                logger.debug(f"Loaded API keys for: {', '.join(self._api_keys.keys())}")
        except Exception as e:
            logger.error(f"Error loading API keys: {e}")
            self._api_keys = {}
    
    def _save_keys(self):
        """Save API keys to the config file."""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self._api_keys, f)
            logger.debug("API keys saved to config file")
        except Exception as e:
            logger.error(f"Error saving API keys: {e}")
    
    def _apply_keys_to_environment(self):
        """Apply all API keys to the environment variables."""
        for key_name, key_value in self._api_keys.items():
            if key_value:  # Only set non-empty keys
                os.environ[key_name] = key_value
                logger.debug(f"Applied {key_name} to environment")
    
    def get_key(self, key_name: str) -> str:
        """
        Get an API key.
        
        Args:
            key_name: Name of the API key (e.g., "MVSEP_API_KEY")
            
        Returns:
            The API key value or empty string if not found
        """
        # First check environment (higher priority)
        env_key = os.environ.get(key_name, '')
        if env_key:
            return env_key
        
        # Then check stored keys
        return self._api_keys.get(key_name, '')
    
    def set_key(self, key_name: str, key_value: str) -> bool:
        """
        Set an API key.
        
        Args:
            key_name: Name of the API key (e.g., "MVSEP_API_KEY")
            key_value: Value of the API key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Store in our dictionary
            self._api_keys[key_name] = key_value
            
            # Apply to environment
            if key_value:
                os.environ[key_name] = key_value
            elif key_name in os.environ:
                del os.environ[key_name]
            
            # Save to config
            self._save_keys()
            
            logger.info(f"API key {key_name} updated successfully")
            return True
        except Exception as e:
            logger.error(f"Error setting API key {key_name}: {e}")
            return False
    
    def delete_key(self, key_name: str) -> bool:
        """
        Delete an API key.
        
        Args:
            key_name: Name of the API key to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Remove from dictionary if exists
            if key_name in self._api_keys:
                del self._api_keys[key_name]
            
            # Remove from environment if exists
            if key_name in os.environ:
                del os.environ[key_name]
            
            # Save updated config
            self._save_keys()
            
            logger.info(f"API key {key_name} deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Error deleting API key {key_name}: {e}")
            return False
    
    def get_all_keys(self) -> Dict[str, str]:
        """
        Get all API keys.
        
        Returns:
            Dictionary of all API keys
        """
        # Create a copy to prevent direct modification
        return dict(self._api_keys)
    
    def is_key_set(self, key_name: str) -> bool:
        """
        Check if an API key is set.
        
        Args:
            key_name: Name of the API key to check
            
        Returns:
            True if the key is set and non-empty, False otherwise
        """
        key = self.get_key(key_name)
        return bool(key and key.strip())


# Convenience function to get the singleton instance
def get_api_key_manager() -> ApiKeyManager:
    """Get the ApiKeyManager singleton instance."""
    return ApiKeyManager.get_instance()
