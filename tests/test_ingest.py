
from unittest.mock import patch


def test_invalid_url(client, auth_headers):
    response = client.post("/api/v1/ingest", json={
        "repo_url": "not-a-url"
    }, headers=auth_headers)
    assert response.status_code == 400


def test_ingest_no_auth(client):
    response = client.post("/api/v1/ingest", json={
        "repo_url": "https://github.com/test/repo"
    })
    assert response.status_code == 401


@patch("app.api.v1.endpoints.ingest.queue_ingestion")
@patch("app.services.github_fetcher.get_repo_size", return_value=500)
def test_fresh_ingest(mock_size, mock_queue, client, auth_headers):
    response = client.post("/api/v1/ingest", json={
        "repo_url": "https://github.com/karpathy/micrograd"
    }, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "queued"
    assert "job_id" in data
    mock_queue.assert_called_once()


@patch("app.api.v1.endpoints.ingest.queue_ingestion")
@patch("app.services.github_fetcher.get_repo_size", return_value=500)
def test_already_ingested(mock_size, mock_queue, client, auth_headers, test_repo,test_job):
    response = client.post("/api/v1/ingest", json={
        "repo_url": "https://github.com/test/repo"
    }, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    mock_queue.assert_not_called()  





