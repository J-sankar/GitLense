# GitLense API

A FastAPI-powered application for analyzing and querying codebases with AI-driven code understanding capabilities.

## Features

- **Code Analysis**: Parse and analyze source code using tree-sitter
- **GitHub Integration**: Connect and analyze GitHub repositories
- **AI-Powered Queries**: Query codebases using semantic search powered by VoyageAI embeddings
- **Background Job Processing**: Asynchronous job execution using Redis and RQ
- **User Authentication**: Secure authentication with JWT tokens and bcrypt
- **Database Storage**: PostgreSQL backend with SQLAlchemy ORM

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Task Queue**: Redis + RQ for background jobs
- **Code Parsing**: Tree-sitter (with Python support)
- **AI/Embeddings**: VoyageAI
- **Authentication**: JWT + bcrypt
- **GitHub Integration**: PyGithub

## Prerequisites

- Python >= 3.10
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
JWT_SECRET_KEY=your-secret-key-here
GITHUB_TOKEN=your-github-token
VOYAGE_API_KEY=your-voyage-api-key
```

4. Initialize the database:
```bash
python -m app.core.database  # Create tables
```

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

## Development

### Running Tests

```bash
pytest test/
```

### Code Quality

Ensure code follows project standards and passes all tests before committing.


```





