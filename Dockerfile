FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    EVERKEEP_HOST=0.0.0.0 \
    EVERKEEP_PORT=8080

WORKDIR /app

COPY runtime/ ./runtime/
COPY scripts/ ./scripts/
COPY contracts/ ./contracts/
COPY db/ ./db/

RUN useradd --create-home --uid 10001 everkeep
USER everkeep

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2).read()"

CMD ["python", "runtime/everkeep_host.py"]
