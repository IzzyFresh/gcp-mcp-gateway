# Gemini Skill: Centralized MCP Gateway Usage

This skill file documents how to use the Centralized MCP Gateway deployed on Cloud Run.

## Overview
The MCP Gateway acts as a hub for all available Google Cloud MCP servers in the project. It automatically discovers services and routes requests to them. It also supports manually added custom services.

## Gateway URL
`https://your-mcp-gateway-url.run.app`

## Authentication
The gateway is secured with two layers:
1.  **Cloud IAM:** Requires a Google OIDC token (no unauthenticated invocations allowed).
2.  **API Key:** Requires a custom header `X-API-Key`.

## Supported Custom Services
*   **`looker-mcp`**: Custom Looker MCP server.
*   **`looker-mcp-linux`**: Custom Looker MCP server for Linux environment.

## Usage Rules

### 1. Discovering Services
To get the list of all services (auto-discovered + custom):
```bash
TOKEN=$(gcloud auth print-identity-token)
curl -H "Authorization: Bearer $TOKEN" \
     -H "X-API-Key: <YOUR_API_KEY>" \
     https://your-mcp-gateway-url.run.app/services
```

### 2. Listing Tools for a Service
To list tools available for a specific service:
```bash
TOKEN=$(gcloud auth print-identity-token)
curl -X POST -H "Authorization: Bearer $TOKEN" \
     -H "X-API-Key: <YOUR_API_KEY>" \
     -H "Content-Type: application/json" \
     -d '{"service": "looker-mcp"}' \
     https://your-mcp-gateway-url.run.app/list-tools
```

### 3. Calling a Tool
To call a tool (e.g., `execute_sql_readonly` on BigQuery):
```bash
TOKEN=$(gcloud auth print-identity-token)
curl -X POST -H "Authorization: Bearer $TOKEN" \
     -H "X-API-Key: <YOUR_API_KEY>" \
     -H "Content-Type: application/json" \
     -d '{
       "service": "bigquery.googleapis.com",
       "tool_name": "execute_sql_readonly",
       "arguments": {
         "projectId": "YOUR_PROJECT_ID",
         "query": "SELECT COUNT(*) FROM `YOUR_PROJECT_ID.your_dataset.your_table`"
       }
     }' \
     https://your-mcp-gateway-url.run.app/call-tool
```

## Configuration
The default API key is set to `default_secret_key`. You should update the `MCP_GATEWAY_API_KEY` environment variable in the Cloud Run service settings to a secure value.
