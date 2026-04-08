from tree_sitter import Language, Parser
import tree_sitter_python as tsPython
import tree_sitter_java as tsJava
import tree_sitter_javascript as tsJavascript
import tree_sitter_typescript as tsTypescript
import tree_sitter_html as tsHtml
import tree_sitter_c as tsC
import tree_sitter_go as tsGo


from app.core.logger import get_logger

logger = get_logger(__name__)

_PY_LANGUAGE = Language(tsPython.language())
_JS_LANGUAGE = Language(tsJavascript.language())
_TS_LANGUAGE = Language(tsTypescript.language_typescript())
_JAVA_LANGUAGE = Language(tsJava.language())




LANGUAGE_CONFIG = {
    "py": {
        "parser": Parser(_PY_LANGUAGE),
        "node_types": ["function_definition", "class_definition"],
        "parent_types": ["class_definition"],
        "import_types": ["import_statement", "import_from_statement"],
        "export_types": [] 
    },
    "js": {
        "parser": Parser(_JS_LANGUAGE),
        "node_types": [
            "function_declaration", "function_expression", "arrow_function", 
            "generator_function_declaration", "class_declaration", "method_definition",
            "jsx_element", "jsx_self_closing_element"
        ],
        "parent_types": ["class_declaration"],
        "import_types": ["import_statement"],
        "export_types": ["export_statement", "export_declaration"]
    },
    "ts": {
        "parser": Parser(_TS_LANGUAGE),
        "node_types": [
            "function_declaration", "function_expression", "arrow_function",
            "class_declaration", "method_definition", "jsx_element", 
            "jsx_self_closing_element"
        ],
        "parent_types": ["class_declaration", "interface_declaration", "enum_declaration"], 
        "import_types": ["import_statement"], 
        "export_types": ["export_statement", "export_declaration"] 
    },
    "java": {
        "parser": Parser(_JAVA_LANGUAGE),
        "node_types": ["method_declaration", "class_declaration", "interface_declaration"],
        "parent_types": ["class_declaration", "interface_declaration", "enum_declaration"],
        "import_types": ["import_declaration"],
        "export_types": []
    },
    "c": {
        "parser": Parser(Language(tsC.language())),
        "node_types": ["function_definition", "struct_specifier"], 
        "parent_types": ["struct_specifier", "union_specifier", "enum_specifier"],
        "import_types": ["preproc_include"], 
        "export_types": []
    },
    "go": {
        "parser": Parser(Language(tsGo.language())),
        "node_types": ["function_declaration", "method_declaration", "type_declaration"],
        "parent_types": ["type_declaration"],
        "import_types": ["import_declaration"], 
        "export_types": [] 
    },
    "html": {
        "parser": Parser(Language(tsHtml.language())),
        "node_types": ["element", "script_element", "style_element"],
        "parent_types": ["element"], 
        "import_types": [],
        "export_types": []
    }
}

def extract_name(node, contents: str) -> str:
    name_node = node.child_by_field_name('name')
    if name_node:
        return contents[name_node.start_byte:name_node.end_byte].strip()
    
    for child in node.children:
        # SKIP modifiers (where @RequestBody and 'public' live)
        if child.type == "modifiers":
            continue
        # SKIP formal_parameters (where the variables inside ( ) live)
        if child.type == "formal_parameters":
            continue
            
        if child.type == "identifier":
            return contents[child.start_byte:child.end_byte].strip()
        

    if node.type in ("arrow_function", "function") and node.parent:
        if node.parent.type == "variable_declarator":
            for c in node.parent.children:
                if c.type == "identifier":
                    return contents[c.start_byte:c.end_byte].strip()

    for child in node.children:
        if child.type == "identifier":
            return contents[child.start_byte:child.end_byte].strip()

    return "anonymous"


def walk(node, content:str, config:dict, chunks:list[dict], language:str, path:str,parent_scope:str)->None:
    
    node_types = config["node_types"]
    parent_types = config.get("parent_types",[])
    name = extract_name(node, content)
    if node.type in node_types:
        code = content[node.start_byte:node.end_byte]

        logger.debug(f"Found {language} code: {name} of type {node.type} at {path}")

        chunks.append({
            "name": name,
            "parent_scope": parent_scope,
            "code": code,
            "language": language,
            "file": path,
            "type": node.type, 
            "start_line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1

        })

        logger.debug(f"Extracted {language} chunk: {name} of type {node.type} from {path} lines {node.start_point[0] + 1}-{node.end_point[0] + 1}")

    new_scope = name if node.type in parent_types else parent_scope


    for child in node.children:
        walk(child, content, config, chunks, language, path,parent_scope=new_scope)



def extract_chunks(file_path:str, content:str, language:str)->dict:
    config  = LANGUAGE_CONFIG.get(language)

    

    if not config:
        logger.warning(f"Language '{language}' not supported, skipping {file_path}")
        return []
        
    tree = config["parser"].parse(bytes(content, "utf-8"))
    logger.info(f"Parsed file {file_path} into syntax tree")
    root_node = tree.root_node

    file_imports = []
    file_exports = []
    
    for child in root_node.children:
        if child.type in config.get("import_types", []):
            file_imports.append(content[child.start_byte:child.end_byte].strip())
        if child.type in config.get("export_types", []):
            file_exports.append(content[child.start_byte:child.end_byte].strip())   
    
    chunks = []

    walk(root_node, content, config, chunks, language, file_path, parent_scope=file_path)
    global_nodes = [
        child for child in root_node.children
        if child.type not in config.get("node_types") and 
        child.type not in config.get("parent_types", []) and     # 👈 EXCLUDE CLASSES/INTERFACES
        child.type not in config.get("import_types", []) and
        child.type not in config.get("export_types", []) and
        child.type != "comment"
    ]
    if global_nodes:
        global_code = "\n".join([content[n.start_byte:n.end_byte].strip() for n in global_nodes])
        chunks.append({
            "name": "module_scope",
            "parent_scope": file_path, 
            "code": global_code,
            "language": language,
            "file": file_path,
            "type": "global_logic",
            "start_line": global_nodes[0].start_point[0] + 1,
            "end_line": global_nodes[-1].end_point[0] + 1
        })
    if not chunks and content.strip():
        chunks.append({
            "name": "global_scope",
            "parent_scope": file_path,
            "code": content,
            "language": language,
            "file": file_path,
            "type": "module", 
            "start_line": 1,
            "end_line": len(content.splitlines())
        })
    skeleton_lines = []
    for chunk in chunks:
        if chunk["type"] in config.get("node_types", []) or chunk["type"] in config.get("parent_types", []):
 
            line = f"{chunk['type']}: {chunk['name']}"
            skeleton_lines.append(line)
    return {
        "metadata": {
            "path": file_path,
            "imports": file_imports,
            "exports": file_exports,
            "language": language,
            "skeleton": skeleton_lines
        },
        "chunks": chunks
    }

def parse_files(files: list[dict]) -> dict:
    all_chunks = []
    all_metadata = []
    for file in files:
        file_data = extract_chunks(file["path"], file["content"], file["language"])
        all_chunks.extend(file_data.get("chunks"))
        all_metadata.append(file_data.get("metadata"))
    logger.info(f"Extracted {len(all_chunks)} chunks from {len(files)} files")
    return {
        "chunks": all_chunks,
        "metadata": all_metadata
    }