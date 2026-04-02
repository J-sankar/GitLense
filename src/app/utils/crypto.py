import hashlib
import uuid 


def get_deterministic_id(filename: str, code: str) -> str :
    normalized_code = code.replace("\r\n", "\n").strip()
    unique_string = f"{filename}:{normalized_code}"
    hash_obj = hashlib.md5(unique_string.encode('utf-8'))

    return str(uuid.UUID(hash_obj.hexdigest()))

