# ---------- stage 1: build ----------
FROM python:3.12-slim AS builder

WORKDIR /app

# install dependencies into a virtual env so we can copy it to the final image
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ---------- stage 2: runtime ----------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# run as a normal user, not root
RUN useradd --create-home appuser

COPY --from=builder /opt/venv /opt/venv
COPY main.py .

USER appuser

EXPOSE 8000

# slim image has no curl, so use python for the check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
