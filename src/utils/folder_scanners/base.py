"""Base folder scanner class."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import os
import logging

logger = logging.getLogger(__name__)


class FolderScanner(ABC):
    """Abstract base class for folder scanning operations."""
    
    def scan(self, folder_path: str) -> List[Dict[str, Any]]:
        """
        Scan a folder and return processed items.
        
        Args:
            folder_path: Path to folder to scan
            
        Returns:
            List of processed item dictionaries
        """
        if not os.path.exists(folder_path):
            logger.warning(f"Folder does not exist: {folder_path}")
            return []
        
        if not os.path.isdir(folder_path):
            logger.warning(f"Path is not a directory: {folder_path}")
            return []
        
        results = []
        for name in sorted(os.listdir(folder_path)):
            item_path = os.path.join(folder_path, name)
            if self._is_valid_item(item_path, name):
                item = self._process_item(item_path, name)
                if item is not None:
                    results.append(item)
        
        logger.info(f"Scanned {len(results)} items from {folder_path}")
        return results
    
    @abstractmethod
    def _is_valid_item(self, path: str, name: str) -> bool:
        """Check if an item should be processed."""
        pass
    
    @abstractmethod
    def _process_item(self, path: str, name: str) -> Dict[str, Any]:
        """Process a single item and return its data."""
        pass
