"""Unit tests for polytoken/bootstrap.sh (--check, idempotency, rollback)."""

import os
import unittest

from helpers import sandbox_factory

TEMPLATE = None  # filled per-test from the sandbox layer copy


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.sb, self.cleanup = sandbox_factory()
        self.addCleanup(self.cleanup)
        self.cfg = os.path.join(self.sb.tmp, "confighome")
        self.template = os.path.join(self.sb.layer, "config.template.yaml")
        self.installed_config = os.path.join(self.cfg, "config.yaml")
        self.installed_hooks = os.path.join(self.cfg, "hooks.json")
        self.secrets = os.path.join(self.sb.home, ".config", "polytoken", "secrets")

    def seed_secrets(self):
        os.makedirs(self.secrets, exist_ok=True)
        for name in ("zai", "deepseek", "tavily"):
            with open(os.path.join(self.secrets, name), "w") as fh:
                fh.write("test-value-not-a-real-key")

    def install(self, *extra):
        return self.sb.run_bootstrap("--no-prompt", *extra, config_home=self.cfg)

    def backups(self, name):
        return [f for f in os.listdir(self.cfg)
                if f.startswith(name + ".bak.")] if os.path.isdir(self.cfg) else []

    # ---------------------------------------------------------------- check
    def test_check_clean_after_install(self):
        self.seed_secrets()
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stderr)
        c = self.sb.run_bootstrap("--check", config_home=self.cfg)
        self.assertEqual(c.returncode, 0, c.stdout + c.stderr)
        self.assertIn("clean", c.stdout)

    def test_check_detects_config_drift(self):
        self.seed_secrets()
        self.install()
        with open(self.installed_config, "a") as fh:
            fh.write("# drifted\n")
        c = self.sb.run_bootstrap("--check", config_home=self.cfg)
        self.assertEqual(c.returncode, 1)
        self.assertIn("config: drifted", c.stdout)

    def test_check_detects_hooks_drift(self):
        self.seed_secrets()
        self.install()
        os.remove(self.installed_hooks)
        with open(self.installed_hooks, "w") as fh:
            fh.write("[]\n")
        c = self.sb.run_bootstrap("--check", config_home=self.cfg)
        self.assertEqual(c.returncode, 1)
        self.assertIn("hooks:", c.stdout)
        self.assertIn("not the layer symlink", c.stdout)

    def test_check_detects_missing_secrets(self):
        self.install()
        c = self.sb.run_bootstrap("--check", config_home=self.cfg)
        self.assertEqual(c.returncode, 1)
        self.assertIn("secrets: missing", c.stdout)
        for name in ("zai", "deepseek", "tavily"):
            self.assertIn(name, c.stdout)

    def test_check_detects_missing_hooks(self):
        self.seed_secrets()
        self.install()
        os.remove(self.installed_hooks)
        c = self.sb.run_bootstrap("--check", config_home=self.cfg)
        self.assertEqual(c.returncode, 1)
        self.assertIn("hooks: missing", c.stdout)

    def test_version_mismatch_names_both_versions(self):
        self.seed_secrets()
        self.install()
        c = self.sb.run_bootstrap(
            "--check", config_home=self.cfg,
            env_extra={"FAKE_POLYTOKEN_VERSION": "9.9.9"})
        self.assertEqual(c.returncode, 1)
        self.assertIn("0.8.17", c.stdout + c.stderr)
        self.assertIn("9.9.9", c.stdout + c.stderr)

    # ----------------------------------------------------------- idempotency
    def test_second_run_is_noop(self):
        self.seed_secrets()
        self.install()
        before = sorted(os.listdir(self.cfg))
        bcfg = len(self.backups("config.yaml"))
        bhooks = len(self.backups("hooks.json"))
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("already current", r.stdout)
        self.assertIn("already symlinked", r.stdout)
        self.assertEqual(sorted(os.listdir(self.cfg)), before)
        self.assertEqual(len(self.backups("config.yaml")), bcfg)
        self.assertEqual(len(self.backups("hooks.json")), bhooks)

    def test_install_replaces_drifted_config_with_backup(self):
        os.makedirs(self.cfg, exist_ok=True)
        with open(self.installed_config, "w") as fh:
            fh.write("version: 4\n# old plaintext-key config\n")
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(self.installed_config) as fh:
            self.assertEqual(fh.read(), open(self.template).read())
        self.assertEqual(len(self.backups("config.yaml")), 1)
        with open(os.path.join(self.cfg, self.backups("config.yaml")[0])) as fh:
            self.assertIn("old plaintext-key config", fh.read())

    # -------------------------------------------------------------- rollback
    def test_rollback_restores_pre_install_state(self):
        os.makedirs(self.cfg, exist_ok=True)
        with open(self.installed_config, "w") as fh:
            fh.write("# the pre-install config\n")
        with open(self.installed_hooks, "w") as fh:
            fh.write("# the pre-install hooks\n")
        self.install()
        r = self.sb.run_bootstrap("--rollback", config_home=self.cfg)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(self.installed_config) as fh:
            self.assertEqual(fh.read(), "# the pre-install config\n")
        with open(self.installed_hooks) as fh:
            self.assertEqual(fh.read(), "# the pre-install hooks\n")
        self.assertFalse(os.path.islink(self.installed_hooks))

    def test_rollback_removes_fresh_install(self):
        """Fresh installs (no pre-existing file) are stamped; rollback
        removes them, restoring the true pre-install state (absence)."""
        self.seed_secrets()
        self.install()
        self.assertTrue(os.path.exists(self.installed_config))
        r = self.sb.run_bootstrap("--rollback", config_home=self.cfg)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(self.installed_config))
        self.assertFalse(os.path.exists(self.installed_hooks))

    # ---------------------------------------------------------------- perms
    def test_secrets_dir_permissions(self):
        self.seed_secrets()
        self.install()
        self.assertEqual(oct(os.stat(self.secrets).st_mode)[-3:], "700")
        for name in ("zai", "deepseek", "tavily"):
            self.assertEqual(
                oct(os.stat(os.path.join(self.secrets, name)).st_mode)[-3:],
                "600")

    def test_install_symlinks_hooks_into_layer(self):
        self.seed_secrets()
        self.install()
        self.assertTrue(os.path.islink(self.installed_hooks))
        target = os.path.realpath(self.installed_hooks)
        self.assertEqual(
            target, os.path.join(self.sb.layer, "hooks.json"))

    # ------------------------------------------------- config-dir selection
    def test_darwin_ignores_bare_secrets_dir(self):
        """Regression (Mac bring-up): ~/.config/polytoken existing for
        SECRETS alone must not make bootstrap target it on macOS — polytoken
        reads ~/Library/Application Support/polytoken there, so config
        landed where it was never loaded ("no providers available")."""
        # secrets-only ~/.config/polytoken, exactly like a real Mac mid-run
        os.makedirs(os.path.join(self.sb.home, ".config/polytoken/secrets"),
                    exist_ok=True)
        r = self.sb.run_bootstrap("--no-prompt",
                                  env_extra={"POLYTOKEN_TEST_UNAME": "Darwin"})
        self.assertEqual(r.returncode, 0, r.stderr)
        mac_cfg = os.path.join(
            self.sb.home, "Library", "Application Support", "polytoken")
        self.assertTrue(os.path.isfile(os.path.join(mac_cfg, "config.yaml")))
        self.assertTrue(os.path.islink(os.path.join(mac_cfg, "hooks.json")))
        self.assertFalse(
            os.path.exists(os.path.join(self.sb.home,
                                        ".config/polytoken/config.yaml")))

    def test_linux_default_still_prefers_existing_config(self):
        """A real config in ~/.config/polytoken keeps bootstrap targeting it
        (Linux default, and the deliberate 'prefer where a config lives')."""
        os.makedirs(os.path.join(self.sb.home, ".config/polytoken"),
                    exist_ok=True)
        with open(os.path.join(self.sb.home, ".config/polytoken/config.yaml"),
                  "w") as fh:
            fh.write("# existing\n")
        r = self.sb.run_bootstrap("--no-prompt")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.isfile(
            os.path.join(self.sb.home, ".config/polytoken/config.yaml")))
        self.assertTrue(os.path.islink(
            os.path.join(self.sb.home, ".config/polytoken/hooks.json")))


if __name__ == "__main__":
    unittest.main()
