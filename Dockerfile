FROM python:3.9-slim

WORKDIR /app/bot

# Setup Telegram bot
COPY requirements.txt .
COPY app.py .
RUN pip install -r requirements.txt

# Start the application
CMD ["python", "app.py"]
