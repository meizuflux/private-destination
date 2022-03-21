FROM python:3.10-slim-buster
LABEL maintainer meizuflux

COPY requirements.txt ./requirements.txt

RUN apt-get update \
    && apt-get install -y git \
    && apt-get clean && rm -rf /var/cache/apt/* && rm -rf /var/lib/apt/lists/* && rm -rf /tmp/* \
    && pip install -r requirements.txt

COPY . .

WORKDIR /

CMD gunicorn app:app_factory --bind 0.0.0.0:8000 --worker-class aiohttp.GunicornUVLoopWebWorker

EXPOSE 8000