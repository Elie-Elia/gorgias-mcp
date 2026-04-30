# Gorgias MCP Server

MCP server for Gorgias MCP Server

## Setup

```bash
# Install dependencies
uv sync

# Copy environment file
cp .env.example .env

# Edit .env with your values
```

## Local Development

```bash
# Run the server
./run.sh

# Or directly
uv run gorgias-mcp-server
```


## Authentication

This server uses a developer-provided API key. Set `API_KEY` in your `.env` file.

Users don't need to provide any credentials - the API key is managed by the server.


## Tools

- `example_tool` - Example tool demonstrating credential usage
