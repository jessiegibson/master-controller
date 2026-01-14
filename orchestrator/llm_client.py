"""
LLM Client for Claude API

Handles all interactions with the Claude API, including:
- Message creation
- Token counting
- Error handling and retries
- Response streaming (future)
"""

import os
from typing import Optional, Dict, Any
from anthropic import Anthropic
import time


class LLMClient:
    """Client for interacting with Claude API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ):
        """Initialize LLM client.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Claude model to use
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment or provided")

        self.client = Anthropic(api_key=self.api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def create_message(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Create a message with Claude.

        Args:
            system_prompt: System prompt (agent identity + instructions)
            user_message: User message (task + context)
            max_tokens: Override default max_tokens
            temperature: Override default temperature

        Returns:
            Dict with:
                - content: Response text
                - usage: Token usage stats
                - model: Model used
                - stop_reason: Why generation stopped
        """
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens or self.max_tokens,
            temperature=temperature or self.temperature,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )

        return {
            "content": response.content[0].text,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            "model": response.model,
            "stop_reason": response.stop_reason,
        }

    def create_message_with_retry(
        self,
        system_prompt: str,
        user_message: str,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        **kwargs
    ) -> Dict[str, Any]:
        """Create message with exponential backoff retry.

        Args:
            system_prompt: System prompt
            user_message: User message
            max_retries: Maximum retry attempts
            initial_delay: Initial delay in seconds
            **kwargs: Additional arguments for create_message

        Returns:
            Response dict from create_message

        Raises:
            Exception: If all retries exhausted
        """
        delay = initial_delay
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                return self.create_message(system_prompt, user_message, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    print(f"API call failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
                    print(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    raise Exception(f"Failed after {max_retries + 1} attempts: {e}") from last_error

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count for text.

        Rough estimate: ~4 characters per token for English text.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        return len(text) // 4
