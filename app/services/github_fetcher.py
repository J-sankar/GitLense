from app.core.logger import get_logger
from github import Github
from app.core.config import settings

import os

logger = get_logger(__name__)

SUPPORTED_EXTENSIONS =  {
    ".py": "py",
    ".js": "js",
    ".java": "java",
    ".ts": "ts",
}


def get_language(file_name:str) ->str:
    ext = os.path.splitext(file_name)[1]
    return SUPPORTED_EXTENSIONS.get(ext)

def parse_repo_name(repo_url: str) -> str:
    return "/".join(repo_url.rstrip("/").split("/")[-2:])

def fetch_repo_files(repo_url: str) -> list[dict]:
    repo_name = parse_repo_name(repo_url)
    g = Github(settings.GITHUB_TOKEN)
    repo = g.get_repo(repo_name)

    logger.info(f"Fetching files from repository: {repo.full_name}")
    logger.debug(f"Description: {repo.description}")
    files = []
    contents = repo.get_contents("")
    

    while contents:
        item = contents.pop(0)
    
        if item.type == "dir":
            contents.extend(repo.get_contents(item.path))
            continue
        
        language = get_language(item.name)

        if not language:
            continue
    
        try:
            file_content = item.decoded_content.decode("utf-8")
            files.append({
                "path": item.path,
                "language": language,
                "content": file_content
            })
            logger.info(f"Fetched file: {item.path} ({language})")
        except Exception as e:
            logger.warning(f"Skipped {item.path}: {e}")
            continue
    return files

