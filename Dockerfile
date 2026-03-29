FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PORT=7860 \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    API_RELOAD=false \
    CMSVS_API_URL=http://127.0.0.1:8000

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 user

WORKDIR $HOME/app

COPY requirements.txt .

RUN pip install --upgrade pip && pip install -r requirements.txt

COPY --chown=user:user . .

RUN chmod +x $HOME/app/scripts/start_space.sh

USER user

EXPOSE 7860 8000

CMD ["/home/user/app/scripts/start_space.sh"]
