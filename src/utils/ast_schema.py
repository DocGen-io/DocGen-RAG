"""
AST Schema - Pydantic models for validating AST extractor output.

All language extractors must produce output conforming to these schemas.
This ensures consistency across TypeScript, Java, Python, C# and future language support.
"""

from typing import List, Optional
from pydantic import BaseModel, field_validator


class ASTMethodSchema(BaseModel):
    """Schema for a single method in AST output."""
    method_name: str
    method_type: Optional[str] = None
    is_api_route: bool
    method_path: Optional[str] = None
    method_definition: str
    
    @field_validator('method_name')
    @classmethod
    def method_name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('method_name cannot be empty')
        return v


class ASTClassSchema(BaseModel):
    """Schema for a class/module in AST output."""
    class_name: Optional[str] = None
    class_type: Optional[str] = None
    base_path: Optional[str] = "/"
    methods: List[ASTMethodSchema]
    file_name: Optional[str] = None


def validate_ast_output(data: List[dict]) -> List[ASTClassSchema]:
    """
    Validate AST output against schema.
    
    Args:
        data: List of class dictionaries from AST extractor
        
    Returns:
        List of validated ASTClassSchema objects
        
    Raises:
        pydantic.ValidationError: If data doesn't match schema
    """
    return [ASTClassSchema(**cls) for cls in data]
