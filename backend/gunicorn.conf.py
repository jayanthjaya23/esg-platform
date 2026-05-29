"""
Gunicorn production configuration for ESG Analytics Platform on Render.
"""
import multiprocessing
import os

# ─── Server socket ───────────────────────────────────────────────────────────
# Bind is passed via --bind flag in start command; keep port dynamic via $PORT
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# ─── Workers ─────────────────────────────────────────────────────────────────
# Render free tier: 512 MB RAM — keep workers low
workers = min(multiprocessing.cpu_count() * 2 + 1, 4)
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 5

# ─── Logging ─────────────────────────────────────────────────────────────────
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sµs'

# ─── Process naming ──────────────────────────────────────────────────────────
proc_name = "esg_analytics"

# ─── Server mechanics ────────────────────────────────────────────────────────
preload_app = True
daemon = False
pidfile = None

# ─── Limits ──────────────────────────────────────────────────────────────────
max_requests = 1000
max_requests_jitter = 100
graceful_timeout = 30