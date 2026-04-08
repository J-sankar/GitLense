from app.parser.base import BaseParser
from typing import List




class PythonParser(BaseParser):
    def extract_name(self, node, content_bytes):
        name_node = node.child_by_field_name("name")

        if name_node:
            raw_bytes = content_bytes[name_node.start_byte:name_node.end_byte]
            return raw_bytes.decode("utf-8", errors="replace").strip()
        
        if node.type in ("function_definition", "class_definition"):
            for child in node.children:
                if child.type == "identifier":
                    raw_bytes = content_bytes[child.start_byte:child.end_byte]
                    return raw_bytes.decode("utf-8", errors="replace").strip()
        return "anonymous"
    
    def get_skeleton_lines(self, chunks:List[dict]) -> List[str] :
        config = self.config
        skeleton_lines = []
        for chunk in chunks:
            if chunk["type"] in config.get("node_types", []) or chunk["type"] in config.get("parent_types", []):
                code_lines = chunk["code"].strip().splitlines()
                signature = None 
                for line in code_lines:
                    if not line.strip().startswith("@"):
                        signature = line.strip()
                        break

                line = f"{chunk['type']}: {signature}"
                skeleton_lines.append(line)
        return skeleton_lines

