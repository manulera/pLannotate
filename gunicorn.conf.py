"""Gunicorn settings for the API container, configured through the environment."""

import os

bind = "0.0.0.0:8000"
worker_class = "uvicorn_worker.UvicornWorker"
workers = int(os.environ.get("PLANNOTATE_WORKERS", 2))
# seconds without a heartbeat before a worker is killed and replaced
timeout = int(os.environ.get("PLANNOTATE_TIMEOUT", 300))
graceful_timeout = 30
