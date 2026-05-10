from abc import ABC, abstractmethod


class ProviderStrategy(ABC):
    """Abstract base class for AI provider credential setup and configuration injection strategies."""

    @abstractmethod
    def setup(self) -> None:
        """Execute the credential setup flow."""
        pass

    @abstractmethod
    def inject(self, config_dict: dict) -> None:
        """Inject required credentials dynamically into config_dict."""
        pass
