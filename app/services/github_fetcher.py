
from github import Github
from core.config import settings

SUPPORTED_EXTENSIONS =  {
    ".py": "py",
    ".js": "js",
    ".java": "java",
    ".ts": "ts",
}


def get_language(file_name:str) ->str:
    ext = os.path.splitext(file_name)[1]
    return SUPPORTED_EXTENSIONS.get(ext)

def fetch_repo_files(repo_url: str) -> any:
    repo_name = "/".join(repo_url.split("/")[-2:])
    g = Github(settings.GITHUB_TOKEN)
    repo = g.get_repo(repo_name)

    print("Fetching files from repo: ", repo.full_name)
    print(f"description: {repo.description}")

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
            print(f"Fetched file: {item.path} (language: {language})")
        except Exception as e:
            print(f"Error decoding file {item.path}: {e}")
            continue
    return files

if __name__ == "__main__":
    fetch_repo_files("https://github.com/J-sankar/veritas_v6")