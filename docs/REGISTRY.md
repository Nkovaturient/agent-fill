# Registry and release checklist

Use this as a **submission template** for maintainers. Nothing here implies the package has already been listed in a third-party directory—check each site after you submit.

**Repository:** [https://github.com/Nkovaturient/agent-fill](https://github.com/Nkovaturient/agent-fill)  
**Version (pyproject):** `0.1.0`  
**Transport:** stdio  
**MCP tools (7):** `run_pipeline`, `anchor_date`, `check_temporal_prior`, `fetch_source`, `score_staleness`, `make_provenance`, `reconcile_sources`

---

## Cursor

- [ ] Clone or vendor the repo locally.
- [ ] Project skill symlink:

  ```bash
  mkdir -p .cursor/skills
  ln -s /absolute/path/to/agent-fill .cursor/skills/agent-fill
  ```

  Cursor loads `SKILL.md` from that folder when the skill is enabled.

- [ ] MCP stdio config in `.cursor/mcp.json` (adjust paths; use a venv with `pip install '.[mcp]'` or `mcp_server/requirements.txt`):

  ```json
  {
    "mcpServers": {
      "agent-fill": {
        "command": "/absolute/path/to/agent-fill/.venv/bin/python",
        "args": ["/absolute/path/to/agent-fill/mcp_server/server.py"]
      }
    }
  }
  ```

  After `pip install -e '.[mcp]'` from the repo root, you can instead use:

  ```json
  {
    "mcpServers": {
      "agent-fill": {
        "command": "/absolute/path/to/agent-fill/.venv/bin/agent-fill-mcp",
        "args": []
      }
    }
  }
  ```

- [ ] Confirm all 7 tools appear in the MCP tool list and run `python evals/run_evals.py` once.

---

## Claude Code

- [ ] Install the portable skill:

  ```bash
  git clone https://github.com/Nkovaturient/agent-fill.git
  mkdir -p ~/.claude/skills
  ln -s "$(pwd)/agent-fill" ~/.claude/skills/agent-fill
  ```

- [ ] Register the MCP server (stdio):

  ```bash
  claude mcp add agent-fill -- \
    "$(pwd)/agent-fill/.venv/bin/python" \
    "$(pwd)/agent-fill/mcp_server/server.py"
  ```

  Or with the console entry point after `pip install -e '.[mcp]'`:

  ```bash
  claude mcp add agent-fill -- "$(pwd)/agent-fill/.venv/bin/agent-fill-mcp"
  ```

- [ ] Verify Step 2 `canonical_registries` output by running a gated query (e.g. government statistics with a future period).

---

## MCP server directories

Paste the same metadata everywhere the form asks for name, repo, transport, and tools:

| Field | Value |
| --- | --- |
| Name | `agent-fill` |
| Description | Temporal grounding skill and MCP server: anchor UTC date, gate queries by publication lag, fetch sources with four dates, score staleness, enforce provenance. |
| Repository URL | `https://github.com/Nkovaturient/agent-fill` |
| Transport | `stdio` |
| Start command | `python mcp_server/server.py` (or `agent-fill-mcp` after install) |
| Tools | `run_pipeline`, `anchor_date`, `check_temporal_prior`, `fetch_source`, `score_staleness`, `make_provenance`, `reconcile_sources` |
| License | MIT |

Suggested listing sites (follow each site’s submission flow; links are entry points, not proof of listing):

- [ ] [Model Context Protocol — Example servers](https://github.com/modelcontextprotocol/servers) (community PR pattern; read their contributing guide)
- [ ] [Smithery](https://smithery.ai/) — search “submit” / “publish server” in their docs
- [ ] [Glama MCP directory](https://glama.ai/mcp/servers)
- [ ] [PulseMCP](https://www.pulsemcp.com/)

**Short blurb for directory forms:**

> agent-fill anchors the real clock, blocks impossible time-sensitive queries via lag priors and canonical_registries, fetches public URLs with separated published/modified/data-as-of/accessed dates, scores staleness, and emits provenance contracts. Seven stdio MCP tools mirror the five-step SKILL.md protocol.

---

## Git tag and GitHub release (v0.1.0)

Prerequisites: `main` is pushed and includes the release docs; working tree clean.

1. **Check for an existing tag:**

   ```bash
   git tag -l 'v0.1.0'
   ```

2. **If no tag exists, create and push:**

   ```bash
   git tag -a v0.1.0 -m "agent-fill 0.1.0: temporal grounding skill, MCP server, evals"
   git push origin v0.1.0
   ```

3. **GitHub release (authenticated `gh`):**

   ```bash
   gh auth login   # if needed
   gh release create v0.1.0 \
     --title "v0.1.0" \
     --notes-file CHANGELOG.md
   ```

   Or on [github.com/Nkovaturient/agent-fill/releases/new](https://github.com/Nkovaturient/agent-fill/releases/new): choose tag `v0.1.0`, title `v0.1.0`, paste the `## [0.1.0]` section from `CHANGELOG.md`.

4. **After release:** update the `[0.1.0]` link at the bottom of `CHANGELOG.md` if the release URL differs.

**Note:** `gh release create` was not run automatically in the v0.1.0 prep pass because GitHub CLI was not authenticated in that environment. Run the steps above locally.