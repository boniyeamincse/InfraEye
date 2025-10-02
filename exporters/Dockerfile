FROM python:3.9-slim

WORKDIR /app

COPY security_exporter.py .

RUN pip install --no-cache-dir requests

# Create a non-root user
RUN useradd --create-home --shell /bin/bash exporter

# Install required system tools
RUN apt-get update && apt-get install -y \
    net-tools \
    procps \
    && rm -rf /var/lib/apt/lists/*

USER exporter

EXPOSE 8001

CMD ["python3", "security_exporter.py"]