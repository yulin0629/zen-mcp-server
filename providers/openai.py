"""OpenAI model provider implementation."""

from .base import (
    FixedTemperatureConstraint,
    ModelCapabilities,
    ProviderType,
    RangeTemperatureConstraint,
)
from .openai_compatible import OpenAICompatibleProvider


class OpenAIModelProvider(OpenAICompatibleProvider):
    """Official OpenAI API provider (api.openai.com)."""

    # Model configurations
    SUPPORTED_MODELS = {
        "o3": {
            "context_window": 200_000,  # 200K tokens
            "supports_extended_thinking": False,
        },
        "o4-mini": {
            "context_window": 200_000,  # 200K tokens
            "supports_extended_thinking": False,
        },
    }

    def __init__(self, api_key: str, **kwargs):
        """Initialize OpenAI provider with API key."""
        # Set default OpenAI base URL, allow override for regions/custom endpoints
        kwargs.setdefault("base_url", "https://api.openai.com/v1")
        super().__init__(api_key, **kwargs)

    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        """Get capabilities for a specific OpenAI model."""
        if model_name not in self.SUPPORTED_MODELS:
            raise ValueError(f"Unsupported OpenAI model: {model_name}")

        config = self.SUPPORTED_MODELS[model_name]

        # Define temperature constraints per model
        if model_name in ["o3", "o4-mini"]:
            # O3 models only support temperature=1.0
            temp_constraint = FixedTemperatureConstraint(1.0)
        else:
            # Other OpenAI models support 0.0-2.0 range
            temp_constraint = RangeTemperatureConstraint(0.0, 2.0, 0.7)

        return ModelCapabilities(
            provider=ProviderType.OPENAI,
            model_name=model_name,
            friendly_name="OpenAI",
            context_window=config["context_window"],
            supports_extended_thinking=config["supports_extended_thinking"],
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            temperature_constraint=temp_constraint,
        )

    def get_provider_type(self) -> ProviderType:
        """Get the provider type."""
        return ProviderType.OPENAI

    def validate_model_name(self, model_name: str) -> bool:
        """Validate if the model name is supported."""
        return model_name in self.SUPPORTED_MODELS

    def supports_thinking_mode(self, model_name: str) -> bool:
        """Check if the model supports extended thinking mode."""
        # Currently no OpenAI models support extended thinking
        # This may change with future O3 models
        return False
