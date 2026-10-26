FROM postgres:16.15-bookworm@sha256:d81f7b51697014367236d07ec58b54153fc28f828b72bf247fe5c7487520bcb0 AS pgtools
FROM python:3.12.15-slim-bookworm@sha256:6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70 AS deps
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 libreadline8 liblz4-1 libzstd1 && rm -rf /var/lib/apt/lists/*
COPY --from=pgtools /usr/lib/postgresql/16/bin/pg_dump /usr/lib/postgresql/16/bin/pg_restore /usr/lib/postgresql/16/bin/psql /usr/lib/postgresql/16/bin/
COPY --from=pgtools /usr/lib/*-linux-gnu/libpq.so.5* /usr/local/lib/
RUN ldconfig && groupadd --gid 10001 commerceguard && useradd --uid 10001 --gid 10001 --no-create-home commerceguard
WORKDIR /app
COPY requirements-web.lock /app/
RUN python -m pip install --no-cache-dir --require-hashes -r requirements-web.lock && python -m pip check

FROM deps AS full-deps
COPY requirements-analytics.lock requirements-orchestration.lock /app/
RUN python -m venv /opt/analytics && /opt/analytics/bin/pip install --no-cache-dir --require-hashes -r requirements-analytics.lock && /opt/analytics/bin/pip check
RUN python -m venv /opt/orchestration && /opt/orchestration/bin/pip install --no-cache-dir --require-hashes -r requirements-orchestration.lock && /opt/orchestration/bin/pip check

FROM deps AS web
COPY commerceguard /app/commerceguard
COPY analytics /app/analytics
COPY deploy/entrypoint.py /app/deploy/entrypoint.py
RUN mkdir -p /var/lib/commerceguard/raw /var/lib/commerceguard/tmp /var/lib/commerceguard/backups && chown -R 10001:10001 /var/lib/commerceguard && dpkg-query -W > /app/os-packages.txt
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 COMMERCEGUARD_INTERNAL_NETWORK=1
USER 10001:10001
ENTRYPOINT ["python","/app/deploy/entrypoint.py"]
CMD ["web"]

FROM web AS full
COPY --from=full-deps /opt/analytics /opt/analytics
COPY --from=full-deps /opt/orchestration /opt/orchestration
COPY --from=full-deps /app/requirements-analytics.lock /app/requirements-orchestration.lock /app/
