FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    ffmpeg \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Build frontend → static files served by Flask
RUN cd frontend && npm ci && npm run build

RUN mkdir -p /app/assets

EXPOSE 5000

CMD bash -c "flask db upgrade 2>/dev/null; python -c 'from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()' && gunicorn -w 4 -b 0.0.0.0:5000 'app:create_app()'"
