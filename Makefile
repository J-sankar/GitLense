SHELL := /bin/bash

.PHONY: server worker-s worker-m worker-l cleanup stop

server:
	source .venv/bin/activate && uvicorn main:app --reload

worker-s:
	source .venv/bin/activate && python worker.py small

worker-m:
	source .venv/bin/activate && python worker.py medium

worker-l:
	source .venv/bin/activate && python worker.py large

cleanup:
	@read -p "Enter Repo ID to wipe: " repo_id; \
	python -m scripts.repo_cleanup $$repo_id

stop:
	@echo "Killing all uvicorn and worker processes..."
	-pkill -f uvicorn
	-pkill -f worker.py
	@echo "Cleaned."	


reset-redis:
	@echo "Flushing Redis queues..."
	redis-cli flushall
	@echo "Redis is clean."