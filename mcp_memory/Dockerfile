ARG BUILD_FROM=ghcr.io/home-assistant/base:latest
FROM $BUILD_FROM

RUN \
  apk add --no-cache \
    python3 \
    py3-pip \
    python3-dev

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install MCP, vector database, and embedding tools
RUN pip3 install --no-cache-dir \
    mcp \
    uvicorn

WORKDIR /data

COPY run.sh /
COPY main.py /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]