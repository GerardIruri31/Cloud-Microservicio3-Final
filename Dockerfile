FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=America/Lima

RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# estos paths son relativos al contexto ApifyConnection/
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# copia solo el código (no el .env)
COPY app/*.py /app/

EXPOSE 8000
CMD ["uvicorn", "ApifyConnectionController:app", "--host", "0.0.0.0", "--port", "8000"]
