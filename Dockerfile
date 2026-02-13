FROM python:3.11-slim

WORKDIR /app

# Install dependencies including op CLI
RUN apt-get update && apt-get install -y curl && \
    curl -sS https://downloads.1password.com/linux/stable/x86_64/1password-latest.x86_64 -o /usr/local/bin/1password && \
    chmod +x /usr/local/bin/1password && \
    ln -s /usr/local/bin/1password /usr/local/bin/op && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . .

# Create data directory
RUN mkdir -p /data

# Default command
CMD ["python", "main.py"]
