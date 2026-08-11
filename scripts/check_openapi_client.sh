#!/bin/sh
set -eu

node scripts/generate_openapi_client.mjs --check
