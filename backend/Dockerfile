FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd --create-home appuser
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
RUN mkdir -p /app/exports && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
