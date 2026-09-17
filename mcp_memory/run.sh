#!/usr/bin/with-contenv bashio

bashio::log.info "Starting MCP Memory app..."

# Read user configuration from options.json using bashio
export DEFAULT_CATEGORY=$(bashio::config 'default_category')
bashio::log.info "Default memory category is set to: ${DEFAULT_CATEGORY}"

# Start the MCP server
exec python3 /main.py