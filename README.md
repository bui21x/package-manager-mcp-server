# Package Manager MCP Server

A Model Context Protocol (MCP) server that provides package management capabilities for AI agents, supporting dependency resolution, version management, and package querying across multiple package managers.

## Features

- Package information retrieval
- Dependency resolution
- Version compatibility checking
- Support for multiple package managers
- Health monitoring

## Supported Package Managers

- pip (Python)
- npm (JavaScript/Node.js)
- More coming soon: cargo (Rust), composer (PHP), gem (Ruby)

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run server:
```bash
uvicorn src.mcp_server:app --reload
```

## API Endpoints

- POST /package_info - Get package information
- POST /dependencies - Get package dependencies
- POST /compatible_versions - Get compatible package versions
- GET /supported_package_managers - List supported package managers
- GET /health - Check server health

## Example Usage

```python
# Get package information
POST /package_info
{
    "package_name": "fastapi",
    "package_manager": "pip"
}

# Get package dependencies
POST /dependencies
{
    "package_name": "fastapi",
    "package_manager": "pip",
    "version": "0.95.0"
}

# Find compatible versions
POST /compatible_versions
{
    "package_name": "fastapi",
    "package_manager": "pip",
    "version_constraint": ">=0.90.0"
}
```

## MCP Integration

This server follows the MCP specification for tool integration with AI agents, designed for easy integration into terminal AI agents and systems requiring package management functionality.