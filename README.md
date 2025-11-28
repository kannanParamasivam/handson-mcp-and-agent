## uv commands

Create new project

```shell
uv init mcp-server-code-of-conduct
```

Sync dependencies

```shell
uv sync
```

Add a new dependency

```shell
uv add fastmcp
```

```shell
uv add dotenv
```

Show dependency tree

```shell
uv tree
```

Run MCP inspector
```shell
uv run fastmcp dev mcp/server/path/mcp-server-file.py
```

Run MCP client as python module
```shell
uv run python3 -m <folder-name>.mcp-client-file-name
```