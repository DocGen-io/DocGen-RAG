"""
Base abstract class for output format builders.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class OutputFormatBuilder(ABC):
    """Abstract base class for output format builders."""
    
    @abstractmethod
    def build(self, endpoints: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build the output format from a list of endpoint data.
        
        Args:
            endpoints: List of dicts with 'method_name', 'data', and optionally 'http_method'
            
        Returns:
            Complete output format as dictionary
        """
        pass
    
    @abstractmethod
    def validate(self, output: Dict[str, Any]) -> bool:
        """
        Validate the generated output.
        
        Args:
            output: Generated output dictionary
            
        Returns:
            True if valid, False otherwise
        """
        pass
