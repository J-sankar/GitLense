import os


def parse_repo_name(repo_url: str) -> tuple[str,str]:
    parts =   repo_url.rstrip("/").split("/")
    return parts[-2], parts[-1]


SUPPORTED_EXTENSIONS =  {
    ".py": "py",
    ".js": "js",
    ".java": "java",
    ".ts": "ts",
    ".go": "go",
    ".html":"html"
}


def get_language(file_name:str) ->str:
    ext = os.path.splitext(file_name)[1]
    return SUPPORTED_EXTENSIONS.get(ext)