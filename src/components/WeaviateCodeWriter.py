"""
WeaviateCodeWriter - Haystack component to store AST and code mapper data in Weaviate.

This component reads AST JSON files and mapped_ast.json, and stores
the data in Weaviate for semantic search and retrieval.

The AST data is saved exactly as extracted by the base_extractor,
which already includes file_name, class_name, and trimmed method_definition.
"""

from haystack import component, Document
from haystack.components.writers import DocumentWriter
from haystack.components.embedders import SentenceTransformersDocumentEmbedder
from haystack_integrations.document_stores.weaviate import WeaviateDocumentStore
from typing import List, Dict, Any, Optional
import logging

from src.utils.json_loader import load_json_file, flatten_ast_methods
from src.utils.folder_scanners import ASTFolderScanner

logger = logging.getLogger(__name__)


@component
class WeaviateCodeWriter:
    """
    Haystack component that writes AST method data and code mapper dependencies
    to Weaviate document store.
    
    Usage:
        writer = WeaviateCodeWriter(weaviate_url="http://localhost:8080")
        result = writer.run(
            ast_folder="./ast",
            mapped_ast_path="./mapped_ast.json"
        )
    """
    
    def __init__(
        self,
        weaviate_url: str = "http://127.0.0.1:8080",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        additional_headers: Optional[Dict[str, str]] = None
    ):
        """
        Initialize the WeaviateCodeWriter component.
        
        Args:
            weaviate_url: URL of the Weaviate instance
            embedding_model: Model to use for generating embeddings
            additional_headers: Optional headers for Weaviate (e.g., API keys)
        """
        self.weaviate_url = weaviate_url
        self.embedding_model = embedding_model
        self.additional_headers = additional_headers or {}
        
        # Initialize document store
        self.document_store = WeaviateDocumentStore(
            url=weaviate_url,
            additional_headers=self.additional_headers
        )
        
        # Initialize embedder
        self.embedder = SentenceTransformersDocumentEmbedder(model=embedding_model)
        self.embedder.warm_up()
        
        # Initialize writer
        self.writer = DocumentWriter(document_store=self.document_store)
    
    def _ast_methods_to_documents(self, ast_data: List[Dict[str, Any]]) -> List[Document]:
        """
        Convert flattened AST methods to Haystack Documents.
        
        Args:
            ast_data: List of file info dicts from load_json_folder
            
        Returns:
            List of Haystack Document objects
        """
        methods = flatten_ast_methods(ast_data)
        documents = []
        
        for method in methods:
            # Create document content - the method code with context
            class_name = method.get('class_name', 'Unknown')
            method_name = method.get('method_name', 'unknown')
            method_definition = method.get('method_definition', '')
            
            content = f"Class: {class_name}\nMethod: {method_name}\n\n{method_definition}"
            
            # Create document with all method metadata
            doc = Document(
                content=content,
                meta={
                    'type': 'ast_method',
                    'dependencies': [],
                    'dependency_count': 0,
                    **method  # Include all fields from the method
                }
            )
            documents.append(doc)
        
        logger.info(f"Created {len(documents)} documents from AST methods")
        return documents
    
    def _mapped_ast_to_documents(self, mapped_ast: Dict[str, Any]) -> List[Document]:
        """
        Convert mapped_ast.json to Haystack Documents.
        
        Args:
            mapped_ast: Dictionary from mapped_ast.json
            
        Returns:
            List of Haystack Document objects
        """
        documents = []
        
        for class_name, class_data in mapped_ast.items():
            methods = class_data.get('methods', [])
            
            for method_info in methods:
                method_name = method_info.get('method', 'unknown')
                dependencies = method_info.get('dependencies', [])
                
                # Create content summarizing the method dependencies
                deps_str = ', '.join(dependencies) if dependencies else 'None'
                content = f"Class: {class_name}\nMethod: {method_name}\nDependencies: {deps_str}"
                
                # Create document with metadata
                doc = Document(
                    content=content,
                    meta={
                        'type': 'code_mapper',
                        'class_name': class_name,
                        'method_name': method_name,
                        'method_definition': "",   # Default empty
                        'file_name': "",           # Default empty
                        'dependencies': dependencies,
                        'dependency_count': len(dependencies)
                    }
                )
                documents.append(doc)
        
        logger.info(f"Created {len(documents)} documents from code mapper")
        return documents
    
    @component.output_types(
        ast_documents_written=int,
        mapper_documents_written=int,
        total_documents=int
    )
    def run(
        self,
        ast_folder: str = "ast",
        mapped_ast_path: str = "mapped_ast.json",
        ast_data: Optional[List[Dict[str, Any]]] = None,
        mapped_ast: Optional[Dict[str, Any]] = None
    ) -> Dict[str, int]:
        """
        Process AST and mapped_ast and write to Weaviate.
        
        Args:
            ast_folder: (Deprecated) Path to folder containing AST JSON files
            mapped_ast_path: (Deprecated) Path to mapped_ast.json file
            ast_data: Optional list of AST data dictionaries (from ASTExtractor)
            mapped_ast: Optional mapped AST dictionary (from CodeMapper)
            
        Returns:
            Dictionary with counts of documents written
        """
        logger.info(f"Starting WeaviateCodeWriter")
        
        # Load data: Use in-memory if provided, else fall back to files
        ast_files = []
        if ast_data:
            logger.info(f"Using provided in-memory AST data ({len(ast_data)} files)")
            ast_files = ast_data
        elif ast_folder:
            logger.info(f"Scanning AST folder: {ast_folder}")
            ast_files = ASTFolderScanner().scan(ast_folder)
            
        mapped_ast_data = {}
        if mapped_ast:
             logger.info("Using provided in-memory mapped AST")
             mapped_ast_data = mapped_ast
        elif mapped_ast_path:
             logger.info(f"Loading mapped AST from: {mapped_ast_path}")
             mapped_ast_data = load_json_file(mapped_ast_path) or {}
        
        # Process to documents
        ast_documents = self._ast_methods_to_documents(ast_files)
        mapper_documents = self._mapped_ast_to_documents(mapped_ast_data)
        
        # Combine all documents
        all_documents = ast_documents + mapper_documents
        
        if not all_documents:
            logger.warning("No documents to write")
            return {
                "ast_documents_written": 0,
                "mapper_documents_written": 0,
                "total_documents": 0
            }
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(all_documents)} documents...")
        embedded_docs = self.embedder.run(documents=all_documents)
        
        # Write to Weaviate
        logger.info("Writing documents to Weaviate...")
        self.writer.run(documents=embedded_docs['documents'])
        
        result = {
            "ast_documents_written": len(ast_documents),
            "mapper_documents_written": len(mapper_documents),
            "total_documents": len(all_documents)
        }
        
        logger.info(f"Successfully wrote {result['total_documents']} documents to Weaviate")
        return result
