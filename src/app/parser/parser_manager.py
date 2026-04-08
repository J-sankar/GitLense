
from tree_sitter import Language
import tree_sitter_python as tsPython
import tree_sitter_java as tsJava
import tree_sitter_javascript as tsJavascript
import tree_sitter_typescript as tsTypescript
import tree_sitter_html as tsHtml
import tree_sitter_c as tsC
import tree_sitter_go as tsGo


from app.parser.base import ParserConfig
from app.parser.java import JavaParser
from app.parser.python import PythonParser

from app.core.logger import get_logger

logger = get_logger(__name__)



class ParserManager:
    def __init__(self):
        self.languages = {
            "_PY_LANGUAGE": Language(tsPython.language()),
            "_JS_LANGUAGE": Language(tsJavascript.language()),
            "_TS_LANGUAGE": Language(tsTypescript.language_typescript()),
            "_JAVA_LANGUAGE": Language(tsJava.language()),
            "_HTML_LANGUAGE": Language(tsHtml.language()),
            "_C_LANGUAGE": Language(tsC.language()),
            "_GO_LANGUAGE": Language(tsGo.language()),
        }
        self.configs  = {
    "py": {
        "node_types": ["function_definition", "class_definition"],
        "parent_types": ["class_definition"],
        "import_types": ["import_statement", "import_from_statement"],
        "export_types": [] 
    },
    "js": {
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
        "node_types": ["method_declaration", "class_declaration", "interface_declaration"],
        "parent_types": ["class_declaration", "interface_declaration", "enum_declaration"],
        "import_types": ["import_declaration"],
        "export_types": []
    },
    "c": {

        "node_types": ["function_definition", "struct_specifier"], 
        "parent_types": ["struct_specifier", "union_specifier", "enum_specifier"],
        "import_types": ["preproc_include"], 
        "export_types": []
    },
    "go": {
      
        "node_types": ["function_declaration", "method_declaration", "type_declaration"],
        "parent_types": ["type_declaration"],
        "import_types": ["import_declaration"], 
        "export_types": [] 
    },
    "html": {
        "node_types": ["element", "script_element", "style_element"],
        "parent_types": ["element"], 
        "import_types": [],
        "export_types": []
    }
}
        self.strategies = {
            "py": PythonParser(self.languages["py"], ParserConfig(self.configs["py"])),
            "java": JavaParser(self.languages["java"], ParserConfig(self.configs["java"]))
        }
        


    def extract_chunks(self, file_path:str, content:str, language:str)->dict:
        startegy = self.strategies.get(language,[])
        if not startegy:
            logger.error(f"No startegy found for language {language}")
            raise Exception(f"No strategy found for language {language}")
        
        
        



