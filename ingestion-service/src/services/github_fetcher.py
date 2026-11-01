import asyncio
from src.core.logger import get_logger
from githubkit import GitHub
from githubkit.exception import RequestFailed
from src.core.config import settings
from src.utils.github import parse_repo_name,get_language
import base64
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    after_log,
)
import logging
logger = get_logger(__name__)



g = GitHub(auth=settings.GITHUB_TOKEN)


MAX_RETRIES = 3 

def is_rate_limit_error(e: Exception) -> bool:
    error_msg = str(e).lower()
    return (
        "rate limit" in error_msg or
        "429"        in error_msg or
        "403"        in error_msg or
        "quota"      in error_msg
    )



async def wait_for_rate_limit_reset():
    try:
        rate_limit = await g.rest.rate_limit.async_get()
        reset_time = rate_limit.parsed_data.rate.reset
        from datetime import datetime, timezone
        now        = datetime.now(timezone.utc).timestamp()
        wait_time  = max(int(reset_time) - int(now) + 5, 60)
        logger.warning(f"Rate limit hit — waiting {wait_time}s for reset")
        await asyncio.sleep(wait_time)
    except Exception:
        logger.warning("Could not get rate limit reset time — waiting 60s")
        await asyncio.sleep(60)



@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=5, max=30),
    retry=retry_if_exception_type(RequestFailed),
    after=after_log(logger=logger, log_level=logging.WARNING),
    reraise=True
)
async def _get_repo(owner: str, repo_name: str):
    return await g.rest.repos.async_get(owner=owner, repo=repo_name)

@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=5, max=30),
    retry=retry_if_exception_type(RequestFailed),
    after=after_log(logger=logger, log_level=logging.WARNING),
    reraise=True
)
async def _get_tree(owner: str, repo_name: str, branch: str):
    return await g.rest.git.async_get_tree(
        owner=owner,
        repo=repo_name,
        tree_sha=branch,
        recursive="1"
    )


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=5, max=30),
    retry=retry_if_exception_type(RequestFailed),
    after=after_log(logger=logger, log_level=logging.WARNING),
    reraise=True
)
async def _get_blob(owner: str, repo_name: str, sha: str):
    return await g.rest.git.async_get_blob(
        owner=owner,
        repo=repo_name,
        file_sha=sha
    )



async def get_repo_size(repo_url: str) ->int :
    try:
        owner,repo_name = parse_repo_name(repo_url)
        response = await _get_repo(owner=owner, repo_name=repo_name)
        size = response.parsed_data.size
        
        logger.info(f"Obtained Repo size: {size} KB")
        return size
        
    except Exception as e:
        logger.warning(f"Could not get repo size: {e} → defaulting to medium")
        return 2000






async def fetch_repo_files(repo_url:str) -> list[dict]:
    owner, repo_name = parse_repo_name(repo_url)
    logger.info(f"Fetching files from repository: {owner}/{repo_name}")

    files = []
    try:
        repo_response = await _get_repo(owner=owner, repo_name=repo_name)
        default_branch = repo_response.parsed_data.default_branch
        logger.debug(f"Description: {repo_response.parsed_data.description}")
        tree_response = await _get_tree(
            owner=owner,
            repo_name=repo_name,
            branch=default_branch,
        )
        for item in tree_response.parsed_data.tree:
            logger.debug(f"item:{item}")
            if item.type != "blob":
                continue
            language = get_language(item.path)
            logger.debug(f"language: {language}")
            if not language:
                continue

            try:
                # 4. Fetch the actual file content using the file's SHA
                blob_response = await _get_blob(
                    owner=owner,
                    repo_name=repo_name,
                    sha=item.sha
                )
                
                # GitHub returns blob content encoded in base64
                file_content = base64.b64decode(blob_response.parsed_data.content).decode("utf-8")
                
                files.append({
                    "path": item.path,
                    "language": language,
                    "content": file_content
                })
                logger.info(f"Fetched file: {item.path} ({language})")
                
            except Exception as e:
                if is_rate_limit_error(e):
                    logger.error("Rate limit hit during blob fetching!")
                    raise # Break out of the loop and pass to the outer block
                logger.warning(f"Skipped {item.path}: {e}")
                continue

    except Exception as e:
        if is_rate_limit_error(e):
            logger.error(f"Rate limit hit fetching repo tree: {str(e).lower()}")
            raise
        logger.error(f"Failed to fetch repository data: {e}")
        raise 
      
    return files



