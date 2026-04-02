from tree_sitter import Language, Parser
import tree_sitter_python as tsPython
import tree_sitter_javascript as tsJavascript
import tree_sitter_typescript as tsTypescript
import tree_sitter_java as tsJava
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
        "parser":     Parser(_PY_LANGUAGE),
        "node_types": ["function_definition", "class_definition"]
    },
    "js": {
        "parser":     Parser(_JS_LANGUAGE),
        "node_types": [ "function_declaration",        # function foo() {}
        "function_expression",         # const foo = function() {}
        "arrow_function",              # const foo = () => {}
        "generator_function_declaration", # function* foo() {}

        # ── Classes ───────────────────────────────────
        "class_declaration",           # class Foo {}
        "method_definition",           # foo() {} inside class

        # ── React/JSX ─────────────────────────────────
        "jsx_element",                 # <div>...</div>
        "jsx_self_closing_element",    # <Component />

        # ── Imports ───────────────────────────────────
        "import_statement",            # import x from 'y'

        # ── Exports ───────────────────────────────────
        "export_statement",       ]
    },
    "ts": {
        "parser":     Parser(_TS_LANGUAGE),
        "node_types": [ "function_declaration",        # function foo() {}
        "function_expression",         # const foo = function() {}
        "arrow_function",              # const foo = () => {}
        "generator_function_declaration", # function* foo() {}

        # ── Classes ───────────────────────────────────
        "class_declaration",           # class Foo {}
        "method_definition",           # foo() {} inside class

        # ── React/JSX ─────────────────────────────────
        "jsx_element",                 # <div>...</div>
        "jsx_self_closing_element",    # <Component />

        # ── Imports ───────────────────────────────────
        "import_statement",            # import x from 'y'

        # ── Exports ───────────────────────────────────
        "export_statement",       ]
    },
    "java": {
        "parser":     Parser(_JAVA_LANGUAGE),
        "node_types": ["method_declaration", "class_declaration", "interface_declaration"]
    },
    "html": {
        "parser":     Parser(Language(tsHtml.language())),
        "node_types": ["element", "script_element", "style_element"]
    },
    "c": {
        "parser":     Parser(Language(tsC.language())),
        "node_types": ["function_definition", "struct_specifier", "declaration"]
    },
    "go": {
        "parser":     Parser(Language(tsGo.language())),
        "node_types": ["function_declaration", "method_declaration", "type_declaration"]
    },
}

def extract_name(node, contents:str)->str:
    for child in node.children:
        if child.type == "identifier":
            return contents[child.start_byte:child.end_byte]

    # ── Go methods (func (s *Server) Start()) ────────────────
    for child in node.children:
        if child.type == "field_identifier":
            return contents[child.start_byte:child.end_byte]

    # ── JS/TS arrow + named function expressions ─────────────
    if node.type in ("arrow_function", "function") and node.parent:
        if node.parent.type == "variable_declarator":
            for child in node.parent.children:
                if child.type == "identifier":
                    return contents[child.start_byte:child.end_byte]
    

    return "anonymous"


def walk(node, content:str, node_types:list[str], chunk:list[dict], language:str, path:str)->None:
    
    if node.type in node_types:
        name = extract_name(node, content)
        code = content[node.start_byte:node.end_byte]

        logger.debug(f"Found {language} code: {name} of type {node.type} at {path}")

        chunk.append({
            "name": name,
            "code": code,
            "language": language,
            "file": path,
            "type": node.type, 
            "start_line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1

        })

        logger.debug(f"Extracted {language} chunk: {name} of type {node.type} from {path} lines {node.start_point[0] + 1}-{node.end_point[0] + 1}")
    for child in node.children:
        walk(child, content, node_types, chunk, language, path)



def extract_chunks(file_path:str, content:str, language:str)->list[dict]:
    config  = LANGUAGE_CONFIG.get(language)

    if not config:
        logger.warning(f"Language '{language}' not supported, skipping {file_path}")
        return []
        
    tree = config["parser"].parse(bytes(content, "utf-8"))
    logger.info(f"Parsed file {file_path} into syntax tree")
    root_node = tree.root_node

    
    chunk = []
    walk(root_node, content, config["node_types"], chunk, language, file_path)

    return chunk

def parse_files(files: list[dict]) -> list[dict]:
    all_chunks = []
    for file in files:
        chunks = extract_chunks(file["path"], file["content"], file["language"])
        all_chunks.extend(chunks)
    logger.info(f"Extracted {len(all_chunks)} chunks from {len(files)} files")
    return all_chunks