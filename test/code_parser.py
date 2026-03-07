from tree_sitter import Language, Parser
import tree_sitter_python as tsPython

PY_LANGUAGE = Language(tsPython.language())
parser = Parser(PY_LANGUAGE)


def extract_name(node, contents:str)->str:
    for child in node.children:
        if child.type == "identifier":
            return contents[child.start_byte:child.end_byte]
    return "anonymous"


def walk(node, content:str, node_types:list[str], chunk:list[dict], language:str, path:str)->None:
    print(f"Visiting node: {node.type} at {path} lines {node.start_point[0] + 1}-{node.end_point[0] + 1}")
    if node.type in node_types:
        name = extract_name(node, content)
        code = content[node.start_byte:node.end_byte]

        print(f"Found {language} code: {name} at {path}")

        chunk.append({
            "name": name,
            "code": code,
            "language": language,
            "path": path,
            "start_line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1

        })

        print(f"Extracted code chunk: {name} ({language}) at {path} lines {node.start_point[0] + 1}-{node.end_point[0] + 1}")

    for child in node.children:
        walk(child, content, node_types, chunk, language, path)



def extract_chunks(file_path:str, content:str, language:str)->list[dict]:
    if language != "py":
        print(f"Language {language} not supported for parsing")
        return []

    tree = parser.parse(bytes(content, "utf-8"))
    print(f"Parsed syntax tree for {file_path}")
    root_node = tree.root_node

    node_types = []
    if language == "py":
        node_types = ["function_definition", "class_definition"]

    chunk = []
    walk(root_node, content, node_types, chunk, language, file_path)

    return chunk