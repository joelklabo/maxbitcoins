FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y curl && \
    curl -sS https://app.1password.com/downloads/1password-cli/1password-cli-latest.deb -o /tmp/1password-cli.deb && \
    dpkg -i /tmp/1password-cli.deb || apt-get install -f -y && \
    rm /tmp/1password-cli.deb && \
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
