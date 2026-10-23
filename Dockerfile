FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./
COPY templates/ ./templates/
COPY static/ ./static/
COPY favicon.svg ./static/favicon.svg

EXPOSE 5000

# Threads: a monitor chat answer can stream for minutes; it must not block the rest of the page
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--worker-class", "gthread", "--threads", "8", "--timeout", "120", "app:app"]