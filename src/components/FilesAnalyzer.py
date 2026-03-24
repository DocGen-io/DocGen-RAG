import os
import json
from typing import List, Dict, Any, Optional, Set
from haystack import component
from haystack.dataclasses import ChatMessage
from src.utils.logger import DocGenLogger
from src.utils.config_loader import load_config
from src.utils.llm_json_handler import LLMJsonHandler
from src.utils.modelGenerator import ModelGenerator
from src.utils.weaviate_utils import fetch_by_keyword, fetch_by_node_id
from haystack_integrations.document_stores.weaviate import WeaviateDocumentStore
from prompts.filesAnalyzerPrompt import get_file_analyzer_system_prompt, file_analyzer_user_prompt

logger = DocGenLogger(__name__)

@component
class FilesAnalyzer:
    """
    Analyzes endpoints using an LLM to recursively discover dependencies.
    For each discovered dependency, it queries Weaviate to fetch its code chunk,
    and analyzes it again to find deep dependencies up to a maximum depth.
    """
    
    def __init__(
        self,
        weaviate_url: str = "http://127.0.0.1:8080",
        config_path: str = "config.yaml",
        max_depth: int = 3
    ):
        self.config = load_config(config_path)
        self.max_depth = max_depth
        
        # Use the 'code_analyzer' model config
        self.generator = ModelGenerator("code_analyzer", config_path).get_generator()
        self.weaviate_url = weaviate_url

    def _analyze_code(self, file_path: str, code_content: str, language: str, method_name: str) -> List[Dict[str, Any]]:
        """Run the LLM to extract dependencies from a code string."""
        sys_prompt = get_file_analyzer_system_prompt(language)
        usr_prompt = file_analyzer_user_prompt.substitute(
            query_data_file_path=file_path,
            method_name=method_name,
            query_data_file_content=code_content
        )
        
        messages = [
            ChatMessage.from_system(sys_prompt),
            ChatMessage.from_user(usr_prompt)
        ]
        
        # The LLM outputs a dict with "content" array
        result = LLMJsonHandler.parse_with_retry(generator=self.generator, prompt=messages, max_retries=2)
        if not result or "content" not in result:
            return []
            
        return result.get("content", [])

    def _fetch_dependency_code(self, dependency_origin: str, dependency_name: str, current_path: str, current_code: str) -> tuple[Optional[str], str, str]:
        """Fetch the code, file path, and Weaviate node_id of a dependency."""
        search_query = f"{dependency_origin} {dependency_name}" if dependency_origin else dependency_name
        
        # We fetch a configured top_k matches to ensure the true dependency is captured 
        # even if BM25 scores the caller or other irrelevant files higher.
        top_k = self.config.get("code_analyzer", {}).get("dependency_search_top_k", 100)
        docs = fetch_by_keyword(self.document_store, search_query, top_k=top_k)
        if not docs:
            return None, "", ""
            
        # 1. First pass: look for a match in a completely DIFFERENT file that isn't the caller's code.
        for doc in docs:
            if doc.content.strip() == current_code.strip():
                continue
                
            doc_path = doc.meta.get("file_path", "")
            if doc_path.strip() != current_path.strip():
                return doc.content, doc_path, doc.meta.get("node_id", "")
                
        # 2. Second pass (Fallback): If no matches in other files were found, the dependency might be 
        # in the exact same file (e.g. a local helper function). Just return the first chunk that 
        # isn't exactly the caller's chunk.
        for doc in docs:
            if doc.content.strip() != current_code.strip():
                return doc.content, doc.meta.get("file_path", ""), doc.meta.get("node_id", "")
                
        # 3. Absolute fallback (everything was identical to caller for some reason)
        return docs[0].content, docs[0].meta.get("file_path", ""), docs[0].meta.get("node_id", "")

    @component.output_types(endpoints=List[Dict[str, Any]])
    def run(
        self,
        endpoints: List[Dict[str, Any]],
        project_name: str = "",
        wait_for_weaviate: Optional[int] = None,
        working_dir: str = ""
    ) -> Dict[str, Any]:
        """
        Recursively analyzes endpoints and their dependencies.
        Returns the updated endpoints list where each endpoint has a fully 
        populated 'dependencies' list containing all deep dependencies.
        """
        if not endpoints:
            return {"endpoints": []}

        logger.info(f"FilesAnalyzer: Recursively analyzing {len(endpoints)} endpoints")
        
        from src.utils.weaviate_utils import get_weaviate_store
        
        with get_weaviate_store(url=self.weaviate_url) as self.document_store:
            for ep in endpoints:
                method_name = ep.get("method_name", "ENDPOINT")
                fallback_code = ep.get("method_definition", "")
                if not fallback_code:
                    continue
                    
                file_path = ep.get("file_path", "unknown")
                ext = os.path.splitext(file_path)[1].lower()
                language = "java" if ext == ".java" else "typescript" if ext == ".ts" else "c#" if ext == ".cs" else "python"
                
                # Try to load the full file. If it fails, fallback to the method code
                try:
                    abs_path = os.path.join(working_dir, file_path) if working_dir and not os.path.isabs(file_path) else file_path
                    if os.path.exists(abs_path):
                        with open(abs_path, "r", encoding="utf-8") as f:
                            endpoint_code = f.read()
                    else:
                        endpoint_code = fallback_code
                except Exception:
                    endpoint_code = fallback_code
                
                visited: Set[str] = set()
                all_discovered_deps: List[Dict[str, Any]] = []
                
                # queue tuples: (dependency_name, current_code, current_depth, current_file_path, current_method_name)
                queue = [(method_name, endpoint_code, 0, file_path, method_name)]
                
                while queue:
                    current_name, current_code, current_depth, current_path, current_method_name = queue.pop(0)
                    
                    if current_name in visited:
                        continue
                    visited.add(current_name)
                    
                    # Analyze the current code piece
                    analysis_results = self._analyze_code(current_path, current_code, language, current_method_name)
                    
                    for item in analysis_results:
                        deps = item.get("dependencies", [])
                        for d in deps:
                            dep_name = d.get("dependency_name")
                            if not dep_name or dep_name in visited:
                                continue
                                
                            dep_origin = d.get("dependency_origin", "")
                            dep_chunk_code, dep_file_path, dep_node_id = self._fetch_dependency_code(dep_origin, dep_name, current_path, current_code)
                            if dep_node_id:
                                d["target_node_id"] = dep_node_id
                                
                            # Add to the endpoint's discovered dependencies
                            all_discovered_deps.append(d)
                            
                            # Fetch its code and add to queue if we haven't reached max depth
                            if current_depth < self.max_depth and dep_chunk_code:
                                # Try to load full file for the dependency
                                dep_full_code = dep_chunk_code
                                try:
                                    dep_file_path = dep_file_path or ""
                                    dep_abs_path = os.path.join(working_dir, dep_file_path) if working_dir and not os.path.isabs(dep_file_path) else dep_file_path
                                    if dep_abs_path and os.path.exists(dep_abs_path):
                                        with open(dep_abs_path, "r", encoding="utf-8") as f:
                                            dep_full_code = f.read()
                                except Exception:
                                    pass
                                queue.append((dep_name, dep_full_code, current_depth + 1, dep_file_path or current_path, dep_name))
                                    
                # Attach all fully resolved dependencies back to the endpoint
                ep["dependencies"] = all_discovered_deps

        return {"endpoints": endpoints}