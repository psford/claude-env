# Bootstrap Artifacts

Files in this directory are **starter templates** that bootstrap copies into a new companion project. Edit-then-commit the result inside the destination repo — these are starting points, not symlinks.

## Files

### `endpoints.schema.json`

JSON Schema (draft 2020-12) for the **endpoint registry** pattern used by stock-analyzer and road-trip. The schema is identical in both consumers and was duplicated until this PR — companion projects should now reference (or copy) this canonical version instead.

**Usage in a new project:**

```bash
# Copy the schema next to your endpoints.json
cp /path/to/claude-env/infrastructure/bootstrap/endpoints.schema.json ./endpoints.schema.json

# Create endpoints.json pointing at it
cat > endpoints.json <<'EOF'
{
  "$schema": "./endpoints.schema.json",
  "project": "<your-project-name>",
  "environments": {
    "dev": { },
    "prod": { }
  }
}
EOF
```

The companion repo gets:
- The `.claude/hooks/endpoint_registry_guard.py` hook (declared in `tooling-manifest.json`) that blocks hardcoded connection strings and `Environment.GetEnvironmentVariable` calls for known endpoint keys.
- The `.claude/hooks/endpoint_schema_validator.py` hook that validates `endpoints.json` shape on commits touching it.

Both hooks auto-activate when `endpoints.json` exists at the repo root; no per-repo config needed.

### `nvmrc.template`

Single-line `.nvmrc` template (defaults to `20`). The `engines_node_guard.py` hook (claude-env, universal tier) blocks `npm install` in Node projects with no `.nvmrc` and no `engines.node` pin, so new Node projects should drop this in:

```bash
cp /path/to/claude-env/infrastructure/bootstrap/nvmrc.template .nvmrc
# Then edit if you need a different major (18, 20, 22, …)
```

## Adding a new bootstrap artifact

1. Place the file in this directory.
2. Add an entry to `tooling-manifest.json` under `tools[]`. The `manifest_completeness_guard.py` hook will block the commit otherwise.
3. Document its purpose here.
4. Reference it from companion-repo onboarding docs.
