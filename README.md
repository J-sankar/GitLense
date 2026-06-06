# Codebase QA (GitLense API)

This repository contains a small microservice-style system for codebase analysis, ingestion, and retrieval-augmented generation (RAG). It uses FastAPI services, background workers, Redis, PostgreSQL, and vector storage to parse repositories, create embeddings, and answer queries over code.

**High-level architecture**

- **API services**: lightweight FastAPI services that expose REST endpoints.
	- `auth-service/` — authentication service, user and token management.
	- `ingestion-service/` — repository fetchers, parsers, and ingestion pipelines that create documents and embeddings.
	- `rag-service/` — RAG endpoint(s) that combine semantic search with LLM reasoning to answer queries.
- **Workers**: background processing (see `worker.py` and `src/.../workers/`) for ingestion, indexing, and long-running tasks.
- **Data stores**:
	- PostgreSQL for relational data (models in each service under `models/`).
	- Redis for queues and rate-limiting.
	- Qdrant (or other vector DB) for vector similarity search used by semantic search.
- **Infrastructure**: `docker-compose.yml` can bring up services locally for development.

Repository layout (top-level)

- `auth-service/` — auth microservice (FastAPI, alembic migrations, pyproject)
- `ingestion-service/` — ingestion microservice (parsers, processors, workers)
- `rag-service/` — RAG API and helpers
- `main.py` — lightweight root entry (if present) for a combined run
- `worker.py` — simple worker runner for local development
- `docker-compose.yml`, `Dockerfile` — container orchestrations and images
- `scripts/` — utility scripts such as repository cleanup and seeding

Getting started (developer flow)

- Requirements: Python 3.11+, Docker & Docker Compose, PostgreSQL, Redis
- Recommended: create a Python virtual environment per-service (many services include a `pyproject.toml`).

Quick local run (using the Make tasks present in this repo)

Run the API server:

```bash
make server
```

Run background workers (small/medium/large queues):

```bash
make worker-s
make worker-m
make worker-l
```

Bring up everything with Docker Compose:

```bash
docker-compose up -d --build
```

Stop and reset local services:

```bash
make stop
make reset-redis
```

Environment variables

Each service expects configuration via env vars or a `.env` file. Typical variables include `DATABASE_URL`, `REDIS_URL`, provider API keys (e.g. embedding/LLM providers), and service-specific flags. Check each service's `core/config.py` for concrete names.

Testing

- Run service tests from the service folder or at repo root where tests are present:

```bash
pytest
```



Where to look next

- Authentication flows: [auth-service](auth-service)
- Ingestion & parsing: [ingestion-service](ingestion-service)
- RAG & retrieval: [rag-service](rag-service)
- Worker entrypoint: `worker.py`
- Docker and local orchestration: `docker-compose.yml`








