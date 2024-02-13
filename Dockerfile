FROM python:3.9-slim

WORKDIR /app/bot

RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY app.py .

RUN pip install -r requirements.txt

WORKDIR /app/temp

CMD ["python", "/app/bot/app.py"]
