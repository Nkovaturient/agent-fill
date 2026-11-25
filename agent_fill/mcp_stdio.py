import importlib.util
import sys

from agent_fill._paths import ensure_scripts_on_path, repo_root

ensure_scripts_on_path()


def main() -> None:
    server_path = repo_root() / "mcp_server" / "server.py"
    if not server_path.is_file():
        raise SystemExit(f"MCP server not found at {server_path}")

    spec = importlib.util.spec_from_file_location("agent_fill_mcp_server", server_path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Cannot load MCP server from {server_path}")

    mod = importlib.util.module_from_spec(spec)
    sys.modules["agent_fill_mcp_server"] = mod
    spec.loader.exec_module(mod)
    mod.mcp.run(transport="stdio")


if __name__ == "__main__":
    main()