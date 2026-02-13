FROM python:3.11-slim

WORKDIR /app

# Install nak CLI
RUN pip install --no-cache-dir nak

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . .

# Create data directory
RUN mkdir -p /data

# Default command
CMD ["python", "main.py"]
