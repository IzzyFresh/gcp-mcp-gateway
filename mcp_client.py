import httpx
import google.auth
from google.auth.transport.requests import Request
import google.oauth2.id_token
import json

class MCPClient:
    def __init__(self):
        self.credentials, self.project_id = google.auth.default()
        # Enable follow_redirects to handle 307 redirects from Cloud Run/FastAPI
        # Increase default timeout to 60 seconds for slow backend services
        self.client = httpx.Client(follow_redirects=True, timeout=60.0)

    def _get_token(self):
        if not self.credentials.valid:
            self.credentials.refresh(Request())
        return self.credentials.token

    def _get_oidc_token(self, audience: str):
        auth_req = Request()
        id_token = google.oauth2.id_token.fetch_id_token(auth_req, audience)
        return id_token

    def call_method(self, url: str, method: str, params: dict = None, request_id: int = 1):
        if url.endswith("/sse"):
            return self.call_sse_method(url, method, params, request_id)
        else:
            return self.call_http_method(url, method, params, request_id)

    def _get_headers(self, url: str):
        if ".run.app" in url:
            parts = url.split('/')
            audience = "/".join(parts[:3])
            token = self._get_oidc_token(audience)
        else:
            token = self._get_token()
            
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def call_http_method(self, url: str, method: str, params: dict = None, request_id: int = 1):
        headers = self._get_headers(url)
        
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id
        }
        if params:
            payload["params"] = params
            
        response = self.client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()

    def call_sse_method(self, url: str, method: str, params: dict = None, request_id: int = 1):
        headers = self._get_headers(url)
        
        # 1. Connect to SSE endpoint (GET)
        get_headers = headers.copy()
        if "Content-Type" in get_headers:
            del get_headers["Content-Type"]
            
        with self.client.stream("GET", url, headers=get_headers) as response:
            response.raise_for_status()
            
            post_url = None
            # Use a single loop to read the stream to avoid "content already streamed" error
            for line in response.iter_lines():
                if line.startswith("event: endpoint"):
                    continue
                elif line.startswith("data: "):
                    if not post_url:
                        post_url = line[6:]
                        # Fix relative URLs
                        if not post_url.startswith("http"):
                            parts = url.split('/')
                            base_url = "/".join(parts[:3])
                            post_url = base_url + post_url
                        
                        # 2. Send POST request with JSON-RPC payload
                        payload = {
                            "jsonrpc": "2.0",
                            "method": method,
                            "id": request_id
                        }
                        if params:
                            payload["params"] = params
                            
                        post_response = self.client.post(post_url, headers=headers, json=payload)
                        post_response.raise_for_status()
                        
                        # Continue loop to wait for response on the same stream
                        continue
                    else:
                        # This is data after post_url was found, likely the response
                        data_str = line[6:]
                        try:
                            data = json.loads(data_str)
                            if data.get("id") == request_id:
                                return data
                        except:
                            pass
                        
        raise Exception("Timed out or failed to receive response on SSE stream")

    def list_tools(self, url: str):
        return self.call_method(url, "tools/list")

    def call_tool(self, url: str, tool_name: str, arguments: dict):
        params = {
            "name": tool_name,
            "arguments": arguments
        }
        return self.call_method(url, "tools/call", params)

    def discover_servers(self):
        url = "https://serviceusage.googleapis.com/v2beta/services?filter=mcp_server:urls"
        token = self._get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        response = self.client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        services = {}
        for item in data.get("services", []):
            mcp_info = item.get("mcpServer")
            if mcp_info and mcp_info.get("urls"):
                name = mcp_info.get("name")
                urls = mcp_info.get("urls")
                if name and urls:
                    mcp_url = urls[0]
                    if not mcp_url.startswith("http"):
                        mcp_url = f"https://{mcp_url}"
                    services[name] = mcp_url
        return services
