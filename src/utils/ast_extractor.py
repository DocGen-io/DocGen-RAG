import sys
import os
import json
from tree_sitter import Language, Parser
from tree_sitter_language_pack import get_language
from src.components.LanguageFinder import LanguageFinder
from src.services.framework_detector import FrameworkDetector


def get_language_object(language_name):
    return get_language(language_name)


def parse_file(file_path, language_name):
    try:
        lang = get_language_object(language_name)
        if not lang:
            return None, None
            
        parser = Parser(lang)
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
            # Hack for NestJS files with @ts-nocheck to generic parsing
            if language_name == 'typescript' and code.startswith('// @ts-nocheck'):
                 # tree-sitter handles comments fine, so no need to strip, but good to note
                 pass
        tree = parser.parse(bytes(code, 'utf8'))
        return tree, code
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return None, None

def get_node_text(node, code_bytes):
    return code_bytes[node.start_byte:node.end_byte].decode('utf8')

def extract_chunk(node, code_bytes, language, file_name, parent_name=None, file_path=None):
    """
    Extracts a chunk if it matches heuristics.
    Returns dict or None.
    """
    text = get_node_text(node, code_bytes)
    
    # Heuristics
    start_line = node.start_point[0] + 1
    end_line = node.end_point[0] + 1
    
    chunk = {
        "type": node.type,
        "name": "unknown",
        "start_line": start_line,
        "end_line": end_line,
        "text": text,
        "parent_name": parent_name,
        "filepath": file_path,
        "decorators": []
    }

    # Extract Name and Decorators based on language
    # This is a simplified extraction logic
    
    if language == 'python':
        if node.type in ['class_definition', 'function_definition']:
            # name is usually a child with field 'name'
            name_node = node.child_by_field_name('name')
            if name_node:
                chunk['name'] = get_node_text(name_node, code_bytes)
            
            # check decorators (they are usually siblings or part of decorated_definition)
            pass

    if language == 'python' and node.type == 'decorated_definition':
        # Name is not direct child of decorated_definition, need to look into function_definition or class_definition child
        definition_node = node.child_by_field_name('definition')
        if definition_node:
             name_node = definition_node.child_by_field_name('name')
             if name_node:
                 chunk['name'] = get_node_text(name_node, code_bytes)

    elif language in ['java', 'c_sharp', 'typescript', 'php', 'cpp']:
         if node.type in ['class_declaration', 'method_declaration', 'class_definition', 'method_definition', 'function_definition']:
             name_node = node.child_by_field_name('name')
             if name_node:
                 chunk['name'] = get_node_text(name_node, code_bytes)

    # Note: We rely on the initial FrameworkDetector validation to ensure we are only processing relevant projects.
    # However, we still need node-level filtering to avoid extracting utilities or non-API code.
    # This logic can remain locally or eventually be moved to detailed strategies per framework.
    
    # Simple Keep-All matching the existing "keep heuristic" logic style for now, 
    # but could be improved.
    # For now, we assume if we are here, we are in a valid framework project, but we still filter specific types.
    
    # 1. NestJS
    if file_name.endswith('.ts'):
        if 'Controller' in text and node.type == 'class_declaration': return chunk
        if 'Service' in chunk['name'] and node.type == 'class_declaration': return chunk
        if node.type == 'method_definition' and ('@Get' in text or '@Post' in text or '@Put' in text): return chunk
        
    # 2. Spring Boot
    elif file_name.endswith('.java'):
        if node.type == 'class_declaration':
            if ('Controller' in text or 'Service' in text): return chunk
        if node.type == 'method_declaration':
            if ('@PostMapping' in text or '@GetMapping' in text or '@PutMapping' in text): return chunk

    # 3. Django / FastAPI (Python)
    elif file_name.endswith('.py'):
        if node.type == 'decorated_definition':
            if '@' in text: return chunk
        elif node.type == 'class_definition':
            if 'View' in chunk['name'] or 'Service' in chunk['name'] or 'Serializer' in chunk['name']:
                return chunk

    # 4. .NET
    elif file_name.endswith('.cs'):
         if node.type == 'class_declaration':
             if 'Controller' in chunk['name'] or 'Service' in chunk['name']: return chunk
         if node.type == 'method_declaration':
             if '[' in text and ']' in text:
                 return chunk
                 
    # 5. PHP (Laravel/legacy) - stub for future expansion based on user request "php"
    elif file_name.endswith('.php'):
         if 'Controller' in chunk['name']: return chunk
         
    # 6. Express (JS/TS) - stub
    elif file_name.endswith('.js'):
         if 'app.get' in text or 'app.post' in text: return chunk

    return None

def process_directory(input_dir, output_dir=None):
    
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Scanning {input_dir}...")
    
    # 1. Framework Validation
    framework_finder = FrameworkDetector()
    detected_framework = framework_finder.detect(input_dir)
    print(f"Detected Framework: {detected_framework}")
    
    if detected_framework == "Unknown":
        print(f"Error: this code base does not create REST API endpoints -> cannot generate REST API Documentation ..")
        # In a real tool this might exit(1), but for this script we just return or raise
        # For the purpose of the requirement "test cases ... to check the output (here it should be an error)"
        raise ValueError("this code base does not create REST API endpoints -> cannot generate REST API Documentation ..")

    language_finder = LanguageFinder()
    all_ast_data = []

    for root, dirs, files in os.walk(input_dir):
        # exclusions
        if 'node_modules' in dirs: dirs.remove('node_modules')
        
        for file in files:
            file_path = os.path.join(root, file)
            
            # 2. Language Detection
            lang_name = language_finder.detect(file_path)
            
            if lang_name != 'unknown':
                print(f"Processing {file} as {lang_name}...")
                
                try:
                    tree, code = parse_file(file_path, lang_name)
                    if not tree: continue

                    code_bytes = bytes(code, 'utf8')
                    
                    cursor = tree.walk()
                    chunks = []
                    
                    def traverse(curr_node, parent_name=None):
                        added = False
                        
                        relevant_types = [
                            'class_definition', 'function_definition', 'decorated_definition', # Python
                            'class_declaration', 'method_declaration', # Java, C#
                            'method_definition', # TS
                            'function_declaration' # Go, PHP?
                        ]
                        
                        if curr_node.type in relevant_types:
                            rel_path = os.path.relpath(file_path, input_dir)
                            chunk = extract_chunk(curr_node, code_bytes, lang_name, file, parent_name=parent_name, file_path=rel_path)
                            if chunk:
                                chunks.append(chunk)
                                added = True
                        
                        if not added or (curr_node.type in ['class_definition', 'class_declaration']):
                             new_parent_name = parent_name
                             if curr_node.type in ['class_definition', 'class_declaration']:
                                 name_child = curr_node.child_by_field_name('name')
                                 if name_child:
                                     new_parent_name = get_node_text(name_child, code_bytes)
                             
                             for child in curr_node.children:
                                 traverse(child, parent_name=new_parent_name)

                    traverse(tree.root_node)

                    if chunks:
                        final_data = {
                            "file": file,
                            "language": lang_name,
                            "relevant_chunks": chunks
                        }
                        all_ast_data.append(final_data)

                        if output_dir:
                            safe_root = os.path.relpath(root, input_dir).replace(os.sep, '_')
                            if safe_root == '.' or safe_root == '': safe_root = ""
                            else: safe_root += "_"
                            
                            output_filename = f"{safe_root}{os.path.splitext(file)[0]}.json"
                            output_path = os.path.join(output_dir, output_filename)
                            
                            with open(output_path, 'w', encoding='utf-8') as f:
                                json.dump(final_data, f, indent=2)
                            print(f"Saved {len(chunks)} chunks to {output_path}")
                except Exception as e:
                   # Parser might assume language lib is present, catch if not
                   print(f"Skipping {file}: {e}")
                   continue

    return all_ast_data

# Configuration
APIS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'apis-test')
AST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ast')

if __name__ == "__main__":
    process_directory(APIS_DIR, AST_DIR)
