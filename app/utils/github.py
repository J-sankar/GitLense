import os


def parse_repo_name(repo_url: str) -> str:
    return "/".join(repo_url.rstrip("/").split("/")[-2:])


SUPPORTED_EXTENSIONS =  {
    ".py": "py",
    ".js": "js",
    ".java": "java",
    ".ts": "ts",
    ".go": "go"
}


def get_language(file_name:str) ->str:
    ext = os.path.splitext(file_name)[1]
    return SUPPORTED_EXTENSIONS.get(ext)