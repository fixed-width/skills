# Fixed Width skills

Open [Agent Skills](https://agentskills.io) from Fixed Width — reusable agent guidance, not tied to
any one agent. Install with the [`skills` CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add fixed-width/skills                  # all skills in this repo
npx skills add fixed-width/skills -s glass-drive   # just one
```

Works across the agents the CLI supports (Claude Code, Codex, Cursor, OpenCode, and more).

## Skills

| Skill | For |
|---|---|
| `glass-drive` | Driving the **glass** GUI-automation MCP server — the build → see → interact → debug loop over a native app, verifying by pixels / diff / logs / a11y instead of guessing. Requires the glass MCP server: <https://github.com/fixed-width/glass> |

## License

Apache-2.0 — see [LICENSE](LICENSE).
