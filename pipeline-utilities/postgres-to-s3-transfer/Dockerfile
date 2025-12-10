FROM debian:stable-slim
RUN apt-get update && apt-get install -y postgresql-client awscli && rm -rf /var/lib/apt/lists/*
COPY postgres-to-s3-transfer.sh /postgres-to-s3-transfer.sh
ENTRYPOINT ["/bin/bash", "/postgres-to-s3-transfer.sh"]
