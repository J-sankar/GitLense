SHELL := /bin/bash

.PHONY: server worker-s worker-m worker-l cleanup stop

server:
	source .venv/bin/activate && uvicorn main:app --reload

worker-repo-fetch:
	source .venv/bin/activate && python -m src.workers.repo_fetch

worker-file-process:
	source .venv/bin/activate && python -m src.workers.file_process

worker-file-store:
	source .venv/bin/activate && python -m src.workers.file_store

cleanup:
	@read -p "Enter Repo ID to wipe: " repo_id; \
	python -m scripts.repo_cleanup $$repo_id

stop:
	@echo "Killing all uvicorn and worker processes..."
	-pkill -f uvicorn
	-pkill -f repo_fetch.py
	@echo "Cleaned."	


reset-redis:
	@echo "Flushing Redis queues..."
	redis-cli flushall
	@echo "Redis is clean."