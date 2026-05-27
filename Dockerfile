FROM python:3.11-slim

WORKDIR /app

# Install any system deps needed
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python deps
COPY render_bundle/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy monolithic backend + pre-built frontend static files
COPY render_bundle/main.py .
COPY render_bundle/gateway_app ./gateway_app
COPY render_bundle/orch_app ./orch_app
COPY render_bundle/search_app ./search_app
COPY render_bundle/pricing_app ./pricing_app
COPY render_bundle/shared ./shared
COPY render_bundle/static ./static

# Koyeb and most platforms inject PORT; default to 8000
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
