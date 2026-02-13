FROM python:3.11-slim

WORKDIR /app

# Install dependencies including op CLI
RUN apt-get update && apt-get install -y curl gnupg && \
    curl -sS https://downloads.1password.com/linux/keys/1password.asc | gpg --dearmor -o /usr/share/keyrings/1password-archive-keyring.gpg && \
    echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/1password-archive-keyring.gpg] https://downloads.1password.com/linux/debian stable main' > /etc/apt/sources.list.d/1password.list && \
    apt-get update && apt-get install -y 1password-cli && \
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
