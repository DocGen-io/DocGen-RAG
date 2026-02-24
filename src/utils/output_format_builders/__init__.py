"""
Output format builders for generating Swagger/OpenAPICollection files.

This module provides abstract and concrete builder classes for creating
valid API documentation output formats from individual endpoint documentation.
"""

from src.utils.output_format_builders.base import OutputFormatBuilder
from src.utils.output_format_builders.swagger_builder import SwaggerBuilder

__all__ = ["OutputFormatBuilder", "SwaggerBuilder"]
