import os
import json
from tree_sitter_languages import get_language, get_parser

# Configuration
APIS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'apis-test')
AST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ast')

def parse_file(file_path, language_name):
    try:
        language = get_language(language_name)
        parser = get_parser(language_name)
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

def extract_chunk(node, code_bytes, language, file_name):
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
            # In python tree-sitter, decorators wrap the definition. 
            # If we are visiting the definition directly, we might miss the wrapper.
            # We should probably visit `decorated_definition` instead.
            pass

    elif language in ['java', 'c_sharp', 'typescript']:
        if node.type in ['class_declaration', 'method_declaration', 'class_definition', 'method_definition']:
             name_node = node.child_by_field_name('name')
             if name_node:
                 chunk['name'] = get_node_text(name_node, code_bytes)

    # FILTERING LOGIC
    # 1. NestJS
    if file_name.endswith('.ts'):
        # Keep Controller classes
        if 'Controller' in text and node.type == 'class_declaration': return chunk
        # Keep Services
        if 'Service' in chunk['name'] and node.type == 'class_declaration': return chunk
        # Keep Methods with decorators like @Get, @Post
        if node.type == 'method_definition' and ('@Get' in text or '@Post' in text or '@Put' in text): return chunk
        
    # 2. Spring Boot
    elif file_name.endswith('.java'):
        # Keep Controllers and Services
        if node.type == 'class_declaration':
            if ('Controller' in text or 'Service' in text): return chunk
        if node.type == 'method_declaration':
            if ('@PostMapping' in text or '@GetMapping' in text or '@PutMapping' in text): return chunk

    # 3. Django / FastAPI (Python)
    elif file_name.endswith('.py'):
        # Python handling is tricky because `decorated_definition` contains the class/function
        # We need to handle `decorated_definition` specifically
        if node.type == 'decorated_definition':
            # Check content
            if '@' in text: # Has decorator
                 return chunk
        elif node.type == 'class_definition':
            # Check naming convention if no decorator
            if 'View' in chunk['name'] or 'Service' in chunk['name'] or 'Serializer' in chunk['name']:
                return chunk


    # 4. .NET
    elif file_name.endswith('.cs'):
         if node.type == 'class_declaration':
             if 'Controller' in chunk['name'] or 'Service' in chunk['name']: return chunk
         if node.type == 'method_declaration':
             if '[' in text and ']' in text: # loose check for attributes like [HttpPost]
                 return chunk

    return None

def process_files():
    extension_map = {
        '.ts': 'typescript',
        '.java': 'java',
        '.py': 'python',
        '.cs': 'c_sharp'
    }

    if not os.path.exists(AST_DIR):
        os.makedirs(AST_DIR)

    print(f"Scanning {APIS_DIR}...")
    
    for root, dirs, files in os.walk(APIS_DIR):
        for file in files:
            file_path = os.path.join(root, file)
            ext = os.path.splitext(file)[1]
            
            if ext in extension_map:
                lang_name = extension_map[ext]
                print(f"Processing {file} as {lang_name}...")
                
                tree, code = parse_file(file_path, lang_name)
                if not tree: continue

                code_bytes = bytes(code, 'utf8')
                
                # Targeted Traversal
                # We will walk the tree and specifically look for "Definitions"
                
                cursor = tree.walk()
                chunks = []
                
                def traverse(curr_node):
                    # Python `decorated_definition` wraps `class_definition`
                    # We accept `decorated_definition` and process it, but don't recurse into it 
                    # to generate DOUBLE chunks (one for decorated, one for class).
                    
                    added = False
                    
                    # TYPES WE CARE ABOUT
                    relevant_types = [
                        'class_definition', 'function_definition', 'decorated_definition', # Python
                        'class_declaration', 'method_declaration', # Java, C#
                        'method_definition', # TS
                    ]
                    
                    if curr_node.type in relevant_types:
                        chunk = extract_chunk(curr_node, code_bytes, lang_name, file)
                        if chunk:
                            chunks.append(chunk)
                            added = True
                    
                    # Only recurse if we didn't add this node as a chunk (to keep it top-level)
                    # OR if match was a class, we MIGHT want methods inside?
                    # "reduce the code used more and more" -> implies we might just want the Class High Level?
                    # But user said "extract functions as controllers functions"
                    # So we DOES want methods.
                    
                    if not added or (curr_node.type in ['class_definition', 'class_declaration']):
                         for child in curr_node.children:
                             traverse(child)

                traverse(tree.root_node)

                # Save
                safe_root = os.path.relpath(root, APIS_DIR).replace(os.sep, '_')
                if safe_root == '.' or safe_root == '': safe_root = ""
                else: safe_root += "_"
                
                output_filename = f"{safe_root}{os.path.splitext(file)[0]}.json"
                output_path = os.path.join(AST_DIR, output_filename)
                
                if chunks:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        final_data = {
                            "file": file,
                            "language": lang_name,
                            "relevant_chunks": chunks
                        }
                        json.dump(final_data, f, indent=2)
                    print(f"Saved {len(chunks)} chunks to {output_path}")
                else:
                    print(f"No relevant chunks found in {file}")

if __name__ == "__main__":
    process_files()
