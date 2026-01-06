# Template MCP Server

> **🎯 Purpose**: Production-ready base template for building MCP (Model Context Protocol) servers using FastMCP 2.x
> 
> **👥 Audience**: Developers creating new MCP servers, LLMs assisting with MCP development
>
> **📖 Complete Specification**: See [SPEC.md](SPEC.md) for detailed patterns and rules

---

## 📋 Table of Contents

- [What is This?](#what-is-this)
- [Features](#features)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Creating Your MCP](#creating-your-mcp)
- [Knowledge Base Setup](#knowledge-base-setup)
- [Traefik Gateway Integration](#traefik-gateway-integration)
- [Development Guide](#development-guide)
- [Testing](#testing)
- [Deployment](#deployment)
- [For LLMs](#for-llms)

---

## 🎯 What is This?

This is a **template repository** for creating MCP servers. It includes:

✅ **Hot-reload capable server.py** - Never manually restart during development  
✅ **Auto-discovery** - Tools/resources/prompts automatically loaded  
✅ **Structured logging** - Correlation IDs, request tracking, JSON output  
✅ **Knowledge base system** - Built-in help tools for LLM consumption  
✅ **Traefik-ready** - Optional gateway integration (commented labels)  
✅ **Production patterns** - Auth, rate limiting, health checks, graceful shutdown  

### 🔑 Key Principle

**Keep important files unchanged** (server.py, mcp_app.py, config.py). These provide:
- Hot reload functionality
- Auto-discovery of tools
- Structured logging
- Request tracking

**Customize these**:
- `server/config/settings.yaml` - Your configuration
- `server/tools/*.py` - Your tools
- `server/knowledge_base/*.md` - Your documentation
- `docker-compose.yml` labels - Traefik if needed

---

## ✨ Features

### Core Infrastructure
- ✅ **FastMCP 2.x** - Latest framework with proper SSE/HTTP support
- ✅ **Auto-Discovery** - Automatically loads all tools, resources, prompts
- ✅ **Hot Reload** - Code changes detected, server reloads (uvicorn --reload)
- ✅ **Request Logging** - Every request logged with correlation ID
- ✅ **Error Handling** - Comprehensive patterns in all tools

### Configuration & Validation
- ✅ **Config Validation** - Validates settings.yaml on startup (fail fast)
- ✅ **Multi-Environment** - Separate configs for dev/prod
- ✅ **Environment Variables** - .env support with template

### Security & Operations
- ✅ **Multiple Auth Methods** - Bearer token, API Key, Basic Auth
- ✅ **Health Checks** - `/healthz` (simple) and `/health/deep` (thorough)
- ✅ **Rate Limiting** - Optional middleware for API protection
- ✅ **Graceful Shutdown** - Handles SIGINT/SIGTERM properly

### Developer Experience
- ✅ **Knowledge Base System** - Built-in help tools for documentation
- ✅ **Testing Framework** - Pytest examples and patterns
- ✅ **Database Template** - Connection pooling pattern included
- ✅ **Structured Logging** - JSON or text format
- ✅ **Docker Ready** - Complete Docker setup with health checks

### Gateway Integration
- ✅ **Traefik-Ready** - Commented labels for easy gateway setup
- ✅ **Path-based Routing** - Each MCP gets /mcp-name prefix
- ✅ **Health Check Integration** - Load balancer health checks

### LLM Development
- ✅ **Comprehensive SPEC.md** - Complete patterns for LLM-assisted development
- ✅ **Template Files** - Knowledge base templates included
- ✅ **Clear Structure** - Predictable organization for code generation

---

## 🚀 Quick Start

### 1. Clone the Template

```bash
git clone https://github.com/yourusername/template_mcp.git my-new-mcp
cd my-new-mcp
rm -rf .git  # Remove template git history
git init     # Start fresh
```

### 2. Set Up Environment

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Key variables to customize**:
```bash
MCP_CONTAINER_NAME=my_mcp        # Docker container name
MCP_NAME=my-mcp                   # Service name (used in paths)
MCP_PORT=8100                     # External port
AUTH_ENABLED=false                # Enable auth if needed
USE_TRAEFIK=false                 # Set true if using gateway
```

### 3. Configure Your MCP

Edit `server/config/settings.yaml`:

```yaml
mcp:
  name: "My MCP Server"
  version: "1.0.0"
  description: "Description of what your MCP does"

# Add your custom configuration sections
database:
  host: "localhost"
  port: 5432
  
api:
  endpoint: "https://api.example.com"
  timeout: 30
```

### 4. Run with Docker

```bash
# Build and start
docker-compose up -d

# Check logs
docker-compose logs -f

# Check health
curl http://localhost:8100/healthz
```

### 5. Verify It Works

```bash
# Simple health check
curl http://localhost:8100/healthz
# Expected: OK

# Deep health check
curl http://localhost:8100/health/deep
# Expected: JSON with detailed status

# Version info
curl http://localhost:8100/version
# Expected: JSON with version, tools count, etc.
```

---

## 📁 Project Structure

```
template_mcp/
├── .env.example                      # Environment variables template
├── .gitignore                        # Git ignore rules
├── docker-compose.yml                # Docker Compose (Traefik-ready)
├── Dockerfile                        # Container definition
├── LICENSE                           # MIT License
├── README.md                         # This file
├── SPEC.md                          # ⭐ Technical spec for LLMs
│
└── server/                          # Python application
    ├── __init__.py                  # Package marker
    ├── server.py                    # ⭐ Starlette app (DON'T MODIFY)
    ├── mcp_app.py                   # ⭐ FastMCP instance (DON'T MODIFY)
    ├── config.py                    # ⭐ Config loader (DON'T MODIFY)
    │
    ├── config/                      # Configuration files
    │   ├── settings.yaml            # 📝 CUSTOMIZE: Default config
    │   ├── settings.dev.yaml        # 📝 CUSTOMIZE: Dev overrides
    │   └── settings.prod.yaml       # 📝 CUSTOMIZE: Prod overrides
    │
    ├── knowledge_base/              # ⭐ Documentation for LLMs
    │   ├── README.md                # Knowledge base guide
    │   ├── _TEMPLATE_overview.md    # Template for overview
    │   ├── _TEMPLATE_tool_doc.md    # Template for tool docs
    │   └── tools/                   # Tool-specific documentation
    │
    ├── tools/                       # 📝 CUSTOMIZE: Your MCP tools
    │   ├── __init__.py              
    │   ├── help_tools.py            # Knowledge base access tools
    │   └── example_tool.py          # Example (replace with yours)
    │
    ├── resources/                   # 📝 CUSTOMIZE: Your MCP resources
    │   ├── __init__.py
    │   └── example_resource.py      # Example (replace with yours)
    │
    ├── prompts/                     # 📝 CUSTOMIZE: Your MCP prompts
    │   ├── __init__.py
    │   └── example_prompt.py        # Example (replace with yours)
    │
    ├── db/                          # 📝 OPTIONAL: Database connectors
    │   ├── __init__.py
    │   └── connector.py             # Database connection template
    │
    └── utils/                       # 🔒 CORE UTILITIES (DON'T MODIFY)
        ├── __init__.py
        ├── import_utils.py          # Auto-discovery system
        ├── config_validator.py      # Config validation
        ├── request_logging.py       # Request logging middleware
        └── rate_limiting.py         # Rate limiting (optional)
```

### File Legend
- ⭐ **DON'T MODIFY** - Core infrastructure, keep as-is
- 📝 **CUSTOMIZE** - Edit these for your MCP
- 🔒 **CORE UTILITIES** - Infrastructure code

---

## 🛠️ Creating Your MCP

### Step 1: Set Up Knowledge Base

The knowledge base provides LLM-accessible documentation:

```bash
cd server/knowledge_base

# 1. Create overview
cp _TEMPLATE_overview.md overview.md
nano overview.md  # Customize all [CUSTOMIZE] sections

# 2. Create tool documentation (for each tool)
cp _TEMPLATE_tool_doc.md tools/your_tool_name.md
nano tools/your_tool_name.md  # Fill in tool details
```

**What to document**:
- `overview.md` - What your MCP does, when to use it
- `workflows.md` - Step-by-step guides for common tasks
- `architecture.md` - How it works internally (add Mermaid diagrams!)
- `troubleshooting.md` - Common errors and solutions
- `tools/tool_name.md` - Each tool's detailed documentation

### Step 2: Create Your Tools

```python
# server/tools/my_first_tool.py
from mcp_app import mcp

@mcp.tool(
    name="my_first_tool",
    description=(
        "Clear description of what this tool does.\n\n"
        "**Use when:** Describe the scenario\n"
        "**Returns:** What the tool returns"
    )
)
def my_first_tool(param1: str, param2: int = 10):
    """Internal docstring for developers."""
    
    # Your tool logic here
    result = do_something(param1, param2)
    
    return {
        "status": "success",
        "data": result,
        "message": "Tool executed successfully"
    }
```

**✅ Critical**: Always use explicit `name` and `description` in decorators (see [SPEC.md](SPEC.md) Rule #0)

### Step 3: Add Resources (Optional)

```python
# server/resources/my_resource.py
from mcp_app import mcp

@mcp.resource(
    uri="info://my-resource",
    name="My Resource",
    description="Description of what this resource provides"
)
def my_resource():
    """Provide context or information."""
    return "Resource content here"
```

### Step 4: Add Prompts (Optional)

```python
# server/prompts/my_prompt.py
from mcp_app import mcp

@mcp.prompt(
    name="my_prompt",
    description="Description of what guidance this prompt provides"
)
def my_prompt(context: str):
    """Provide contextual guidance."""
    return f"""You are helping with {context}.

Follow these guidelines:
1. Step one
2. Step two
"""
```

### Step 5: Configure

Edit `server/config/settings.yaml`:

```yaml
mcp:
  name: "My MCP Server"
  version: "1.0.0"
  description: "What your MCP does"

# Your custom configuration
your_service:
  api_key: "${YOUR_API_KEY}"  # From .env
  endpoint: "https://api.example.com"
  timeout: 30

database:
  host: "${DB_HOST:localhost}"
  port: "${DB_PORT:5432}"
```

### Step 6: Test

```bash
# Run tests
cd tests
pip install -r requirements.txt
pytest -v

# Test your tool manually
docker-compose up -d
docker-compose logs -f
```

---

## 📚 Knowledge Base Setup

The knowledge base provides LLM-queryable documentation.

### Why Use It?

- ✅ **Never goes stale** - Documentation updates with code
- ✅ **LLM-accessible** - Built-in help tools for querying
- ✅ **Maintainable** - Just edit markdown files
- ✅ **Version-controlled** - Docs live with code

### Files to Create

1. **`overview.md`** - Copy from `_TEMPLATE_overview.md`
   - What the MCP does
   - When to use it
   - Available tools
   - Security & auth

2. **`workflows.md`** - Step-by-step guides
   - Common task workflows
   - Example conversations
   - Tool combinations

3. **`architecture.md`** - How it works
   - Internal design
   - Data flow diagrams (Mermaid)
   - Configuration impact

4. **`troubleshooting.md`** - Error solutions
   - Common errors
   - Causes and fixes
   - Debugging tips

5. **`tools/tool_name.md`** - Per-tool docs
   - Copy from `_TEMPLATE_tool_doc.md`
   - Parameters, outputs, examples
   - Real-world usage scenarios

### Accessing from LLMs

The `help_tools.py` provides two tools:

```python
# List available documentation
list_knowledge_base_topics()

# Read specific documentation
get_knowledge_base_content(topic="overview")
get_knowledge_base_content(topic="workflows")
get_knowledge_base_content(topic="tool:my_tool_name")
```

---

## 🌐 Traefik Gateway Integration

This template is ready for Traefik gateway integration (labels are commented out).

### Without Traefik (Default)

Direct port binding - each MCP on its own port:

```yaml
# docker-compose.yml (current state)
services:
  template_mcp:
    ports:
      - "8100:8000"  # Direct port binding
```

Access: `http://localhost:8100/`

### With Traefik (Path-based Routing)

All MCPs through single gateway with path prefixes:

**1. Enable Traefik in `.env`**:
```bash
USE_TRAEFIK=true
MCP_NAME=template-mcp
```

**2. Edit `docker-compose.yml`**:
```yaml
services:
  template_mcp:
    # Comment out ports
    # ports:
    #   - "8100:8000"
    
    networks:
      - mcp_network  # Uncomment this
    
    labels:  # Uncomment all labels
      - "traefik.enable=true"
      - "traefik.http.routers.template-mcp.rule=PathPrefix(`/template-mcp`)"
      # ... etc
```

**3. Start gateway first**:
```bash
cd ../mcp-gateway
docker-compose up -d

cd ../template_mcp
docker-compose up -d
```

Access: `http://localhost:8000/template-mcp/`

### Traefik Benefits

- ✅ **Single entry point** - All MCPs through one gateway
- ✅ **Path-based routing** - `/mcp1`, `/mcp2`, etc.
- ✅ **Load balancing** - Distribute requests
- ✅ **Health checks** - Automatic unhealthy instance removal
- ✅ **TLS termination** - HTTPS at gateway

---

## 💻 Development Guide

### Hot Reload

The server automatically reloads when code changes:

```bash
# Start with hot reload (default)
docker-compose up -d

# Edit a tool
nano server/tools/my_tool.py

# Changes automatically detected and server reloads!
# Check logs to see reload:
docker-compose logs -f
```

### Adding Dependencies

```bash
# Add to requirements.txt
echo "requests==2.31.0" >> server/requirements.txt

# Rebuild container
docker-compose up -d --build
```

### Debugging

```bash
# View logs
docker-compose logs -f

# View specific log levels
docker-compose logs -f | grep ERROR

# Enter container
docker-compose exec template_mcp bash

# Check what's loaded
curl http://localhost:8100/version
```

### Configuration Hierarchy

1. **Default**: `server/config/settings.yaml`
2. **Environment override**: `server/config/settings.{ENV}.yaml`
3. **Environment variables**: `.env` file

Example:
```bash
# Set environment
ENV=prod

# Loads: settings.yaml + settings.prod.yaml
# Then applies .env variables
```

---

## 🧪 Testing

### Unit Tests

```bash
cd tests
pip install -r requirements.txt

# Run all tests
pytest -v

# Run specific test
pytest test_example_tool.py -v

# With coverage
pytest --cov=server --cov-report=html
```

### Integration Tests

```bash
# Start server
docker-compose up -d

# Run integration tests
pytest tests/integration/ -v
```

### Manual Testing

```bash
# Health check
curl http://localhost:8100/healthz

# Deep health
curl http://localhost:8100/health/deep | jq

# List knowledge base
curl http://localhost:8100/mcp -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"list_knowledge_base_topics"}}'
```

---

## 🚀 Deployment

### Docker Deployment

```bash
# Production build
ENV=prod docker-compose up -d --build

# Check status
docker-compose ps

# View prod logs
docker-compose logs -f
```

### Environment-Specific Config

Create `server/config/settings.prod.yaml`:

```yaml
mcp:
  name: "My MCP (Production)"
  
logging:
  level: "WARNING"
  format: "json"
  
rate_limiting:
  enabled: true
  max_requests: 100
  window_seconds: 60
```

### Health Checks

Configure your orchestrator to use:

- **Liveness**: `GET /healthz` - Simple "OK" response
- **Readiness**: `GET /health/deep` - Checks dependencies

Example Kubernetes:
```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /health/deep
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
```

---

## 🤖 For LLMs

> **When an LLM is helping create a new MCP using this template:**

### Critical Files to Read

1. **[SPEC.md](SPEC.md)** - Complete technical specification
   - Mandatory patterns
   - Critical rules (especially Rule #0)
   - File structure requirements
   - Best practices

2. **[server/server.py](server/server.py)** - DON'T MODIFY
   - Hot reload setup
   - Auto-discovery
   - Middleware configuration

3. **[server/mcp_app.py](server/mcp_app.py)** - DON'T MODIFY
   - FastMCP initialization
   - Keep minimal

4. **[server/config.py](server/config.py)** - DON'T MODIFY
   - Configuration loading
   - Environment handling

### What to Customize

✅ **ALWAYS CUSTOMIZE**:
- `server/config/settings.yaml` - User's configuration
- `server/tools/*.py` - User's tools (follow SPEC.md Rule #0!)
- `server/knowledge_base/*.md` - Documentation
- `README.md` - Update this file with user's MCP details
- `.env` - User's environment variables

❌ **NEVER MODIFY**:
- `server/server.py` - Core infrastructure
- `server/mcp_app.py` - FastMCP setup
- `server/config.py` - Config loader
- `server/utils/*.py` - Core utilities

### Knowledge Base Setup

Always create these files by copying templates:

```bash
# Overview
cp server/knowledge_base/_TEMPLATE_overview.md server/knowledge_base/overview.md

# Tool documentation (for each tool)
cp server/knowledge_base/_TEMPLATE_tool_doc.md server/knowledge_base/tools/user_tool.md
```

### Traefik Integration

Ask user: "Will this MCP use a Traefik gateway?"

- **YES**: Uncomment labels in `docker-compose.yml`, set `USE_TRAEFIK=true` in `.env`
- **NO**: Leave as-is (direct port binding)

### Tool Pattern (CRITICAL)

**ALWAYS use this pattern** (see SPEC.md Rule #0):

```python
@mcp.tool(
    name="tool_name",  # ✅ REQUIRED - explicit name
    description="..."  # ✅ REQUIRED - clear description
)
def tool_name(param: str):  # ✅ NOT async
    """Docstring."""
    return result  # ✅ Direct return
```

**NEVER use**:
```python
@mcp.tool()  # ❌ Empty decorator
async def tool_name():  # ❌ Async
    return {"result": ...}  # ❌ With type annotation
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file

---

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/template_mcp/issues)
- **Spec**: See [SPEC.md](SPEC.md) for detailed patterns
- **Examples**: Check `server/tools/example_tool.py` for working examples

---

## ✅ Checklist: Creating Your MCP

- [ ] Clone template and remove `.git` folder
- [ ] Update `.env` with your MCP name and port
- [ ] Customize `server/config/settings.yaml`
- [ ] Create knowledge base documentation (copy from templates)
- [ ] Add your tools to `server/tools/`
- [ ] Document each tool in `knowledge_base/tools/`
- [ ] Add resources/prompts if needed
- [ ] Update this README with your MCP details
- [ ] Decide on Traefik (yes/no) and configure accordingly
- [ ] Write tests in `tests/`
- [ ] Test locally: `docker-compose up -d`
- [ ] Verify health: `curl http://localhost:PORT/healthz`
- [ ] Update LICENSE with your information
- [ ] Initialize new git repo and push

---

**Template Version**: 2.0  
**Last Updated**: January 6, 2026  
**FastMCP Version**: 2.x
