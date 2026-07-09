FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY frontend ./frontend
COPY eval ./eval
COPY sample_docs ./sample_docs
COPY scripts ./scripts

RUN useradd --create-home appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn","app.main_with_ui:app","--host","0.0.0.0","--port","8000", "--workers","2"]