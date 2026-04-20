import abc
from typing import Dict, Any

class NamingStrategy(abc.ABC):
    """
    Abstract base class for determining a unique output name
    for documentation generation to prevent filesystem overwrites.
    """
    @abc.abstractmethod
    def generate_name(self, endpoint_id: str, method_info: Dict[str, Any], meta: Dict[str, Any]) -> str:
        """
        Generate a unique storage name.
        """
        pass


class DefaultNamingStrategy(NamingStrategy):
    """
    Default behavior mapping standard REST methods gracefully.
    Used primarily for Typescript, Python, and Java (where naming limits collisions natively).
    """
    def generate_name(self, endpoint_id: str, method_info: Dict[str, Any], meta: Dict[str, Any]) -> str:
        return method_info.get("method_name", "unknown")


class CSharpNamingStrategy(NamingStrategy):
    """
    C# specific behavior due to high chances of redundant generic method names (e.g. 'Get', 'Create').
    Generates an explicit sanitized structure leveraging the endpoint ID.
    """
    def generate_name(self, endpoint_id: str, method_info: Dict[str, Any], meta: Dict[str, Any]) -> str:
        return endpoint_id.replace(":", "_").replace("/", "_").replace("\\", "_")


class NamingStrategyFactory:
    """
    Factory resolving the appropriate NamingStrategy based on endpoint context heuristics.
    """
    @staticmethod
    def get_strategy(endpoint_id: str, meta: Dict[str, Any]) -> NamingStrategy:
        is_csharp = (
            meta.get("file_name", "").endswith(".cs") or 
            meta.get("file_path", "").endswith(".cs") or 
            ".cs:" in endpoint_id.lower()
        )
        
        if is_csharp:
            return CSharpNamingStrategy()
            
        return DefaultNamingStrategy()
