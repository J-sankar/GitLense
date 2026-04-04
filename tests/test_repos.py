

def test_list_repos(client, auth_headers, test_repo):
    response = client.get("/api/v1/repos", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "test/repo"


def test_list_repos_empty(client, auth_headers):
    response = client.get("/api/v1/repos", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_list_repos_no_auth(client):
    response = client.get("/api/v1/repos")
    assert response.status_code == 401