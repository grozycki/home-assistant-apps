ARG BUILD_FROM=ghcr.io/home-assistant/base:latest
FROM $BUILD_FROM

RUN \
  apk add --no-cache \
    python3 \
    py3-uv

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN uv pip install --upgrade fastmcp duckduckgo-search trafilatura httpx

WORKDIR /data

COPY run.sh /
COPY main.py /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
