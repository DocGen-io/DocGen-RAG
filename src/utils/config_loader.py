"""Configuration loading utilities."""
import yaml
from src.utils.logger import DocGenLogger
from typing import Dict, Any,List
import os


logger = DocGenLogger(__name__)



def get_config_value(key: List[str], config: Dict[str, Any]) -> Any:
  
    value = None
    for k in key:
        value = config.get(k, None)
        if value is None:
            raise ValueError(f"Key {k} not found in config")
        config = value

    return value
    
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
            raw_content = f.read()
        
        # Expand environment variables on the raw string before parsing YAML   
        expanded_content = os.path.expandvars(raw_content)
        return yaml.safe_load(expanded_content) or default
    except FileNotFoundError:
        logger.warning(f"Config file not found: {path}")
        return default
    except yaml.YAMLError as e:
        logger.warning(f"Error parsing YAML {path}: {e}")
        return default
    except Exception as e:
        logger.warning(f"Could not load config from {path}: {e}")
        return default
