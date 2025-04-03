FROM python:3.11-slim

RUN apt-get update \
    && apt-get install curl openssl -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY ./payloads ./payloads
COPY ./server.py ./server.py
COPY --chmod=755 reqs.sh /app

# install requirements
RUN /app/reqs.sh

RUN python3 -m pip install -r requirements.txt

COPY --chmod=755 entrypoint.sh /app

EXPOSE 4444
ENTRYPOINT ["/app/entrypoint.sh"]