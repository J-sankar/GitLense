from app.core.logger import get_logger
from github import Github,Auth
from app.core.config import settings
from app.utils.github import parse_repo_name,get_language


logger = get_logger(__name__)



g = Github(auth=Auth.Token(settings.GITHUB_TOKEN))



def get_repo_size(repo_url: str) ->int :
    try:
        repo_name = parse_repo_name(repo_url)
        repo = g.get_repo(repo_name)
        logger.info(f"Obtained Repo size: {repo.size} KB")
        return repo.size
    except Exception as e:
        logger.warning(f"Could not get repo size: {e} → defaulting to medium")
        return 2000



def fetch_repo_files(repo_url: str) -> list[dict]:
    repo_name = parse_repo_name(repo_url)
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

