FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY report_generator.py .

# Create reports directory
RUN mkdir -p /tmp/reports

CMD ["python3", "report_generator.py"]