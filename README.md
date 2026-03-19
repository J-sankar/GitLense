# GitLense API

A FastAPI-powered application for analyzing and querying codebases with AI-driven code understanding capabilities. It parses code using tree-sitter, generates embeddings for semantic search, and uses LLMs to answer questions about repositories.

## Features

- **Code Analysis**: Parse and analyze source code using tree-sitter (supports Python, JavaScript, TypeScript, Java, HTML, C, and Go)
- **GitHub Integration**: Connect and analyze GitHub repositories
- **AI-Powered Queries**: Query codebases using semantic search powered by embeddings (VoyageAI or Gemini)
- **Background Job Processing**: Asynchronous job execution using Redis and RQ
- **Database Storage**: PostgreSQL backend with SQLAlchemy ORM
- **Vector Storage**: Qdrant for efficient vector similarity search
- **LLM Integration**: Groq for generating answers to codebase queries
- **Code Compression**: zlib-based compression for storing code chunks

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Task Queue**: Redis + RQ for background jobs
- **Code Parsing**: Tree-sitter (multi-language support)
- **AI/Embeddings**: VoyageAI or Gemini
- **LLM**: Groq
- **Vector Database**: Qdrant
- **GitHub Integration**: PyGithub
- **Compression**: zlib

## Prerequisites

- Python >= 3.11
- PostgreSQL
- Redis
- Git

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd codebase-qa
```

2. Install dependencies using uv:
```bash
uv pip install -r requirements.txt
```

Or with pip:
```bash
pip install -e .
```

3. Set up environment variables:
Create a `.env` file in the project root with the following:
```
DATABASE_URL=postgresql://user:password@localhost:5432/codebase_qa
REDIS_URL=redis://localhost:6379
GITHUB_TOKEN=your-github-token
VOYAGE_API_KEY=your-voyage-api-key
GEMINI_API_KEY=your-gemini-api-key
GROQ_API_KEY=your-groq-api-key
QDRANT_URL=your-qdrant-url
QDRANT_API_KEY=your-qdrant-api-key
EMBEDDING_PROVIDER=voyage  # or 'gemini'
ENVIRONMENT=development
```

4. Initialize the database:
The database tables are created automatically on startup via FastAPI's lifespan event.

## Running the Application

Start the FastAPI development server:
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

### API Documentation

- **Swagger UI**: http://localhost:8000/docs

### Health Check
- `GET /health` - Check if the API is running

### Background Worker
To process ingestion jobs, run the worker in a separate terminal:
```bash
python worker.py
```

## Development

### Running Tests

```bash
pytest test/
```

### Code Quality

Ensure code follows project standards and passes all tests before committing.


```





