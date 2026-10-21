#!/usr/bin/env python3
"""pull-secrets.sh keeps the .env keys it doesn't generate (2026-10-20).

The script rewrites .env from scratch. Before this, every key added by hand --
road-trip's RT_ADMIN_GITHUB_CLIENT_SECRET, RT_DESIGN_CONNECTION and
NPS_API_KEY, the Jev key TYPESAFE_API_KEY -- was lost on the next run.

Each test runs the real script against a fake `az` on PATH (it answers
`keyvault secret show --name X` with "val-X") and a temporary HOME and output
file, so nothing real is read or written.
"""
import os
import stat
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "infrastructure", "wsl", "pull-secrets.sh")

FAKE_AZ = """#!/usr/bin/env bash
args="$*"
case "$args" in
  *"keyvault list"*) echo "kv-fake" ;;
  *"keyvault secret show"*) echo "val-$(echo "$args" | sed -n 's/.*--name \\([^ ]*\\).*/\\1/p')" ;;
esac
"""


class PullSecretsKeepsHandAddedKeys(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: subprocess.run(["rm", "-r", self.tmp], check=False))
        bin_dir = os.path.join(self.tmp, "bin")
        os.makedirs(bin_dir)
        az = os.path.join(bin_dir, "az")
        with open(az, "w") as fh:
            fh.write(FAKE_AZ)
        os.chmod(az, 0o755)
        self.env = dict(os.environ, PATH=bin_dir + os.pathsep + os.environ["PATH"], HOME=self.tmp)
        self.out = os.path.join(self.tmp, ".env")

    def run_script(self):
        result = subprocess.run(["bash", SCRIPT, "--vault-name", "kv-fake", "--output", self.out],
                                env=self.env, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        with open(self.out) as fh:
            return fh.read(), result.stdout

    def keys(self, text):
        return [line.split("=", 1)[0] for line in text.splitlines() if "=" in line and not line.startswith("#")]

    def test_hand_added_keys_survive_a_rerun_verbatim(self):
        conn = "Server=127.0.0.1,1433;Database=RoadTripMap;User Id=wsl_claude_admin;Password=p=q;TrustServerCertificate=True;"
        with open(self.out, "w") as fh:
            fh.write("# old file\nFINNHUB_API_KEY=old-value\n"
                     "# road-trip local /admin sign-in\nRT_ADMIN_GITHUB_CLIENT_SECRET=abc123\n"
                     f"RT_DESIGN_CONNECTION={conn}\nNPS_API_KEY=nps\nTYPESAFE_API_KEY=jev\n")

        text, stdout = self.run_script()

        for line in ("RT_ADMIN_GITHUB_CLIENT_SECRET=abc123", f"RT_DESIGN_CONNECTION={conn}",
                     "NPS_API_KEY=nps", "TYPESAFE_API_KEY=jev"):
            self.assertIn(line + "\n", text)
        self.assertIn("FINNHUB_API_KEY=val-FinnhubApiKey\n", text, "generated keys are regenerated, not kept")
        self.assertNotIn("old-value", text)
        keys = self.keys(text)
        self.assertEqual(len(keys), len(set(keys)), "no key appears twice")
        self.assertNotIn("abc123", stdout, "the script names kept keys, never their values")
        self.assertIn("RT_ADMIN_GITHUB_CLIENT_SECRET", stdout)

    def test_a_first_run_has_nothing_to_keep(self):
        text, stdout = self.run_script()
        self.assertNotIn("Kept from the previous .env", text)
        self.assertIn("FINNHUB_API_KEY=val-FinnhubApiKey\n", text)

    def test_the_file_stays_private(self):
        with open(self.out, "w") as fh:
            fh.write("NPS_API_KEY=nps\n")
        self.run_script()
        self.assertEqual(stat.S_IMODE(os.stat(self.out).st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()
