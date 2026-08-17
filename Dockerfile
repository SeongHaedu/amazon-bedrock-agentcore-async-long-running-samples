FROM public.ecr.aws/docker/library/python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir bedrock-agentcore

COPY main.py /app/main.py

ENV PORT=8080
EXPOSE 8080
CMD ["python", "/app/main.py"]
