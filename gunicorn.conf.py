# Gunicorn configuration for large file streaming

# Server socket
bind = "0.0.0.0:5000"
workers = 4

# Timeouts - critical for large file downloads
timeout = 600  # 10 minutes for large file downloads
keepalive = 120  # Keep connections alive longer
graceful_timeout = 60

# Worker class - sync is fine for file streaming
worker_class = "sync"

# Disable buffering for streaming responses
forwarded_allow_ips = "*"

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
