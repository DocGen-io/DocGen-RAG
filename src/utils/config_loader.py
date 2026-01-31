"""Configuration loading utilities."""
import yaml
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def load_config(path: str, default: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Load configuration from a YAML file.
    
    Args:
        path: Path to the YAML config file
        default: Default value to return on error (default: empty dict)
        
    Returns:
        Parsed config dict, or default on error
    """
    if default is None:
        default = {}
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f) or default
    except FileNotFoundError:
        logger.warning(f"Config file not found: {path}")
        return default
    except yaml.YAMLError as e:
        logger.warning(f"Error parsing YAML {path}: {e}")
        return default
    except Exception as e:
        logger.warning(f"Could not load config from {path}: {e}")
        return default
