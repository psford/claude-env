# Per-machine secrets — how this works

Secrets never enter git. The config template references each key with a
`$(cat …)` command substitution:

    $(cat ${HOME}/.config/polytoken/secrets/<name>)

The secrets directory `~/.config/polytoken/secrets/` is deliberately at a
fixed path on every OS (macOS included) so the template stays byte-identical
across machines. `polytoken/bootstrap.sh` creates the directory (0700) and
each file (0600), prompting for any file listed in `secrets.example/` that is
missing.

One `<name>.example` file per secret ships here. Each contains only
instructions — never a real value. Current secrets:

- `zai` — ZAI provider API key (static key auth)
- `deepseek` — DeepSeek provider API key (static key auth)
- `tavily` — Tavily web-search API key

Write each value with no trailing newline if you create files by hand:
`printf %s 'VALUE' > ~/.config/polytoken/secrets/zai && chmod 600 …`
(bootstrap tolerates a trailing newline, hand-written files should not rely
on that).
