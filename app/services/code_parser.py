from tree_sitter import Language, Parser
import tree_sitter_python as tsPython

from app.core.logger import get_logger

logger = get_logger(__name__)

PY_LANGUAGE = Language(tsPython.language())
parser = Parser(PY_LANGUAGE)

LANGUAGE_CONFIG = {
    "py": {
        "parser":     parser,
        "node_types": ["function_definition", "class_definition"]
    }
}

def extract_name(node, contents:str)->str:
    for child in node.children:
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
    if language != "py":
        logger.warning(f"Language {language} not supported for parsing")
        return []

    tree = parser.parse(bytes(content, "utf-8"))
    logger.info(f"Parsed file {file_path} into syntax tree")
    root_node = tree.root_node

    node_types = []
    if language == "py":
        node_types = LANGUAGE_CONFIG["py"]["node_types"]

    chunk = []
    walk(root_node, content, node_types, chunk, language, file_path)

    return chunk

def parse_files(files: list[dict]) -> list[dict]:
    all_chunks = []
    for file in files:
        chunks = extract_chunks(file["path"], file["content"], file["language"])
        all_chunks.extend(chunks)
    logger.info(f"Extracted {len(all_chunks)} chunks from {len(files)} files")
    return all_chunks