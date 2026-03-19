def build_embed_text(chunk: dict) -> str:
    return f"""File: {chunk['file']}
    Name: {chunk['name']}
    Type: {chunk['type']}
    Lines: {chunk['start_line']}-{chunk['end_line']}
    {chunk['code']}""".strip()