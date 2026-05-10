from cli.commands.provider_strategies.base import ProviderStrategy
from cli.commands.provider_strategies.gemini import GeminiStrategy
from cli.commands.provider_strategies.openai import OpenAIStrategy
from cli.commands.provider_strategies.ollama import OllamaStrategy

STRATEGIES: dict[str, type[ProviderStrategy]] = {
    "gemini": GeminiStrategy,
    "openai": OpenAIStrategy,
    "ollama": OllamaStrategy,
}
