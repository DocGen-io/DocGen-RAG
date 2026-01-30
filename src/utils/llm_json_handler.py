"""
LLM JSON Handler - Utility class for parsing JSON output from LLMs.

Provides robust JSON extraction, repair, and parsing from LLM responses
with retry logic and fallback handling.
"""

import json
import re
import logging
from typing import Optional, Any, Callable

logger = logging.getLogger(__name__)


class LLMJsonHandler:
    """
    Handles JSON parsing from LLM responses with repair and retry capabilities.
    
    Usage:
        handler = LLMJsonHandler()
        result = handler.parse(response)
        
        # With retry using generator
        result = handler.parse_with_retry(response, generator, prompt, max_retries=3)
    """
    
    @staticmethod
    def extract_json(response: str) -> str:
        """
        Extract JSON from LLM response, handling markdown and extra text.
        
        Args:
            response: Raw LLM response string
            
        Returns:
            Extracted JSON string
        """
        response = response.strip()
        
        # Remove markdown code blocks
        response = re.sub(r'^```json\s*', '', response)
        response = re.sub(r'^```\s*', '', response)
        response = re.sub(r'\s*```$', '', response)
        
        # Find JSON object boundaries
        first_brace = response.find('{')
        last_brace = response.rfind('}')
        
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            response = response[first_brace:last_brace + 1]
        
        return response.strip()
    
    @staticmethod
    def repair_json(json_string: str) -> str:
        """
        Attempt to repair common JSON issues from LLM output.
        
        Fixes:
        - Trailing commas before } or ]
        - Unbalanced brackets and braces
        
        Args:
            json_string: Potentially malformed JSON string
            
        Returns:
            Repaired JSON string
        """
        # Remove trailing commas
        json_string = re.sub(r',\s*}', '}', json_string)
        json_string = re.sub(r',\s*]', ']', json_string)
        
        # Balance brackets and braces
        open_braces = json_string.count('{')
        close_braces = json_string.count('}')
        open_brackets = json_string.count('[')
        close_brackets = json_string.count(']')
        
        json_string += ']' * (open_brackets - close_brackets)
        json_string += '}' * (open_braces - close_braces)
        
        return json_string
    
    @classmethod
    def parse(cls, response: str) -> dict:
        """
        Parse JSON from LLM response with extraction and repair.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Parsed JSON as dictionary
            
        Raises:
            json.JSONDecodeError: If parsing fails after repair
        """
        extracted = cls.extract_json(response)
        repaired = cls.repair_json(extracted)
        return json.loads(repaired)
    
    @classmethod
    def parse_with_retry(
        cls,
        response: str,
        generator: Any,
        prompt: str,
        max_retries: int = 2
    ) -> dict:
        """
        Parse JSON with retry logic using LLM generator.
        
        Args:
            response: Initial LLM response
            generator: Haystack generator component
            prompt: Original prompt (for retries)
            max_retries: Number of retry attempts
            
        Returns:
            Parsed JSON dictionary
            
        Raises:
            json.JSONDecodeError: If all attempts fail
        """
        for attempt in range(max_retries + 1):
            try:
                return cls.parse(response)
            except json.JSONDecodeError as e:
                if attempt < max_retries:
                    logger.warning(f"Attempt {attempt + 1}: JSON parse error: {e}, retrying...")
                    response = generator.run(prompt)['replies'][0]
                else:
                    logger.error(f"All {max_retries + 1} attempts failed. Last response: {response[:200]}...")
                    raise
    
    @classmethod
    def safe_parse(
        cls,
        response: str,
        fallback: Optional[dict] = None
    ) -> Optional[dict]:
        """
        Safely parse JSON, returning fallback on failure instead of raising.
        
        Args:
            response: LLM response to parse
            fallback: Value to return on parse failure
            
        Returns:
            Parsed dict or fallback value
        """
        try:
            return cls.parse(response)
        except json.JSONDecodeError:
            return fallback
