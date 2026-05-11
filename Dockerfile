FROM python:3.11-slim

# Install Node.js and npx for GitHub MCP
RUN apt-get update && apt-get install -y curl gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-install the GitHub server to speed up startup
RUN npm install -g @modelcontextprotocol/server-github

COPY . .
CMD exec uvicorn main:app --host 0.0.0.0 --port $PORT
