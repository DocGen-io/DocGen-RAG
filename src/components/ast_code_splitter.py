"""
ASTCodeSplitter - Haystack component that uses LangChain's tree-sitter
implementation for structural code chunking.

Accepts raw file metadata from FileHasher and produces Haystack Documents
with metadata compatible with Weaviate storage and EndpointGraphManager lookups.
"""
import os
import hashlib
from haystack import component, Document
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from typing import List, Dict, Any

from src.utils.logger import DocGenLogger

logger = DocGenLogger(__name__)

LANG_MAP = {
    "java": Language.JAVA,
    "c_sharp": Language.CSHARP,
    "c#": Language.CSHARP,
    "typescript": Language.TS,
}


@component
class ASTCodeSplitter:
    """
    Haystack component that structurally chunks source code files
    and outputs Haystack Documents ready for Weaviate storage.
    """

    def __init__(self, chunk_size: int = 700, chunk_overlap: int = 70):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def _get_splitter(self, language: str) -> RecursiveCharacterTextSplitter:
        selected_lang = LANG_MAP.get(language.lower())
        if not selected_lang:
            raise ValueError(f"Unsupported language for AST Splitting: {language}")
        return RecursiveCharacterTextSplitter.from_language(
            language=selected_lang,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

    @component.output_types(documents=List[Document])
    def run(self, files: List[Dict[str, str]]) -> Dict[str, List[Document]]:
        """
        Read, split, and package source files into Haystack Documents.

        Args:
            files: List of file dicts from FileHasher (path, language, relative_path).

        Returns:
            documents: List of Document objects with rich metadata for Weaviate.
        """
        split_docs: List[Document] = []

        for file_meta in files:
            file_path = file_meta.get("path", "")
            language = file_meta.get("language", "unknown")
            rel_path = file_meta.get("relative_path", file_path)
            method_name = file_meta.get("method_name", "")
            file_name = os.path.basename(file_path)

            if language.lower() not in LANG_MAP:
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()
            except Exception as e:
                logger.warning(f"Could not read {file_path}: {e}")
                continue

            try:
                splitter = self._get_splitter(language)
                chunks = splitter.split_text(code)
            except Exception as e:
                logger.error(f"Splitting failed for {file_path}: {e}")
                continue

            for i, chunk in enumerate(chunks):
                # Build a node_id that is filterable: file_name:code_chunk:<index>
                node_id = f"{file_name}:code_chunk:{i}:{method_name}"
                doc_id = hashlib.sha256(node_id.encode()).hexdigest()

                doc = Document(
                    id=doc_id,
                    content=chunk,
                    meta={
                        "type": "code_chunk",
                        "node_id": node_id,
                        "file_path": rel_path,
                        "file_name": file_name,
                        "language": language,
                        "chunk_index": i,
                        "is_structural_chunk": True,
                        "method_name": method_name,
                    },
                )
                split_docs.append(doc)

        logger.info(
            f"ASTCodeSplitter produced {len(split_docs)} chunks from {len(files)} files",
            location="ASTCodeSplitter.run",
        )
        return {"documents": split_docs}
