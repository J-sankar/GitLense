from app.parser.base import BaseParser





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
    

