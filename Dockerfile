FROM python:3.9-alpine3.19 as builder

WORKDIR /app

# Install only the necessary build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.9-alpine3.19

WORKDIR /app/bot

# Install only the minimal ffmpeg components needed for audio processing
RUN apk add --no-cache \
    ffmpeg-libs \
    ffmpeg

# Copy only the python packages we need from the builder
COPY --from=builder /root/.local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages

COPY app.py .

# Create temp directory with correct permissions
RUN mkdir -p /app/temp && chmod 777 /app/temp
WORKDIR /app/temp

CMD ["python", "/app/bot/app.py"]
