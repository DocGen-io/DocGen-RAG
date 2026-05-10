from cli.core import console, secrets
from cli.commands.provider_strategies.base import ProviderStrategy


class OllamaStrategy(ProviderStrategy):
    def setup(self) -> None:
        """Credential setup for Ollama (local models)."""
        console.print_header("Ollama Setup")

        console.print_step(
            "Ollama allows you to run models entirely on your own local hardware "
            "for maximum privacy and zero API costs. Ensure the Ollama background "
            "service is running before proceeding."
        )
        console.print_step(
            "Download it from: https://ollama.com/"
        )
        console.print_step("")

        url = console.text("Ollama URL:", default="http://127.0.0.1:11434")
        secrets.store("ollama_url", url)

        console.print_success("Ollama configuration stored.")

    def inject(self, config_dict: dict) -> None:
        """Inject Ollama URL secret into generators.ollama config dynamically."""
        ollama_url = secrets.retrieve("ollama_url")
        if "generators" not in config_dict:
            config_dict["generators"] = {}
        if "ollama" not in config_dict["generators"]:
            config_dict["generators"]["ollama"] = {}
        if ollama_url:
            config_dict["generators"]["ollama"]["url"] = ollama_url
