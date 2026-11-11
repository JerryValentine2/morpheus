FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements-preview.txt .
RUN pip install --no-cache-dir -r requirements-preview.txt
COPY api.py .
COPY runtime/ runtime/
COPY web/ web/
COPY config/ config/
RUN useradd --create-home --uid 10001 morpheus
USER morpheus
ENV PORT=8080 MORPHEUS_ENV=development
EXPOSE 8080
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 1 api:app"]
