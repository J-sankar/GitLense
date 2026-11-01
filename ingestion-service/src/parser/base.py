from abc import ABC,abstractmethod
from tree_sitter import Node,Parser,Language
from src.core.logger import get_logger
from typing import TypedDict, List

logger = get_logger(__name__)

class ParserConfig(TypedDict):
    node_types: List[str]
    parent_types: List[str]
    import_types: List[str]
    export_types: List[str]

class BaseParser(ABC):
    def __init__(self,language:Language, config:ParserConfig):
        self.language = language
        self.config = config
        self.parser = Parser(language)

        

    @abstractmethod
    def extract_name(self,node:Node, content_bytes:str)->str:
        pass

    def get_file_imports_exports(self,root_node:Node,content: str)->dict :
        import_types = self.config.get("import_types", [])
        export_types = self.config.get("export_types",[])
        file_imports = []
        file_exports = []

        for child in root_node.children:
            if child.type in import_types:
                file_imports.append(content[child.start_byte : child.end_byte].strip())
            if child.type in export_types:
                file_exports.append(content[child.start_byte : child.end_byte].strip())
        return {
            "file_imports" : file_imports,
            "file_exports" : file_exports
        }
    

    def get_global_chunks(self, root_node: Node,file_path: str, content: str, language: str) -> List[dict] :
        config = self.config
        chunks = []
        global_nodes = [
            child
            for child in root_node.children
            if child.type not in config.get("node_types")
            and child.type
            not in config.get("parent_types", [])  # 👈 EXCLUDE CLASSES/INTERFACES
            and child.type not in config.get("import_types", [])
            and child.type not in config.get("export_types", [])
            and child.type != "comment"
        ]

        if global_nodes:
            global_code = "\n".join(
                [content[n.start_byte : n.end_byte].strip() for n in global_nodes]
            )
            chunks.append(
                {
                    "name": "module_scope",
                    "parent_scope": file_path,
                    "code": global_code,
                    "language": language,
                    "file": file_path,
                    "type": "global_logic",
                    "start_line": global_nodes[0].start_point[0] + 1,
                    "end_line": global_nodes[-1].end_point[0] + 1,
                }
            )

     
        return chunks
    @abstractmethod
    def get_skeleton_lines(self, chunks:List[dict]) -> List[str] :
        pass



    def walk(self,node:Node, content_bytes:str, chunks:list[dict], language:str, path:str,parent_scope:str)->None:
        
        node_types = self.config["node_types"]
        parent_types = self.config.get("parent_types",[])
        name = self.extract_name(node, content_bytes)
        if node.type in node_types:
            code_bytes = content_bytes[node.start_byte:node.end_byte]
            code = code_bytes.decode("utf-8", errors="replace")

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
            self.walk(child, content_bytes, chunks, language, path,parent_scope=new_scope)



        
