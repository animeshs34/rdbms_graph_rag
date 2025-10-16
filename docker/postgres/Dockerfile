FROM postgres:16

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    git \
    postgresql-server-dev-16 \
    ca-certificates \
    && git clone --depth 1 https://github.com/eulerto/wal2json.git /tmp/wal2json \
    && cd /tmp/wal2json \
    && make \
    && make install \
    && cd / \
    && rm -rf /tmp/wal2json \
    && apt-get purge -y --auto-remove \
    build-essential \
    git \
    postgresql-server-dev-16 \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

