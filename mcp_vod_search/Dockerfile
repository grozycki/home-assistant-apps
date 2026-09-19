FROM ghcr.io/home-assistant/base:latest

# Install requirements for app
RUN \
  apk add --no-cache \
    python3 \
    py3-uv

# Create virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install fastmcp into the virtual environment using uv
RUN uv pip install fastmcp simple-justwatch-python-api

# Python 3 HTTP Server serves the current working dir
# So let's set it to our app persistent data directory.
WORKDIR /data

# Copy data for app
COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]

