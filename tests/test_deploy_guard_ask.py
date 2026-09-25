#!/usr/bin/env python3
"""What deploy_guard ASKS about (CE-2.73, the narrowed refile of CE-2.66).

Why a unittest rather than fixtures: the fixture harness compares exit codes,
and the ask branch exits 0 whether it prompts or stays silent. Its decision is
the permissionDecision in its JSON answer, so that is what is asserted here.

Patrick, 2026-09-23: "you shouldn't be asking me here if it's ok to ask me on
the board." The ask branch matches the RAW command, so every ticket command
whose text mentioned a production deploy prompted him in the IDE.

CE-2.66 tried reading the masked text instead. Its CSO change review measured
that WEAKER: a runner's quoted payload inside $( ), backticks or <( ) under a
text-speaking head was blanked as data and ran unprompted. So this is
narrower. The raw-text prompt stays, with one exemption: a single plain ticket
statement, with no shell machinery at all, which can run nothing but the
ticket CLI with literal arguments.

Round 2 takes CE-2.73's own CSO change review: the exemption reads the command
unstripped, wants a space or tab after `ticket`, and every character
printable, so text a terminal would draw as a second command still prompts;
and each list's size is pinned, so a corpus cannot shrink and stay green.
"""
import json
import os
import subprocess
import sys
import unittest

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    ".claude", "hooks", "deploy_guard.py")

AZ = "az webapp deploy --name app --src-path app.zip"
WR = "npx wrangler deploy --env production"

# Every real deploy shape measured before building
# (/home/patrick/.local/share/harness/ce273-probe.py): each prompts today, on
# the raw command, and must keep prompting.
REAL = [
    AZ, WR, "timeout 900 " + AZ, f'bash -c "{AZ}"', f"sh -c '{AZ}'",
    f'ssh build-box "{AZ}"', f'eval "{AZ}"', f"( {AZ} )", f"{{ {AZ}; }}",
    f'X="{AZ}"; $X', f'echo "{AZ}" | bash', f"printf '%s\\n' '{AZ}' | sh",
    f'echo "{AZ}" > run.sh && bash run.sh', f'ticket new --title "$({AZ})"',
    f'ticket new --title "`{AZ}`"', f'git commit -m "done $({AZ})"',
    f'gh pr create --title t --body "$({AZ})"', f"echo <({AZ})",
    f"bash <<'EOF'\n{AZ}\nEOF", f"env sh <<'EOF'\n{AZ}\nEOF",
    f"ssh build-box <<'EOF'\n{AZ}\nEOF",
    f"python3 - <<'EOF'\nimport os\nos.system('{AZ}')\nEOF",
    f"cat <<'EOF' | bash\n{AZ}\nEOF", f"cat <<'EOF' | ssh build-box\n{AZ}\nEOF",
    f"cat > r.sh <<'EOF'\n{AZ}\nEOF\nbash r.sh", f"tee r.sh <<'EOF'\n{AZ}\nEOF\nsh r.sh",
    f"bash <<< '{AZ}'", f"echo {AZ} | xargs -I{{}} sh -c '{{}}'",
    f"find . -maxdepth 0 -exec {AZ} \\;", f"if {AZ}; then echo ok; fi",
    f"for i in 1; do {AZ}; done", f"ticket show X && {AZ}",
    f"jq -rn '\"{AZ}\"' | sh", f"echo {AZ} | bash", f"git -c alias.z='!{AZ}' z",
    f'git commit -m "ship" && {AZ}', f"cat <<'EOF' | tee r.sh | bash\n{AZ}\nEOF",
    f"cat > r.sh <<'EOF' && bash r.sh\n{AZ}\nEOF",
    # the CSO's four: a runner's payload inside a substitution
    f"echo <(bash -c '{AZ}')", f"echo $(bash -c '{AZ}')", f"echo `bash -c '{AZ}'`",
    f"ticket new --title $(bash -c '{AZ}')",
    # a ticket statement joined to anything else is not plain
    f"ticket new --title x; {AZ}", f"ticket new --title x && {AZ}",
    f"ticket new --title '{AZ}' | bash", f"ticket new --title x\n{AZ}",
    f"ticket new --title '{AZ}' > r.sh; bash r.sh", f"ticket new --title x & {AZ}",
    f"X=1 ticket new --title '{AZ}'", f" ticket new --title x;{AZ}",
    f"ticket new --title x `{AZ}`", f"ticket new --title x <({AZ})",
    # round 2, the review's extension set: patterns 2 and 3, privilege and
    # background wrappers, ANSI-C quoting
    "az container create --resource-group rg --name app --image img",
    "pwsh ./Deploy-ToAzure.ps1 -Env production",
    "sudo " + AZ, "nohup " + AZ, AZ + " &", f"echo $'{AZ}' | bash",
    "ticket new --title $'deploy to production'",
    # a second command a terminal would draw and bash never runs: not plain
    # (the review's finding 1, and the escape-sequence rest of its class)
    f'ticket ask NFL-1 --question "Deploy to Azure now?"\r{AZ}',
    f'ticket ask NFL-1 --question "Deploy to Azure now?" {AZ}',
    f'ticket ask NFL-1 --question "ok"\x1b[1E {AZ}',
]

# A plain ticket command that only mentions a deploy: must not prompt.
PLAIN_TICKET = [
    'ticket new --title "deploy the relay to production"',
    'ticket ask NFL-1 --question "Deploy to Azure now?"',
    "ticket move X --to uat --note 'deploy to production after merge'",
    'ticket ac add X --kind manual --text "after the deploy to production, the site answers"',
    # the subcommands the review checked: the ticket CLI runs fixed argv
    'ticket dispatch X --note "deploy to production after QA"',
    "ticket ac verify X AC1 --ref tests/test_deploy.py::test_production",
    "ticket check X --note deploy-to-production",
]

# Other text that only mentions a deploy: still prompts, as it does today.
OTHER_TEXT = [
    'git commit -m "docs: how to deploy to production"',
    'gh pr create --title t --body "deploy to production after merge"',
    "echo deploy to production is Patricks call",
    # near misses of a plain ticket statement: not plain, so they prompt
    ' ticket ask NFL-1 --question "Deploy to Azure now?"',
    '\tticket ask NFL-1 --question "Deploy to Azure now?"',
    'ticket ask NFL-1 --question "Deploy to Azure now?"\n',
    'ticket ask NFL-1 --question "Deploy to Azure now?"\r',
    ' ticket ask NFL-1 --question "Deploy to Azure now?"',
    'ticket ask NFL-1 --question "Deploy to Azure now?"',
    'ticket new --title "deploy to production‮"',
    'TICKET ask NFL-1 --question "Deploy to Azure now?"',
    'tickets ask NFL-1 --question "Deploy to Azure now?"',
]


def decision(command):
    """The hook's permissionDecision for this command, or "allow" when it
    printed nothing (Claude Code then proceeds without a prompt)."""
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    proc = subprocess.run([sys.executable, HOOK], input=payload,
                          capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        raise AssertionError(f"hook exited {proc.returncode}: {proc.stderr}")
    out = proc.stdout.strip()
    if not out:
        return "allow"
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"]


class TestTheAskIsSilentOnlyForPlainTickets(unittest.TestCase):
    def test_real_deploys_still_prompt(self):
        self.assertEqual(len(REAL), 62, "the measured deploy corpus changed size")
        for command in REAL:
            with self.subTest(command=command):
                self.assertEqual(decision(command), "ask",
                                 f"a real deploy stopped prompting: {command!r}")

    def test_a_plain_ticket_command_does_not_prompt(self):
        self.assertEqual(len(PLAIN_TICKET), 7, "the plain ticket corpus changed size")
        for command in PLAIN_TICKET:
            with self.subTest(command=command):
                self.assertEqual(decision(command), "allow",
                                 f"a plain ticket command still prompts: {command!r}")

    def test_other_text_still_prompts(self):
        self.assertEqual(len(OTHER_TEXT), 12, "the other-text corpus changed size")
        for command in OTHER_TEXT:
            with self.subTest(command=command):
                self.assertEqual(decision(command), "ask",
                                 f"text that is not a plain ticket command stopped prompting: {command!r}")


if __name__ == "__main__":
    unittest.main()
