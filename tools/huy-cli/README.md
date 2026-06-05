# Huygens CLI

Audited VM SSH via the ssh-gateway.

```bash
pip install -r tools/huy-cli/requirements.txt
chmod +x tools/huy-cli/huy
# optional: ln -s $(pwd)/tools/huy-cli/huy ~/bin/huy
```

## Quick start

```bash
eval $(./tools/huy-cli/huy login -q platform-admin 'platform-admin-dev')
./tools/huy-cli/huy use
# pick org → project → VM; context saved to ~/.config/huy/context.env
./tools/huy-cli/huy ssh
```

## Commands

| Command | Description |
|---------|-------------|
| `huy login USER PASS [-q]` | Get JWT; `-q` prints `export` lines for `eval` |
| `huy use` | Interactive org → project → agent → VM; optional connect |
| `huy use --no-connect` | Save context only |
| `huy orgs` | List organizations |
| `huy org select [N\|id\|slug]` | Save org to context |
| `huy projects` | List projects (needs org in context) |
| `huy project select [N\|id\|slug]` | Save project to context |
| `huy vms` | List VMs in project |
| `huy ssh [vm]` | Connect (uses saved context when flags omitted) |
| `huy env [-q]` | Print context as shell exports |
| `huy status` | Show token + saved context |

Context is stored in `~/.config/huy/context.env`. `huy ssh` reads it automatically; run `eval $(huy env -q)` only if you need `HUY_*` variables in your shell.

## Environment

| Variable | Default |
|----------|---------|
| `HUY_CONSOLE_URL` | `http://127.0.0.1:5173` |
| `HUY_SSH_GATEWAY_URL` | same as console |
| `HUY_ACCESS_TOKEN` | from `huy login` |

See [docs/operations/phase9-ssh-gateway.md](../../docs/operations/phase9-ssh-gateway.md).
