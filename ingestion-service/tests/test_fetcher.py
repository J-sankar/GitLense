import pytest_asyncio  # noqa: F401
import  pytest
from unittest.mock import call
from src.workers.repo_fetch import process_fetch_message
from src.models.db import (Repo, Job)
from sqlalchemy import select

@pytest.fixture(autouse=True)
def force_db(mocker, db_session):

    
    mocker.patch(
        "src.workers.repo_fetch.AsyncSessionLocal", 
        return_value=db_session
    )


@pytest.mark.asyncio
async def test_success_path(mocker, db_session, test_repo, test_job):
    mock_publish = mocker.patch("src.workers.repo_fetch.redis_manager.publish")
    mock_ack = mocker.patch("src.workers.repo_fetch.redis_manager.ack")

    mock_files = [
        {"path": "/src/hello.py" ,"language": "python", "content":"hello world"},
        {"path": "/src/server.js" ,"language": "javascript", "content":"hello world"},

    ]
    mocker.patch(
        "src.workers.repo_fetch.fetch_repo_files", 
        return_value=mock_files
    )

    payload = {
        "repo_id": str(test_repo.id),
        "job_id": str(test_job.id),
        "repo_url":test_repo.repo_url,
        "retries": "0"
    }

    await process_fetch_message("message_id_123", payload)
    # await db_session.refresh(test_repo)
    # await db_session.refresh(test_job)
    assert test_repo.status == "fetching"
    assert test_job.status == "processing"
    assert test_job.total_files == 2 
    mock_ack.assert_called_once_with(
        "repo:fetch",
        "fetch-workers",
        "fetch-worker-1",
        "message_id_123"
    )
    assert mock_publish.call_count == 2
    expected_calls = [
        call("file:process", {
            "repo_id": str(test_repo.id),
            "job_id": str(test_job.id),
            "repo_url": str(test_repo.repo_url),
            "file_path": "/src/hello.py",
            "language": "python",
            "content": "hello world",
            "retries": "0"
        }),
        call("file:process", {
            "repo_id": str(test_repo.id),
            "job_id": str(test_job.id),
            "repo_url": str(test_repo.repo_url),
            "file_path": "/src/server.js",
            "language": "javascript",
            "content": "hello world",
            "retries": "0"
        })
    ]
    
    # 2. Assert that ALL of those calls happened
    mock_publish.assert_has_calls(expected_calls, any_order=True)


async def test_empty_repo(mocker, db_session, test_repo , test_job):
    mock_publish = mocker.patch("src.workers.repo_fetch.redis_manager.publish")
    mock_ack = mocker.patch("src.workers.repo_fetch.redis_manager.ack")

   
    mocker.patch(
        "src.workers.repo_fetch.fetch_repo_files", 
        return_value=[]
    )

    payload = {
        "repo_id": str(test_repo.id),
        "job_id": str(test_job.id),
        "repo_url":test_repo.repo_url,
        "retries": "0"
    }
    await process_fetch_message("message_id_123", payload)

    repo_result = await db_session.execute(select(Repo).where(Repo.id == test_repo.id))
    updated_repo = repo_result.scalar_one_or_none()

    job_result = await db_session.execute(select(Job).where(Job.id == test_job.id))
    updatedt_job = job_result.scalar_one_or_none()


    assert updated_repo.status == "failed"
    assert updated_repo.error_message == "No files returned from GitHub"

    assert updatedt_job.status == "failed"
    assert updatedt_job.total_files == 0
    assert updatedt_job.error_message == "No files returned from GitHub"


    mock_ack.call_count = 1 
    mock_ack.assert_called_once_with(
        "repo:fetch",
        "fetch-workers",
        "fetch-worker-1",
        "message_id_123"
    )

    mock_publish.call_count = 0 



async def test_max_retires_exceeded(mocker, db_session,test_repo, test_job):
    mock_publish = mocker.patch("src.workers.repo_fetch.redis_manager.publish")
    mock_ack = mocker.patch("src.workers.repo_fetch.redis_manager.ack")
    mock_dead_letter = mocker.patch("src.workers.repo_fetch.redis_manager.dead_letter")

    mock_files = [
        {"path": "/src/hello.py" ,"language": "python", "content":"hello world"},
        {"path": "/src/server.js" ,"language": "javascript", "content":"hello world"},

    ]
    mocker.patch(
        "src.workers.repo_fetch.fetch_repo_files", 
        return_value=mock_files
    )
    error_msg = "Github API is completely down"
    mocker.patch(
        "src.workers.repo_fetch.fetch_repo_files", 
        side_effect=Exception(error_msg.lower())
    )
    payload = {
        "repo_id": str(test_repo.id),
        "job_id": str(test_job.id),
        "repo_url":test_repo.repo_url,
        "retries": "3"
    }

    await process_fetch_message("message_id_123", payload)

    repo_result = await db_session.execute(select(Repo).where(Repo.id == test_repo.id))
    updated_repo = repo_result.scalar_one_or_none()

    job_result = await db_session.execute(select(Job).where(Job.id == test_job.id))
    updatedt_job = job_result.scalar_one_or_none()


    assert updated_repo.status == "failed"
    assert updated_repo.error_message == error_msg.lower()

    assert updatedt_job.status == "failed"
    assert updatedt_job.total_files == 0
    assert updatedt_job.error_message == error_msg.lower()

    mock_dead_letter.assert_called_once_with("repo:fetch", payload,error_msg.lower() ,reason="Max retries reached")
    mock_publish.call_count = 0 
    mock_ack.call_count = 1 
    mock_ack.assert_called_once_with(
        "repo:fetch",
        "fetch-workers",
        "fetch-worker-1",
        "message_id_123"
    )






    
