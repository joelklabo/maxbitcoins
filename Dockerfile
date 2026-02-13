FROM python:3.11-slim

WORKDIR /app

# Install curl and nak (nostr CLI)
RUN apt-get update && apt-get install -y curl && \
    curl -sL https://github.com/jeffthierch/nak/releases/download/v0.3.2/nak-0.3.2-x86_64-unknown-linux-musl.tar.gz | tar xz && \
    mv nak /usr/local/bin/ && \
    rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . .

# Create data directory
RUN mkdir -p /data

# Default command
CMD ["python", "main.py"]
