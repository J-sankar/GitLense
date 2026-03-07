from code_parser import extract_chunks
from github_fetcher import fetch_repo_files

def test_pipeline(repo_url:str):
    files = fetch_repo_files(repo_url)
    all_chunks = []

    for file in files:
        chunks = extract_chunks(file["path"], file["content"], file["language"])
        all_chunks.extend(chunks)
        if chunks:
            print(f"  {file['path']} → {len(chunks)} chunks")
    print(f"Total extracted chunks: {len(all_chunks)}")

    print("\nSample chunks:")
    for chunk in all_chunks:
        print(f"\n  file: {chunk['path']}")
        print(f"  name: {chunk['name']}")
        print(f"  lines: {chunk['start_line']}-{chunk['end_line']}")
        print(f"  preview: {chunk['code'][:80]}...")

if __name__ == "__main__":
    test_pipeline("https://github.com/J-sankar/veritas_v6")