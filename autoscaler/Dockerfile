FROM python:3.11-slim

WORKDIR /app

RUN pip install docker prometheus-client

COPY autoscaler.py .

CMD ["python", "autoscaler.py"]