"""Unified LLM provider interface supporting OpenAI and Google Gemini"""

from typing import List, Dict, Any, Optional, Iterator, Callable
from abc import ABC, abstractmethod
import json
import time
from functools import wraps
from loguru import logger


def retry_with_exponential_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0
):
    """
    Decorator to retry a function with exponential backoff on rate limit errors

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff calculation
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_str = str(e)
                    last_exception = e

                    # Check if it's a rate limit error (429)
                    is_rate_limit = (
                        "429" in error_str or
                        "rate limit" in error_str.lower() or
                        "quota exceeded" in error_str.lower() or
                        "ResourceExhausted" in error_str
                    )

                    if not is_rate_limit or attempt == max_retries:
                        # Not a rate limit error or max retries reached
                        raise

                    # Calculate delay with exponential backoff
                    wait_time = min(delay, max_delay)
                    logger.warning(
                        f"Rate limit hit (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {wait_time:.1f}s... Error: {error_str[:100]}"
                    )
                    time.sleep(wait_time)
                    delay *= exponential_base

            # Should never reach here, but just in case
            raise last_exception

        return wrapper
    return decorator


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        """Generate a chat completion"""
        pass
    
    @abstractmethod
    def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None
    ) -> Iterator[str]:
        """Generate a streaming chat completion"""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider"""
    
    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview"):
        """
        Initialize OpenAI provider
        
        Args:
            api_key: OpenAI API key
            model: Model name
        """
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model
        logger.info(f"Initialized OpenAI provider with model: {model}")
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        """Generate a chat completion using OpenAI"""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        
        if response_format:
            kwargs["response_format"] = response_format
        
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
    
    def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None
    ) -> Iterator[str]:
        """Generate a streaming chat completion using OpenAI"""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True
        }
        
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        
        stream = self.client.chat.completions.create(**kwargs)
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider"""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        """
        Initialize Gemini provider
        
        Args:
            api_key: Google API key
            model: Model name
        """
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.model_name = model
        self.client = genai.GenerativeModel(model)
        logger.info(f"Initialized Gemini provider with model: {model}")
    
    def _convert_messages_to_gemini_format(self, messages: List[Dict[str, str]]) -> tuple:
        """
        Convert OpenAI-style messages to Gemini format
        
        Returns:
            Tuple of (system_instruction, conversation_history)
        """
        system_instruction = None
        conversation = []
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "system":
                system_instruction = content
            elif role == "user":
                conversation.append({"role": "user", "parts": [content]})
            elif role == "assistant":
                conversation.append({"role": "model", "parts": [content]})
        
        return system_instruction, conversation
    
    @retry_with_exponential_backoff(max_retries=3, initial_delay=2.0, max_delay=30.0)
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        """Generate a chat completion using Gemini with automatic retry on rate limits"""
        import google.generativeai as genai

        system_instruction, conversation = self._convert_messages_to_gemini_format(messages)

        # Try to use system_instruction if supported, otherwise prepend to first message
        if system_instruction:
            try:
                model = genai.GenerativeModel(
                    self.model_name,
                    system_instruction=system_instruction
                )
            except TypeError as e:
                # system_instruction not supported in this version
                logger.debug(f"system_instruction not supported, prepending to conversation: {e}")
                model = self.client
                # Prepend system instruction to first user message
                if conversation and conversation[0]["role"] == "user":
                    conversation[0]["parts"][0] = f"{system_instruction}\n\n{conversation[0]['parts'][0]}"
        else:
            model = self.client

        generation_config = {
            "temperature": temperature,
        }

        if max_tokens:
            generation_config["max_output_tokens"] = max_tokens

        # Try to set JSON response format for newer Gemini models
        # Add JSON instruction to prompt for better compatibility
        if response_format and response_format.get("type") == "json_object":
            if conversation:
                conversation[-1]["parts"][0] += "\n\nPlease respond with valid JSON only."

        # Try with response_mime_type first (for newer Gemini models)
        try:
            if response_format and response_format.get("type") == "json_object":
                generation_config["response_mime_type"] = "application/json"

            if len(conversation) > 1:
                chat = model.start_chat(history=conversation[:-1])
                response = chat.send_message(
                    conversation[-1]["parts"][0],
                    generation_config=generation_config
                )
            else:
                prompt = conversation[0]["parts"][0] if conversation else ""
                response = model.generate_content(
                    prompt,
                    generation_config=generation_config
                )
        except Exception as e:
            # Fallback: Remove response_mime_type and retry
            if "response_mime_type" in str(e) or "Unknown field" in str(e):
                logger.debug(f"response_mime_type not supported, retrying without it")
                generation_config.pop("response_mime_type", None)

                if len(conversation) > 1:
                    chat = model.start_chat(history=conversation[:-1])
                    response = chat.send_message(
                        conversation[-1]["parts"][0],
                        generation_config=generation_config
                    )
                else:
                    prompt = conversation[0]["parts"][0] if conversation else ""
                    response = model.generate_content(
                        prompt,
                        generation_config=generation_config
                    )
            else:
                raise

        return response.text
    
    @retry_with_exponential_backoff(max_retries=3, initial_delay=2.0, max_delay=30.0)
    def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None
    ) -> Iterator[str]:
        """Generate a streaming chat completion using Gemini with automatic retry on rate limits"""
        import google.generativeai as genai
        
        system_instruction, conversation = self._convert_messages_to_gemini_format(messages)
        
        if system_instruction:
            model = genai.GenerativeModel(
                self.model_name,
                system_instruction=system_instruction
            )
        else:
            model = self.client
        
        generation_config = {
            "temperature": temperature,
        }
        
        if max_tokens:
            generation_config["max_output_tokens"] = max_tokens
        
        if len(conversation) > 1:
            chat = model.start_chat(history=conversation[:-1])
            response = chat.send_message(
                conversation[-1]["parts"][0],
                generation_config=generation_config,
                stream=True
            )
        else:
            prompt = conversation[0]["parts"][0] if conversation else ""
            response = model.generate_content(
                prompt,
                generation_config=generation_config,
                stream=True
            )
        
        for chunk in response:
            if chunk.text:
                yield chunk.text


def create_llm_provider(
    provider: str,
    api_key: str,
    model: str
) -> LLMProvider:
    """
    Factory function to create an LLM provider with automatic model correction

    Args:
        provider: Provider name ('openai' or 'gemini')
        api_key: API key for the provider
        model: Model name (will be auto-corrected if incompatible with provider)

    Returns:
        LLMProvider instance
    """
    provider = provider.lower()

    # Auto-correct model if it doesn't match the provider
    corrected_model = model
    if provider == "openai":
        # If model looks like a Gemini model, use default OpenAI model
        if "gemini" in model.lower():
            corrected_model = "gpt-4o-mini"
            logger.warning(f"Model '{model}' is not compatible with OpenAI. Using '{corrected_model}' instead.")
        return OpenAIProvider(api_key=api_key, model=corrected_model)
    elif provider == "gemini":
        # If model looks like an OpenAI model, use default Gemini model
        if "gpt" in model.lower() or model.startswith("text-"):
            corrected_model = "gemini-2.5-flash"
            logger.warning(f"Model '{model}' is not compatible with Gemini. Using '{corrected_model}' instead.")
        return GeminiProvider(api_key=api_key, model=corrected_model)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}. Supported: openai, gemini")

