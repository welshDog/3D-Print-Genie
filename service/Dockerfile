# Print Genie glue service — Phase 2/3. Multi-arch friendly (runs on the Pi alongside PrintGuard).
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8011
# NB: python:3.11-slim has no curl/ps — keep healthchecks dependency-free if added later.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8011"]
