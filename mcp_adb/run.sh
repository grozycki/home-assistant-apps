#!/usr/bin/with-contenv bashio

mkdir -p /data/.android

export HOME=/data
export ADB_VENDOR_KEYS=/data/.android/adbkey

# shellcheck disable=SC2155
export DEVICE_IP=$(bashio::config 'device_ip')
# shellcheck disable=SC2155
export PORT=$(bashio::config 'port')

export HOME=/data
export ADB_VENDOR_KEYS=/data/.android

adb kill-server || true

bashio::log.info "Starting MCP ADB app..."

exec python3 /main.py