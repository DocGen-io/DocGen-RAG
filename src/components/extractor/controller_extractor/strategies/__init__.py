from .base import ExtractorStrategy
from .c_sharp import CSharpStrategy
from .java import JavaStrategy
from .typescript import TypeScriptStrategy

def get_strategy(language_name: str) -> ExtractorStrategy:
    """Factory to get the correct language strategy."""
    if language_name == "c_sharp":
         return CSharpStrategy()
    elif language_name == "java":
         return JavaStrategy()
    elif language_name == "typescript":
         return TypeScriptStrategy()
    # Fallback for languages without specific token resolution needed yet
    return ExtractorStrategy()
