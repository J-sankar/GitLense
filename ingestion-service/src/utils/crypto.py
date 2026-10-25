import hashlib
import uuid 


def normalize_content(content: str) -> str:
    """Standardize line endings and whitespace for consistent hashing."""
    return content.replace("\r\n", "\n").strip()

def get_deterministic_id(filename: str, code: str) -> str :
    normalized_code = normalize_content(code)
    unique_string = f"{filename}:{normalized_code}"
    hash_obj = hashlib.md5(unique_string.encode('utf-8'))

    return str(uuid.UUID(hash_obj.hexdigest()))


def get_file_hash(content:str) ->str :
    normalized_content = normalize_content(content)
    return hashlib.sha256(normalized_content.encode("utf-8")).hexdigest()