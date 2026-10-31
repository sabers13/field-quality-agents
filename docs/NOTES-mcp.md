# MCP Python SDK notes (verified 2026-10-31)

## Version and source

| Item | Value |
|---|---|
| Package | `mcp` (official Model Context Protocol Python SDK) |
| Version | 2.3.0 |
| Release date (PyPI) | 2026-10-02 |
| Python requirement | >=3.11 |
| Docs | <https://py.sdk.modelcontextprotocol.io/> |
| Release line | v2 (current stable line; v1.x docs still published separately) |
| Checked | 2026-10-31 |

Install with the CLI extra for `mcp dev` / `mcp run`:

```bash
uv add "mcp[cli]"
```

## What the SDK provides

The SDK builds MCP servers and clients over stdio, Streamable HTTP and the
legacy SSE transport. For this project only **servers** matter: the same typed
tool functions used by the agents must also be callable from any MCP client.

## Serving existing functions as tools over stdio

v2 uses `MCPServer` (not the older low-level `Server` for the normal path). A
module-level server plus `@mcp.tool()` on each existing function is enough:

```python
from mcp.server import MCPServer

mcp = MCPServer("field-quality-agents")


@mcp.tool()
def similar_cases(text: str, k: int = 5) -> list[dict]:
    """BM25 search over the case knowledge base."""
    return _similar_cases(text=text, k=k)


@mcp.tool()
def recalls_for(make: str, model: str, year: int, group: str) -> list[dict]:
    """Return matching recalls."""
    return _recalls_for(make, model, year, group)


if __name__ == "__main__":
    mcp.run()  # no argument = stdio
```

- `mcp.run()` is synchronous and blocks; with no argument the transport is
  **stdio**, which is what `fqa mcp` needs.
- Register tools with `@mcp.tool()`. The function name, docstring and type
  hints become the MCP tool metadata and input schema.
- Keep `mcp.run()` under `if __name__ == "__main__":`; everything that loads
  the module (including tests and `mcp dev`) imports it first.
- stdout **is the wire** while serving. Log with `logging` (stderr); do not
  print to stdout from tool code. Output flushed to stdout after serving starts
  is diverted to stderr by the SDK, but buffered output from before serving can
  still corrupt the stream.
- Streamable HTTP is available with
  `mcp.run(transport="streamable-http", port=...)`; not used for Q2. SSE is
  superseded and should not be used for new code.

## Local development and testing

- `uv run mcp dev src/field_quality_agents/mcp_server.py` opens the MCP
  Inspector (needs `npx` on `PATH`).
- `uv run mcp run src/field_quality_agents/mcp_server.py` imports the module and
  calls `run()`; the `__main__` block is skipped.
- A test harness can launch the module as a subprocess and speak stdio, list
  tools, then call each one against a fixture DuckDB. Q2 owns that harness.

## Consequences for Q2/Q7

- Q2 owns `src/field_quality_agents/mcp_server.py` and must expose exactly the
  tool surface in `docs/INTERFACES.md`: `similar_cases`, `recalls_for`,
  `investigations_for`, `cluster_stats`, `verify_quotes`, `rulebook`,
  `case_lookup`.
- The MCP layer is a thin adapter: no business logic unique to MCP, so the
  agent tools and MCP tools cannot drift.
- `fqa mcp` should call `mcp.run()` with stdio and must keep stdout clean.
- Q7's API is a separate surface (FastAPI); it may reuse the same functions but
  must not require MCP to be running.
