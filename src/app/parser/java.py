from app.parser.base import BaseParser



class JavaParser(BaseParser):
    def extract_name(self, node, content_bytes):
        name_node = node.child_by_field_name("name")

        if name_node:
            raw_bytes = content_bytes[name_node.start_byte : name_node.end_byte]
            return raw_bytes.decode("utf-8", errors="replace").strip()
            
        
        for child in node.children:
            if child.type in ("modifiers", "formal_parameters", "dimensions","type_parameters"):
                continue
            if child.type == "identifier":
                raw_bytes = content_bytes[name_node.start_byte : name_node.end_byte]
                return raw_bytes.decode("utf-8", errors="replace").strip()
       
        return "anonymous"
    
    
