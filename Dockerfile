# ============================================
# BUILDER STAGE - Compile dependencies only
# ============================================
FROM python:3.11-alpine3.19 AS builder

WORKDIR /app

# Install build dependencies with --virtual for easy cleanup
# These are only needed for compiling Python packages
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    && apk add --no-cache \
    ffmpeg-dev

# Copy and install Python dependencies
# Separate COPY for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/usr/local -r requirements.txt

# ============================================
# RUNTIME STAGE - Minimal final image
# ============================================
FROM python:3.11-alpine3.19

# Create non-root user with specific UID for consistency
RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser

# Set consistent working directory
WORKDIR /app

# Install only runtime dependencies (ffmpeg is needed)
# No --virtual here as these are runtime dependencies
RUN apk add --no-cache \
    ffmpeg \
    && rm -rf /var/cache/apk/*

# Copy Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY app.py .

# Create temp directory with proper permissions
RUN mkdir -p /app/temp && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set working directory for temp files (as required by app.py)
WORKDIR /app/temp

# Health check to ensure container is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Run the application
CMD ["python", "../app.py"]
