# Template MCP Server

A production-ready base template for building MCP (Model Context Protocol) servers using FastMCP.

## Features

- ✅ **FastMCP 2.x** - Latest FastMCP framework
- ✅ **Auto-Discovery** - Automatically discovers and loads all tools, resources, and prompts
- ✅ **Authentication** - Optional Bearer token authentication
- ✅ **Configurable Port** - Set via environment variable
- ✅ **Hot-Reload Config** - Changes to settings.yaml without restart
- ✅ **Docker Ready** - Complete Docker setup with health checks
- ✅ **Graceful Shutdown** - Handles SIGINT/SIGTERM properly
- ✅ **Example Patterns** - Clean examples for tool/resource/prompt

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/aviciot/template_mcp.git
cd template_mcp
cp .env.example .env
```

### 2. Configure

Edit `server/config/settings.yaml`:

```yaml
mcp:
  name: "your-mcp-name"
  description: "Your MCP description"
```

### 3. Run with Docker

```bash
docker-compose up -d
```

### 4. Test

```bash
# Health check
curl http://localhost:8100/healthz

# Version info
curl http://localhost:8100/version

# MCP endpoint (requires MCP client with SSE support)
# The MCP protocol endpoint is at http://localhost:8100/mcp
# Use an MCP client SDK to properly connect:
# - Claude Desktop
# - MCP Python SDK
# - MCP TypeScript SDK
```

**Note**: The MCP protocol uses Server-Sent Events (SSE) and requires proper session management. Direct curl requests won't work - use an MCP client SDK or configure Claude Desktop to connect.

## Project Structure

```
template_mcp/
├── server/
│   ├── config.py              # Configuration loader
│   ├── server.py              # Starlette app with auth
│   ├── mcp_app.py            # FastMCP instance
│   ├── config/
│   │   └── settings.yaml     # Configuration file
│   ├── tools/
│   │   └── example_tool.py   # Example tool
│   ├── resources/
│   │   └── example_resource.py  # Example resource
│   ├── prompts/
│   │   └── example_prompt.py    # Example prompt
│   └── utils/
│       └── import_utils.py   # Auto-discovery
├── docker-compose.yml
├── Dockerfile
└── .env.example
```

## Adding Your Own Tools

1. Create a new file in `server/tools/`:

```python
# server/tools/my_tool.py
from mcp_app import mcp

@mcp.tool()
async def my_tool(param: str) -> str:
    """Tool description"""
    return f"Result: {param}"
```

2. Restart the server - tool is automatically discovered!

## Adding Resources

```python
# server/resources/my_resource.py
from mcp_app import mcp

@mcp.resource("info://my-resource")
async def my_resource() -> str:
    """Resource description"""
    return "Resource content"
```

## Adding Prompts

```python
# server/prompts/my_prompt.py
from mcp_app import mcp

@mcp.prompt()
def my_prompt(context: str = "") -> str:
    """Prompt description"""
    return f"System prompt with {context}"
```

## Configuration

### Environment Variables

- `MCP_PORT` - Server port (default: 8100)
- `AUTO_DISCOVER` - Auto-load tools/resources/prompts (default: true)
- `AUTH_ENABLED` - Enable authentication (default: false)
- `AUTH_TOKEN` - Bearer token for authentication

### Settings File

Edit `server/config/settings.yaml` for:
- Server name and version
- Custom configuration
- Business logic

Use `${ENV_VAR}` syntax to reference environment variables:

```yaml
server:
  port: ${MCP_PORT:-8000}  # Default 8000 if not set
```

## Authentication

Enable authentication in `.env`:

```bash
AUTH_ENABLED=true
AUTH_TOKEN=your-secret-token
```

Then use Bearer token in requests:

```bash
curl -H "Authorization: Bearer your-secret-token" \
  http://localhost:8000/
```

## Development

### Run Without Docker

```bash
cd server
pip install -r requirements.txt
python server.py
```

### View Logs

```bash
docker-compose logs -f template_mcp
```

## License

MIT License - Free to use and modify

## Support

For issues or questions, please open an issue on GitHub.
