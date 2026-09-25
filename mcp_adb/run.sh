#!/usr/bin/with-contenv bashio

# shellcheck disable=SC2155
export DEVICE_IP=$(bashio::config 'device_ip')
export PORT=$(bashio::config 'port')

bashio::log.info "Starting MCP ADB app..."

exec python3 /main.py