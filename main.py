from fastapi import FastAPI, HTTPException, Header, Depends, Request
from pydantic import BaseModel
from mcp_client import MCPClient
from contextlib import asynccontextmanager
import os
import google.auth
from google.cloud import secretmanager
import asyncio
import json
import subprocess
import logging
import shutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp_client = MCPClient()
discovered_services = {}

# Load API Key from environment
API_KEY = os.environ.get("MCP_GATEWAY_API_KEY", "default_secret_key")

def get_secret(secret_id):
    try:
        credentials, project_id = google.auth.default()
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.error(f"Error fetching secret {secret_id}: {e}")
        return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Discovering MCP servers...")
    try:
        global discovered_services
        discovered_services = mcp_client.discover_servers()
        # TODO: Replace with your actual service URLs or rely on auto-discovery
        discovered_services["looker-mcp"] = "https://your-looker-mcp-server-url.run.app/mcp"
        discovered_services["looker-mcp-linux"] = "https://your-looker-mcp-server-linux-url.run.app/mcp"
        discovered_services["github"] = "local://github"
        discovered_services["dataplex"] = "https://dataplex.googleapis.com/mcp"
        logger.info(f"Discovered {len(discovered_services)} services: {list(discovered_services.keys())}")
    except Exception as e:
        logger.error(f"Failed to discover services: {e}")
    yield
    discovered_services.clear()

app = FastAPI(lifespan=lifespan)

async def call_stdio_mcp(command, args, env, method, params, request_id=1):
    logger.info(f"Executing stdio MCP: {command} {args}")
    full_command = shutil.which(command) or command
    
    proc = await asyncio.create_subprocess_exec(
        full_command, *args,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, **env}
    )
    
    message = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": request_id
    }
    
    try:
        proc.stdin.write(json.dumps(message).encode() + b"\n")
        await proc.stdin.drain()
        
        line = await asyncio.wait_for(proc.stdout.readline(), timeout=30.0)
        if line:
            return json.loads(line.decode())
    except asyncio.TimeoutError:
        logger.error("Timeout waiting for stdio MCP response")
        return {"error": "Timeout waiting for response from MCP server"}
    except Exception as e:
        logger.error(f"Error in stdio MCP: {e}")
        return {"error": str(e)}
    finally:
        if proc.returncode is None:
            proc.terminate()
            await proc.wait()
            
    return {"error": "No response from MCP server"}

class ListToolsRequest(BaseModel):
    service: str

class CallToolRequest(BaseModel):
    service: str
    tool_name: str
    arguments: dict

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/list-tools")
async def list_tools(request: ListToolsRequest, r: Request):
    service_url = discovered_services.get(request.service)
    if not service_url:
        raise HTTPException(status_code=404, detail=f"Service {request.service} not found.")
    
    if service_url == "local://github":
        token = get_secret("GITHUB_PERSONAL_ACCESS_TOKEN")
        if not token:
             raise HTTPException(status_code=500, detail="Secret not found")
        env = {"GITHUB_PERSONAL_ACCESS_TOKEN": token}
        result = await call_stdio_mcp("npx", ["-y", "@modelcontextprotocol/server-github"], env, "tools/list", {})
        return result
    
    try:
        result = mcp_client.list_tools(service_url)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/call-tool")
async def call_tool(request: CallToolRequest, r: Request):
    service_url = discovered_services.get(request.service)
    if not service_url:
        raise HTTPException(status_code=404, detail=f"Service {request.service} not found.")
    
    if service_url == "local://github":
        token = get_secret("GITHUB_PERSONAL_ACCESS_TOKEN")
        if not token:
             raise HTTPException(status_code=500, detail="Secret not found")
        env = {"GITHUB_PERSONAL_ACCESS_TOKEN": token}
        params = {"name": request.tool_name, "arguments": request.arguments}
        result = await call_stdio_mcp("npx", ["-y", "@modelcontextprotocol/server-github"], env, "tools/call", params)
        return result
    
    try:
        result = mcp_client.call_tool(service_url, request.tool_name, request.arguments)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
