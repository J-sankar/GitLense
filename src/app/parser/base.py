from abc import ABC,abstractmethod
from tree_sitter import Node,Parser,Language
from app.core.logger import get_logger
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



        
