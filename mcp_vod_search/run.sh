#!/usr/bin/with-contenv bashio

export COUNTRY=$(bashio::config 'country')
export LANGUAGE=$(bashio::config 'language')

# Start the MCP server
exec python3 /main.py
