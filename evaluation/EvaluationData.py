from dataclasses import dataclass
from typing import Optional

@dataclass
class EvaluationRecord:
    model: str
    language: str
    framework: str
    repo_url: str
    success: bool
    execution_time_seconds: float
    valid_openapi: bool
    files_processed: int
    error: Optional[str] = None
    expected_paths_count: Optional[int] = None
    generated_paths_count: Optional[int] = None
    path_match_count: Optional[int] = None
    path_recall: Optional[float] = None
    path_precision: Optional[float] = None
    expected_methods_count: Optional[int] = None
    generated_methods_count: Optional[int] = None
    method_match_count: Optional[int] = None
    method_recall: Optional[float] = None
    method_precision: Optional[float] = None
