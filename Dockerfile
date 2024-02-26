FROM python:3.10-bookworm

WORKDIR /app/bot

RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py .

WORKDIR /app/temp

CMD ["python", "/app/bot/app.py"]
