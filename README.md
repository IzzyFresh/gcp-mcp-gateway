# Centralized MCP Gateway

This repository contains the code and configuration for a Centralized Model Context Protocol (MCP) Gateway designed to run on Google Cloud Platform (GCP), specifically on Cloud Run. It helps teams share and access MCP servers across different environments (like CloudTop VMs or local setups).

## Overview

The MCP Gateway acts as a hub for available MCP servers. It:
- Automatically discovers services registered in GCP (using the Service Usage API).
- Supports manually added custom services (like Looker MCP or GitHub MCP).
- Routes requests from clients to the appropriate MCP server.
- Handles authentication via Google OIDC and an optional custom API Key.

## Repository Structure

- `main.py`: The FastAPI application that serves as the gateway.
- `mcp_client.py`: The client class that handles communication with backend MCP servers (HTTP and SSE).
- `Dockerfile`: Dockerfile for building the gateway image.
- `Dockerfile-github`: Dockerfile for a specific GitHub MCP server bridge (if needed).
- `call_gateway.sh`: A helper script to test calling the gateway.
- `cloudbuild-gateway.yaml`: Cloud Build configuration to build and push the gateway image.
- `requirements.txt`: Python dependencies.
- `skills/`: Directory to store shared skills or rules (e.g., `mcp_gateway_rules.md`).

## Setup and Deployment

### 1. Prerequisites
- A GCP Project.
- Google Cloud SDK installed and configured.
- Docker and Node.js (if running locally or modifying the Dockerfiles).

### 2. Activate MCPs in GCP
To allow the gateway to auto-discover services, you need to register them or ensure they are exposed in a way the discovery mechanism can find.
The current implementation in `mcp_client.py` uses the following endpoint for discovery:
`https://serviceusage.googleapis.com/v2beta/services?filter=mcp_server:urls`

Ensure your team's MCP servers are registered or listed such that this API returns them.
For custom servers not listed by the API, you can manually add them to the `discovered_services` dictionary in `main.py` (around line 40).

### 3. Build and Push the Image
Use Cloud Build to build the container image and push it to Artifact Registry.

1.  Update `cloudbuild-gateway.yaml` with your Artifact Registry repository name (replace `your-artifact-repo`).
2.  Run the following command:
    ```bash
    gcloud builds submit --config cloudbuild-gateway.yaml .
```

### 4. Deploy to Cloud Run
Deploy the image from Artifact Registry to Cloud Run.

```bash
gcloud run deploy mcp-gateway \
  --image us-central1-docker.pkg.dev/YOUR_PROJECT_ID/your-artifact-repo/mcp-gateway:latest \
  --platform managed \
  --region us-central1 \
  --no-allow-unauthenticated \
  --set-env-vars MCP_GATEWAY_API_KEY=your_secure_api_key
```
*Note: Replace `YOUR_PROJECT_ID`, `your-artifact-repo`, and `your_secure_api_key` with your actual values.*

## Usage

Use the provided `call_gateway.sh` script to interact with the gateway.

1.  Update the `GATEWAY_URL` in `call_gateway.sh` with your deployed Cloud Run URL.
2.  Update the `API_KEY` if you changed it from the default.

### Examples

**List tools for a service:**
```bash
./call_gateway.sh /list-tools '{"service": "bigquery.googleapis.com"}'
```

**Call a tool:**
```bash
./call_gateway.sh /call-tool '{
  "service": "bigquery.googleapis.com",
  "tool_name": "execute_sql_readonly",
  "arguments": {
    "projectId": "YOUR_PROJECT_ID",
    "query": "SELECT count(*) FROM `your_dataset.your_table`"
  }
}'
```

## Security Note

- **Sensitive Info Removed:** All specific project IDs, account numbers, and hardcoded URLs have been removed from this repository or replaced with placeholders (like `YOUR_PROJECT_ID` or `your-looker-mcp-server-url`).
- **API Key:** The default API key is `default_secret_key`. Ensure you change this in production by setting the `MCP_GATEWAY_API_KEY` environment variable on Cloud Run.
