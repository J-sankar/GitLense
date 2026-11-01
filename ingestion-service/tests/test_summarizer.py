import pytest
import os
from src.ingestion.processor import _generate_summary
# from app.services.summarizer import Summarizer




@pytest.fixture
def sample_python_metadata():
    return {
        "skeleton": ['function_definition: def exec_commands(api_instance):', 'function_definition: def main():'],
        "imports" : ['import time','from kubernetes import config','from kubernetes.client import Configuration','from kubernetes.client.api import core_v1_api','from kubernetes.client.rest import ApiException','from kubernetes.stream import stream'],
        "exports" : []
    }
SKIP_HEAVY = os.getenv("SKIP_HEAVY_TESTS",0) == "1"
@pytest.mark.asyncio
@pytest.mark.skipif(condition=SKIP_HEAVY,reason="Skipping summarizer test to limit api usage")
@pytest.mark.xfail
async def test_real_summarizer(sample_python_metadata):
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not found. Skipping live integration test.")

    response = await _generate_summary(metadata=sample_python_metadata)
    assert response is not None
    