import pytest
import os
from app.ingestion.processor import _generate_summary
from app.services.summarizer import Summarizer


@pytest.fixture
def sample_python_metadata():
    return {
        "skeleton": ['function_definition: def exec_commands(api_instance):', 'function_definition: def main():'],
        "imports" : ['import time','from kubernetes import config','from kubernetes.client import Configuration','from kubernetes.client.api import core_v1_api','from kubernetes.client.rest import ApiException','from kubernetes.stream import stream'],
        "exports" : []
    }


@pytest.mark.asyncio
@pytest.mark.xfail
async def test_real_summarizer(sample_python_metadata):
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not found. Skipping live integration test.")

    response = _generate_summary(metadata=sample_python_metadata)
    assert response is not None
    