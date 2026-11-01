
from unittest.mock import call,patch
from httpx import AsyncClient
import pytest_asyncio  # noqa: F401
import  pytest

async def test_invalid_url(mocker,client:AsyncClient, ):
    response = await client.post("/api/v2/ingest", json={
        "repo_url": "not-a-url"
    })
    assert response.status_code == 400









