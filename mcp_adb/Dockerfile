ARG BUILD_FROM=ghcr.io/home-assistant/base:latest
FROM $BUILD_FROM

ENV PYTHONUNBUFFERED=1
ENV HOME=/data
ENV ADB_VENDOR_KEYS=/data/.android/adbkey

ENV VIRTUAL_ENV="/opt/venv"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN \
  apk add --no-cache \
    python3 \
    py3-uv \
    android-tools

RUN python3 -m venv $VIRTUAL_ENV

RUN uv pip install fastmcp adbutils zeroconf

WORKDIR /data

COPY run.sh /
COPY main.py /
COPY remote_tools.py /
COPY adb_discovery.py /
COPY app_tools.py /
COPY device_manager.py /
COPY pairing_tools.py /
COPY system_tools.py /
COPY app_resources.py /
COPY guides/ /guides/

RUN chmod a+x /run.sh

CMD [ "/run.sh" ]