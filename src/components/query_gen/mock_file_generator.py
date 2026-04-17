"""
MicroSnippetGenerator — Generates representative atomic source snippets for a framework via LLM.

Detects invalid framework/language names from the LLM response and raises
immediately to prevent wasted pipeline execution.
"""

from typing import List, Dict, Any
import re
from haystack import component
from haystack.dataclasses import ChatMessage

from src.utils.model_generator import ModelGenerator
from src.utils.logger import DocGenLogger
from prompts.query_generation_prompts import (
    micro_snippet_system_prompt,
    micro_snippet_user_prompt,
)

logger = DocGenLogger(__name__)


@component
class MicroSnippetGenerator:
    """Generates exhaustive atomic source snippets for a given framework via LLM."""

    def __init__(self, config_path: str = "config.yaml"):
        self.generator = ModelGenerator(
            "query_generator", config_path
        ).get_generator()

    @component.output_types(snippets=List[Dict[str, str]])
    def run(
        self, framework_name: str, language: str
    ) -> Dict[str, List[Dict[str, str]]]:
        messages = [
            ChatMessage.from_system(micro_snippet_system_prompt),
            ChatMessage.from_user(
                micro_snippet_user_prompt.substitute(
                    framework_name=framework_name,
                    language=language,
                )
            ),
        ]

        response = self.generator.run(messages=messages)["replies"][0]
        text = response.text if hasattr(response, "text") else str(response)

        if "<error>" in text:
            raise ValueError(
                f"Invalid framework or language: "
                f"framework={framework_name}, "
                f"language={language}. "
                f"LLM response indicated invalid request."
            )

        snippets = []
        pattern = r'<snippet\s+type="([^"]+)">\s*(.*?)\s*</snippet>'
        for i, match in enumerate(re.finditer(pattern, text, re.DOTALL)):
            snippets.append({
                "filename": f"snippet_{i}.ext",
                "file_type": match.group(1),
                "content": match.group(2)
            })

        if not snippets:
            raise ValueError(
                f"LLM returned no micro-snippets for {framework_name}/{language}"
            )

        logger.info(
            f"Generated {len(snippets)} micro-snippets for {framework_name}/{language}",
            location="MicroSnippetGenerator.run",
        )

        return {"snippets": snippets}
