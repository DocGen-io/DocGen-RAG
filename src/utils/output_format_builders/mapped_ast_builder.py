"""
Builder for Mapped AST JSON output.
"""

from typing import Dict, Any, List
import json
from src.utils.output_format_builders.base import OutputFormatBuilder

class MappedAstBuilder(OutputFormatBuilder):
    """Builder for mapped AST JSON output format."""
    
    def build(self, mapped_ast_data: Dict[str, Any]) -> Dict[str, Any]:
   
        return mapped_ast_data
    
    def validate(self, output: Dict[str, Any]) -> bool:
      
        return isinstance(output, dict)
    
    def save(self, output: Dict[str, Any], file_path: str) -> None:
      
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)
