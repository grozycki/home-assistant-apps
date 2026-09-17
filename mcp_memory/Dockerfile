ARG BUILD_FROM=ghcr.io/home-assistant/base:latest
FROM $BUILD_FROM

# Install system dependencies and Python
RUN \
  apk add --no-cache \
    python3 \
    py3-pip \
    build-base \
    python3-dev

# Create a virtual environment to prevent PEP 668 conflicts
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install MCP, vector database, and embedding tools
RUN pip3 install --no-cache-dir \
    mcp[cli] \
    chromadb \
    sentence-transformers \
    uvicorn

# Set working directory to the persistent data folder
WORKDIR /data

# Copy execution script and python application
COPY run.sh /
COPY main.py /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]