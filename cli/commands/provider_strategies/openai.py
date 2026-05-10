from cli.core import console, secrets
from cli.commands.provider_strategies.base import ProviderStrategy


class OpenAIStrategy(ProviderStrategy):
    def setup(self) -> None:
        """Credential setup for OpenAI."""
        console.print_header("OpenAI Setup")

        console.print_step(
            "OpenAI requires an API key tied to your own OpenAI account. "
            "This ensures API usage is billed to your personal limits."
        )
        console.print_step(
            "Get your API key here: https://platform.openai.com/api-keys"
        )
        console.print_step("")

        api_key = console.password("OpenAI API key:")
        secrets.store("openai_api_key", api_key)

        console.print_success("OpenAI API key stored securely.")

    def inject(self, config_dict: dict) -> None:
        """Inject OpenAI API key secret into generators.openai config dynamically."""
        openai_api_key = secrets.retrieve("openai_api_key")
        if "generators" not in config_dict:
            config_dict["generators"] = {}
        if "openai" not in config_dict["generators"]:
            config_dict["generators"]["openai"] = {}
        if openai_api_key:
            config_dict["generators"]["openai"]["api_key"] = openai_api_key
