import zlib
import base64


def compress_code(code: str) -> str:
    compressed = zlib.compress(code.encode("utf-8"), level=9)
    return base64.b64encode(compressed).decode("utf-8")



