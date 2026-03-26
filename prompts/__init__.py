

from .docCreatorPrompt import doc_creator_system_prompt, doc_creator_user_prompt
from .filesAnalyzerPrompt import default_analyzer_system_prompt, file_analyzer_user_prompt, get_file_analyzer_system_prompt
from .fetchExamplePrompt import fetch_example_system_prompt, fetch_example_user_prompt

from string import Template as _Template
doc_creator_prompt = _Template(doc_creator_system_prompt)
file_analyzer_prompt = _Template(default_analyzer_system_prompt)
fetch_example_prompt = _Template(fetch_example_system_prompt)

# Alias so `from prompts import file_analyzer_system_prompt` works
file_analyzer_system_prompt = default_analyzer_system_prompt

__all__ = [
    "doc_creator_system_prompt",
    "doc_creator_user_prompt",
    "default_analyzer_system_prompt",
    "file_analyzer_system_prompt",
    "file_analyzer_user_prompt",
    "fetch_example_system_prompt",
    "fetch_example_user_prompt",
    "doc_creator_prompt",
    "file_analyzer_prompt",
    "fetch_example_prompt",
    "get_file_analyzer_system_prompt",
]
