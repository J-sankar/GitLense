from tree_sitter import Language
import tree_sitter_python as tsPython
import tree_sitter_java as tsJava
import tree_sitter_javascript as tsJavascript
import tree_sitter_typescript as tsTypescript
import tree_sitter_html as tsHtml
import tree_sitter_c as tsC
import tree_sitter_go as tsGo


from src.parser.base import ParserConfig
from src.parser.java import JavaParser
from src.parser.python import PythonParser

from src.core.logger import get_logger

logger = get_logger(__name__)


class ParserManager:
    def __init__(self):
        self.languages = {
            "py": Language(tsPython.language()),
            "js": Language(tsJavascript.language()),
            "ts": Language(tsTypescript.language_typescript()),
            "java": Language(tsJava.language()),
            "html": Language(tsHtml.language()),
            "c": Language(tsC.language()),
            "go": Language(tsGo.language()),
        }
        self.configs = {
            "py": {
                "node_types": ["function_definition", "class_definition"],
                "parent_types": ["class_definition"],
                "import_types": ["import_statement", "import_from_statement"],
                "export_types": [],
            },
            "js": {
                "node_types": [
                    "function_declaration",
                    "function_expression",
                    "arrow_function",
                    "generator_function_declaration",
                    "class_declaration",
                    "method_definition",
                    "jsx_element",
                    "jsx_self_closing_element",
                ],
                "parent_types": ["class_declaration"],
                "import_types": ["import_statement"],
                "export_types": ["export_statement", "export_declaration"],
            },
            "ts": {
                "node_types": [
                    "function_declaration",
                    "function_expression",
                    "arrow_function",
                    "class_declaration",
                    "method_definition",
                    "jsx_element",
                    "jsx_self_closing_element",
                ],
                "parent_types": [
                    "class_declaration",
                    "interface_declaration",
                    "enum_declaration",
                ],
                "import_types": ["import_statement"],
                "export_types": ["export_statement", "export_declaration"],
            },
            "java": {
                "node_types": [
                    "method_declaration",
                    "class_declaration",
                    "interface_declaration",
                ],
                "parent_types": [
                    "class_declaration",
                    "interface_declaration",
                    "enum_declaration",
                ],
                "import_types": ["import_declaration"],
                "export_types": [],
            },
            "c": {
                "node_types": ["function_definition", "struct_specifier"],
                "parent_types": [
                    "struct_specifier",
                    "union_specifier",
                    "enum_specifier",
                ],
                "import_types": ["preproc_include"],
                "export_types": [],
            },
            "go": {
                "node_types": [
                    "function_declaration",
                    "method_declaration",
                    "type_declaration",
                ],
                "parent_types": ["type_declaration"],
                "import_types": ["import_declaration"],
                "export_types": [],
            },
            "html": {
                "node_types": ["element", "script_element", "style_element"],
                "parent_types": ["element"],
                "import_types": [],
                "export_types": [],
            },
        }
        self.strategies = {
            "py": PythonParser(
                self.languages["py"], ParserConfig(**self.configs["py"])
            ),
            "java": JavaParser(
                self.languages["java"], ParserConfig(**self.configs["java"])
            ),
        }

    def extract_chunks(self, file_path: str, content: str, language: str) -> dict:
        strategy = self.strategies.get(language)
        if not strategy:
            logger.error(f"No startegy found for language {language}")
            return
        logger.debug(f"extracting from {file_path}...")
        content_bytes = bytes(content, "utf-8",errors="replace")
        parser = strategy.parser
        logger.debug(f"Language obtained: {language}")
        tree = parser.parse(content_bytes)
        logger.debug("Successfully parsed file")
        root_node = tree.root_node

        chunks = []
        
        file_headers = strategy.get_file_imports_exports(root_node,content)

        file_imports = file_headers.get("file_imports")
        file_exports = file_headers.get("file_exports")

        logger.debug(f"obtained headers: {len(file_imports)} imports , {len(file_exports)} exports ")

        strategy.walk(
            root_node, content_bytes, chunks, language, file_path, parent_scope=file_path
        )
        logger.debug(f"Obtained code chunks : {len(chunks)}")

        global_chunks = strategy.get_global_chunks(root_node,file_path,content,language)

        if  global_chunks:
            chunks.extend(global_chunks)
            logger.debug(f"global chunks appended : {len(global_chunks)}")

        

        if not chunks and content.strip():
            chunks.append(
                {
                    "name": "global_scope",
                    "parent_scope": file_path,
                    "code": content,
                    "language": language,
                    "file": file_path,
                    "type": "module",
                    "start_line": 1,
                    "end_line": len(content.splitlines()),
                }
            )
        skeleton_lines = strategy.get_skeleton_lines(chunks)
        if skeleton_lines:
            logger.debug(f"Extracted skeleton lines: {len(skeleton_lines)}")
        return {
            "metadata": {
                "path": file_path,
                "imports": file_imports,
                "exports": file_exports,
                "language": language,
                "skeleton": skeleton_lines
            },
            "chunks": chunks,
        }
