from app.core.qdrant import qdrant_client as client
from qdrant_client import models

collection_name="repo_9d87b3c0-c72f-4a69-994c-620d0fbdd447"
client.create_payload_index(
            collection_name=collection_name,
            field_name="file",
            field_schema=models.KeywordIndexParams(
                type="keyword"
            )
        )
print(f"Created collection and payload index for {collection_name}")