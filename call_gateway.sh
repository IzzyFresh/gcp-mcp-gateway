#!/bin/bash

# Helper script to call the MCP Gateway
# Usage: ./call_gateway.sh <endpoint> <json_payload>
# Example: ./call_gateway.sh /list-tools '{"service": "bigquery.googleapis.com"}'

ENDPOINT=$1
PAYLOAD=$2

if [ -z "$ENDPOINT" ] || [ -z "$PAYLOAD" ]; then
  echo "Usage: $0 <endpoint> <json_payload>"
  echo "Example: $0 /list-tools '{\"service\": \"bigquery.googleapis.com\"}'"
  exit 1
fi

# TODO: Replace with your actual deployed Gateway URL
GATEWAY_URL="https://your-mcp-gateway-url.run.app"
API_KEY="default_secret_key" # Update if changed in your deployment

TOKEN=$(gcloud auth print-identity-token 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "Error: Failed to get OIDC token from gcloud. Are you logged in?"
  exit 1
fi

curl -s -X POST -H "Authorization: Bearer $TOKEN" \
     -H "X-API-Key: $API_KEY" \
     -H "Content-Type: application/json" \
     -d "$PAYLOAD" \
     "$GATEWAY_URL$ENDPOINT"
