FROM ubuntu:latest
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y netcat-traditional openssl tcpdump curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the reverse shell script into the image
WORKDIR /app
COPY client.sh /app/client.sh
RUN chmod +x /app/client.sh

CMD ["/app/client.sh"]
