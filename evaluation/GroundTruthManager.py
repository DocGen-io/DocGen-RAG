import os
import json
import requests
from typing import Optional, Dict, Any
from src.utils.logger import DocGenLogger

logger = DocGenLogger(__name__)

class GroundTruthManager:
    """Manages fetching and loading of the ground truth swagger.json"""
    
    def __init__(self, download_dir: str = "evaluation/ground_truths"):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)
        
    def get_ground_truth(self, url: str, language: str) -> Optional[Dict[str, Any]]:
        """
        Dynamically downloads the ground truth OpenAPI spec from the provided URL.
        Caches it locally to prevent redundant network requests.
        """
        if not url:
            logger.warning(
                f"No ground truth URL provided for language block '{language}'. Accuracy metrics will be skipped.",
                location="GroundTruthManager.get_ground_truth"
            )
            return None
            
        filename = f"ground_truth_{language}.json"
        filepath = os.path.join(self.download_dir, filename)
        
        # If the file already exists, we load it instead of hitting the network.
        if os.path.exists(filepath):
            logger.info(f"Loaded cached ground truth for {language} from {filepath}", location="GroundTruthManager.get_ground_truth")
            with open(filepath, 'r') as f:
                return json.load(f)
                
        # The file doesn't exist yet, we must download it.
        logger.info(f"File {filepath} not found locally. Downloading ground truth for {language} from '{url}'...", location="GroundTruthManager.get_ground_truth")
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            # Check if the URL is a YAML file
            if url.lower().endswith(('.yaml', '.yml')):
                import yaml
                data = yaml.safe_load(response.text)
            else:
                data = response.json()
            
            # Save it so we don't need to download it again next time
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
                
            return data
        except requests.exceptions.JSONDecodeError:
            logger.error(
                f"Failed to parse JSON from {url}. Ensure the link points to a RAW JSON/YAML file (e.g. raw.githubusercontent.com), not an HTML page.",
                location="GroundTruthManager.get_ground_truth"
            )
            return None
        except Exception as e:
            logger.error(f"Failed to download or parse ground truth from {url}: {e}", location="GroundTruthManager.get_ground_truth")
            return None


