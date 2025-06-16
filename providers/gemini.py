"""Gemini model provider implementation."""

import base64
import logging
import os
import time
from typing import Optional

from google import genai
from google.genai import types

from .base import ModelCapabilities, ModelProvider, ModelResponse, ProviderType, RangeTemperatureConstraint

logger = logging.getLogger(__name__)


class GeminiModelProvider(ModelProvider):
    """Google Gemini model provider implementation."""

    # Model configurations
    SUPPORTED_MODELS = {
        "gemini-2.5-flash-preview-05-20": {
            "context_window": 1_048_576,  # 1M tokens
            "supports_extended_thinking": True,
            "max_thinking_tokens": 24576,  # Flash 2.5 thinking budget limit
            "supports_images": True,  # Vision capability
            "max_image_size_mb": 20.0,  # Conservative 20MB limit for reliability
        },
        "gemini-2.5-pro-preview-06-05": {
            "context_window": 1_048_576,  # 1M tokens
            "supports_extended_thinking": True,
            "max_thinking_tokens": 32768,  # Pro 2.5 thinking budget limit
            "supports_images": True,  # Vision capability
            "max_image_size_mb": 32.0,  # Higher limit for Pro model
        },
        # Shorthands
        "flash": "gemini-2.5-flash-preview-05-20",
        "pro": "gemini-2.5-pro-preview-06-05",
    }

    # Thinking mode configurations - percentages of model's max_thinking_tokens
    # These percentages work across all models that support thinking
    THINKING_BUDGETS = {
        "minimal": 0.005,  # 0.5% of max - minimal thinking for fast responses
        "low": 0.08,  # 8% of max - light reasoning tasks
        "medium": 0.33,  # 33% of max - balanced reasoning (default)
        "high": 0.67,  # 67% of max - complex analysis
        "max": 1.0,  # 100% of max - full thinking budget
    }

    def __init__(self, api_key: str, **kwargs):
        """Initialize Gemini provider with API key."""
        super().__init__(api_key, **kwargs)
        self._client = None
        self._token_counters = {}  # Cache for token counting

    @property
    def client(self):
        """Lazy initialization of Gemini client."""
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        """Get capabilities for a specific Gemini model."""
        # Resolve shorthand
        resolved_name = self._resolve_model_name(model_name)

        if resolved_name not in self.SUPPORTED_MODELS:
            raise ValueError(f"Unsupported Gemini model: {model_name}")

        # Check if model is allowed by restrictions
        from utils.model_restrictions import get_restriction_service

        restriction_service = get_restriction_service()
        # IMPORTANT: Parameter order is (provider_type, model_name, original_name)
        # resolved_name is the canonical model name, model_name is the user input
        if not restriction_service.is_allowed(ProviderType.GOOGLE, resolved_name, model_name):
            raise ValueError(f"Gemini model '{resolved_name}' is not allowed by restriction policy.")

        config = self.SUPPORTED_MODELS[resolved_name]

        # Gemini models support 0.0-2.0 temperature range
        temp_constraint = RangeTemperatureConstraint(0.0, 2.0, 0.7)

        return ModelCapabilities(
            provider=ProviderType.GOOGLE,
            model_name=resolved_name,
            friendly_name="Gemini",
            context_window=config["context_window"],
            supports_extended_thinking=config["supports_extended_thinking"],
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_images=config.get("supports_images", False),
            max_image_size_mb=config.get("max_image_size_mb", 0.0),
            temperature_constraint=temp_constraint,
        )

    def generate_content(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        thinking_mode: str = "medium",
        images: Optional[list[str]] = None,
        **kwargs,
    ) -> ModelResponse:
        """Generate content using Gemini model."""
        # Validate parameters
        resolved_name = self._resolve_model_name(model_name)
        self.validate_parameters(model_name, temperature)

        # Prepare content parts (text and potentially images)
        parts = []

        # Add system and user prompts as text
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        else:
            full_prompt = prompt

        parts.append({"text": full_prompt})

        # Add images if provided and model supports vision
        if images and self._supports_vision(resolved_name):
            for image_path in images:
                try:
                    image_part = self._process_image(image_path)
                    if image_part:
                        parts.append(image_part)
                except Exception as e:
                    logger.warning(f"Failed to process image {image_path}: {e}")
                    # Continue with other images and text
                    continue
        elif images and not self._supports_vision(resolved_name):
            logger.warning(f"Model {resolved_name} does not support images, ignoring {len(images)} image(s)")

        # Create contents structure
        contents = [{"parts": parts}]

        # Prepare generation config
        generation_config = types.GenerateContentConfig(
            temperature=temperature,
            candidate_count=1,
        )

        # Add max output tokens if specified
        if max_output_tokens:
            generation_config.max_output_tokens = max_output_tokens

        # Add thinking configuration for models that support it
        capabilities = self.get_capabilities(model_name)
        if capabilities.supports_extended_thinking and thinking_mode in self.THINKING_BUDGETS:
            # Get model's max thinking tokens and calculate actual budget
            model_config = self.SUPPORTED_MODELS.get(resolved_name)
            if model_config and "max_thinking_tokens" in model_config:
                max_thinking_tokens = model_config["max_thinking_tokens"]
                actual_thinking_budget = int(max_thinking_tokens * self.THINKING_BUDGETS[thinking_mode])
                generation_config.thinking_config = types.ThinkingConfig(thinking_budget=actual_thinking_budget)

        # Retry logic with progressive delays
        max_retries = 4  # Total of 4 attempts
        retry_delays = [1, 3, 5, 8]  # Progressive delays: 1s, 3s, 5s, 8s

        last_exception = None

        for attempt in range(max_retries):
            try:
                # Generate content
                response = self.client.models.generate_content(
                    model=resolved_name,
                    contents=contents,
                    config=generation_config,
                )

                # Extract usage information if available
                usage = self._extract_usage(response)

                return ModelResponse(
                    content=response.text,
                    usage=usage,
                    model_name=resolved_name,
                    friendly_name="Gemini",
                    provider=ProviderType.GOOGLE,
                    metadata={
                        "thinking_mode": thinking_mode if capabilities.supports_extended_thinking else None,
                        "finish_reason": (
                            getattr(response.candidates[0], "finish_reason", "STOP") if response.candidates else "STOP"
                        ),
                    },
                )

            except Exception as e:
                last_exception = e

                # Check if this is a retryable error
                error_str = str(e).lower()
                is_retryable = any(
                    term in error_str
                    for term in [
                        "timeout",
                        "connection",
                        "network",
                        "temporary",
                        "unavailable",
                        "retry",
                        "429",
                        "500",
                        "502",
                        "503",
                        "504",
                    ]
                )

                # If this is the last attempt or not retryable, give up
                if attempt == max_retries - 1 or not is_retryable:
                    break

                # Get progressive delay
                delay = retry_delays[attempt]

                # Log retry attempt
                logger.warning(
                    f"Gemini API error for model {resolved_name}, attempt {attempt + 1}/{max_retries}: {str(e)}. Retrying in {delay}s..."
                )
                time.sleep(delay)

        # If we get here, all retries failed
        error_msg = f"Gemini API error for model {resolved_name} after {max_retries} attempts: {str(last_exception)}"
        raise RuntimeError(error_msg) from last_exception

    def count_tokens(self, text: str, model_name: str) -> int:
        """Count tokens for the given text using Gemini's tokenizer."""
        self._resolve_model_name(model_name)

        # For now, use a simple estimation
        # TODO: Use actual Gemini tokenizer when available in SDK
        # Rough estimation: ~4 characters per token for English text
        return len(text) // 4

    def get_provider_type(self) -> ProviderType:
        """Get the provider type."""
        return ProviderType.GOOGLE

    def validate_model_name(self, model_name: str) -> bool:
        """Validate if the model name is supported and allowed."""
        resolved_name = self._resolve_model_name(model_name)

        # First check if model is supported
        if resolved_name not in self.SUPPORTED_MODELS or not isinstance(self.SUPPORTED_MODELS[resolved_name], dict):
            return False

        # Then check if model is allowed by restrictions
        from utils.model_restrictions import get_restriction_service

        restriction_service = get_restriction_service()
        # IMPORTANT: Parameter order is (provider_type, model_name, original_name)
        # resolved_name is the canonical model name, model_name is the user input
        if not restriction_service.is_allowed(ProviderType.GOOGLE, resolved_name, model_name):
            logger.debug(f"Gemini model '{model_name}' -> '{resolved_name}' blocked by restrictions")
            return False

        return True

    def supports_thinking_mode(self, model_name: str) -> bool:
        """Check if the model supports extended thinking mode."""
        capabilities = self.get_capabilities(model_name)
        return capabilities.supports_extended_thinking

    def get_thinking_budget(self, model_name: str, thinking_mode: str) -> int:
        """Get actual thinking token budget for a model and thinking mode."""
        resolved_name = self._resolve_model_name(model_name)
        model_config = self.SUPPORTED_MODELS.get(resolved_name, {})

        if not model_config.get("supports_extended_thinking", False):
            return 0

        if thinking_mode not in self.THINKING_BUDGETS:
            return 0

        max_thinking_tokens = model_config.get("max_thinking_tokens", 0)
        if max_thinking_tokens == 0:
            return 0

        return int(max_thinking_tokens * self.THINKING_BUDGETS[thinking_mode])

    def _resolve_model_name(self, model_name: str) -> str:
        """Resolve model shorthand to full name."""
        # Check if it's a shorthand
        shorthand_value = self.SUPPORTED_MODELS.get(model_name.lower())
        if isinstance(shorthand_value, str):
            return shorthand_value
        return model_name

    def _extract_usage(self, response) -> dict[str, int]:
        """Extract token usage from Gemini response."""
        usage = {}

        # Try to extract usage metadata from response
        # Note: The actual structure depends on the SDK version and response format
        if hasattr(response, "usage_metadata"):
            metadata = response.usage_metadata
            if hasattr(metadata, "prompt_token_count"):
                usage["input_tokens"] = metadata.prompt_token_count
            if hasattr(metadata, "candidates_token_count"):
                usage["output_tokens"] = metadata.candidates_token_count
            if "input_tokens" in usage and "output_tokens" in usage:
                usage["total_tokens"] = usage["input_tokens"] + usage["output_tokens"]

        return usage

    def _supports_vision(self, model_name: str) -> bool:
        """Check if the model supports vision (image processing)."""
        # Gemini 2.5 models support vision
        vision_models = {
            "gemini-2.5-flash-preview-05-20",
            "gemini-2.5-pro-preview-06-05",
            "gemini-2.0-flash",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        }
        return model_name in vision_models

    def _process_image(self, image_path: str) -> Optional[dict]:
        """Process an image for Gemini API."""
        try:
            if image_path.startswith("data:image/"):
                # Handle data URL: data:image/png;base64,iVBORw0...
                header, data = image_path.split(",", 1)
                mime_type = header.split(";")[0].split(":")[1]
                return {"inline_data": {"mime_type": mime_type, "data": data}}
            else:
                # Handle file path - translate for Docker environment
                from utils.file_types import get_image_mime_type
                from utils.file_utils import translate_path_for_environment

                translated_path = translate_path_for_environment(image_path)
                logger.debug(f"Translated image path from '{image_path}' to '{translated_path}'")

                if not os.path.exists(translated_path):
                    logger.warning(f"Image file not found: {translated_path} (original: {image_path})")
                    return None

                # Use translated path for all subsequent operations
                image_path = translated_path

                # Detect MIME type from file extension using centralized mappings
                ext = os.path.splitext(image_path)[1].lower()
                mime_type = get_image_mime_type(ext)

                # Read and encode the image
                with open(image_path, "rb") as f:
                    image_data = base64.b64encode(f.read()).decode()

                return {"inline_data": {"mime_type": mime_type, "data": image_data}}
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            return None
