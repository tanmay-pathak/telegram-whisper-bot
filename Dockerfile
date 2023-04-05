FROM python:3.9-slim

WORKDIR /app

# Setup Whisper.cpp
RUN apt-get update && apt-get install -y git curl make gcc g++ ffmpeg
RUN git clone https://github.com/ggerganov/whisper.cpp.git /app
RUN /app/models/download-ggml-model.sh base
RUN make

WORKDIR /app/bot

# Setup Telegram bot
COPY requirements.txt .
COPY app.py .
COPY convert.sh .
RUN pip install -r requirements.txt

# Start the application
CMD ["python", "app.py"]
