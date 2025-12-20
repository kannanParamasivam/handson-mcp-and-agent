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

## Running a2a router agent

* Run timeoff mcp server
```shell
uv run python3 -m time_off_app.time_off_mcp_server
```
This will start the timeoff mcp server on port 8000 with streamable-http enabled.

* Run agent server for hr policy agent
```shell
uv run python3 -m hr_a2a_app.hr_policy_a2a_wrapper_server
```
This will start the hr policy agent server on port 9001.

* Run agent server for timeoff agent
```shell
uv run python3 -m time_off_app.time_off_a2a_wrapper_server
```
This will start the timeoff agent server on port 9002.

* Run router agent
```shell
uv run python3 -m hr_a2a_app.hr_client_router_agent
```
This will run few user prompts to test the router agent.  
