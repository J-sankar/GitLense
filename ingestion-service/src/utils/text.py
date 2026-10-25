def build_embed_text(chunk: dict) -> str:
    return f"""File: {chunk['file']}
    Name: {chunk['name']}
    Type: {chunk['type']}
    Lines: {chunk['start_line']}-{chunk['end_line']}
    Parent_Scope: {chunk["parent_scope"]}
    {chunk['code']}""".strip()