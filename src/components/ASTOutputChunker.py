from haystack import component, Document
from typing import List

@component
class ASTOutputChunker:
    @component.output_types(documents=List[Document])
    def run(self, ast_data_list: List[dict], max_tokens: int = 500):
        all_docs = []
        for ast_data in ast_data_list:
            for chunk in ast_data.get("relevant_chunks", []):
                text = chunk["text"]
                name = chunk["name"]
                
                # Simplified "token" check (e.g., words)
                words = text.split()
                if len(words) > max_tokens:
                    # Split recursively or into fixed windows
                    for i in range(0, len(words), max_tokens):
                        sub_text = " ".join(words[i : i + max_tokens])
                        # Add context prefix to every sub-chunk
                        contextual_text = f"Context: Function {name}\n{sub_text}"
                        
                        all_docs.append(Document(
                            content=contextual_text,
                            meta={
                                "name": name,
                                "type": chunk["type"],
                                "file": ast_data.get("file", "unknown"),
                                "is_sub_chunk": True
                            }
                        ))
                else:
                    all_docs.append(Document(content=text, meta=chunk))
        
        return {"documents": all_docs}