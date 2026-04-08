#!/usr/bin/env python3
"""
Test suite for endpoint registry and schema validator hooks.

Tests the logic functions of endpoint_registry_guard.py and
endpoint_schema_validator.py without requiring git environment.
"""

import json
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import tempfile


# Add hooks directory to path so we can import the modules
hooks_dir = os.path.join(os.path.dirname(__file__), "..", ".claude", "hooks")
sys.path.insert(0, hooks_dir)

import endpoint_registry_guard
import endpoint_schema_validator


class TestLoadEnvKeys:
    """Test endpoint_registry_guard.load_env_keys()"""

    def test_extracts_simple_env_keys(self, tmp_path):
        """Extract simple env keys from endpoints.json"""
        endpoints_file = tmp_path / "endpoints.json"
        endpoints_file.write_text(json.dumps({
            "environments": {
                "dev": {
                    "database": {
                        "source": "env",
                        "key": "DB_CONN_STRING"
                    }
                }
            }
        }))

        keys = endpoint_registry_guard.load_env_keys(str(endpoints_file))
        assert "DB_CONN_STRING" in keys

    def test_extracts_compound_env_keys(self, tmp_path):
        """Extract env keys from compound endpoint entries"""
        endpoints_file = tmp_path / "endpoints.json"
        endpoints_file.write_text(json.dumps({
            "environments": {
                "prod": {
                    "api": {
                        "host": {
                            "source": "env",
                            "key": "API_HOST"
                        },
                        "port": {
                            "source": "env",
                            "key": "API_PORT"
                        }
                    }
                }
            }
        }))

        keys = endpoint_registry_guard.load_env_keys(str(endpoints_file))
        assert "API_HOST" in keys
        assert "API_PORT" in keys

    def test_ignores_literal_sources(self, tmp_path):
        """Ignore literal source entries"""
        endpoints_file = tmp_path / "endpoints.json"
        endpoints_file.write_text(json.dumps({
            "environments": {
                "dev": {
                    "endpoint": {
                        "source": "literal",
                        "value": "http://localhost:3000"
                    }
                }
            }
        }))

        keys = endpoint_registry_guard.load_env_keys(str(endpoints_file))
        assert len(keys) == 0

    def test_ignores_keyvault_sources(self, tmp_path):
        """Ignore keyvault source entries"""
        endpoints_file = tmp_path / "endpoints.json"
        endpoints_file.write_text(json.dumps({
            "environments": {
                "prod": {
                    "db": {
                        "source": "keyvault",
                        "vault": "my-vault",
                        "secret": "db-conn-string"
                    }
                }
            }
        }))

        keys = endpoint_registry_guard.load_env_keys(str(endpoints_file))
        assert len(keys) == 0

    def test_handles_malformed_json(self, tmp_path):
        """Gracefully handle malformed JSON"""
        endpoints_file = tmp_path / "endpoints.json"
        endpoints_file.write_text("{invalid json")

        keys = endpoint_registry_guard.load_env_keys(str(endpoints_file))
        assert isinstance(keys, set)
        assert len(keys) == 0

    def test_handles_missing_file(self, tmp_path):
        """Gracefully handle missing file"""
        nonexistent = tmp_path / "nonexistent.json"
        keys = endpoint_registry_guard.load_env_keys(str(nonexistent))
        assert isinstance(keys, set)
        assert len(keys) == 0

    def test_extracts_across_multiple_environments(self, tmp_path):
        """Extract keys across multiple environment blocks"""
        endpoints_file = tmp_path / "endpoints.json"
        endpoints_file.write_text(json.dumps({
            "environments": {
                "dev": {
                    "db": {"source": "env", "key": "DEV_DB_CONN"}
                },
                "prod": {
                    "db": {"source": "env", "key": "PROD_DB_CONN"}
                }
            }
        }))

        keys = endpoint_registry_guard.load_env_keys(str(endpoints_file))
        assert "DEV_DB_CONN" in keys
        assert "PROD_DB_CONN" in keys
        assert len(keys) == 2


class TestScanDiff:
    """Test endpoint_registry_guard.scan_diff()"""

    def test_detects_hardcoded_connection_strings(self):
        """Detect hardcoded connection strings with Server=tcp:"""
        diff = """diff --git a/app.cs b/app.cs
+++ b/app.cs
@@ -10,6 +10,7 @@
+var cs = "Server=tcp:myserver.database.windows.net,1433;..."
"""
        violations = endpoint_registry_guard.scan_diff(diff, set())
        assert len(violations) == 1
        assert "connection string" in violations[0]["reason"].lower()

    def test_detects_datasource_pattern(self):
        """Detect Data Source= pattern"""
        diff = """diff --git a/config.cs b/config.cs
+++ b/config.cs
@@ -5,6 +5,7 @@
+string cs = "Data Source=mydb.example.com;..."
"""
        violations = endpoint_registry_guard.scan_diff(diff, set())
        assert len(violations) == 1

    def test_detects_azure_database_windows_net(self):
        """Detect .database.windows.net pattern"""
        diff = """diff --git a/settings.cs b/settings.cs
+++ b/settings.cs
@@ -20,6 +20,7 @@
+const host = "myserver.database.windows.net";
"""
        violations = endpoint_registry_guard.scan_diff(diff, set())
        assert len(violations) == 1

    def test_detects_initial_catalog_pattern(self):
        """Detect Initial Catalog= pattern"""
        diff = """diff --git a/db.cs b/db.cs
+++ b/db.cs
@@ -1,6 +1,7 @@
+var cs = "Initial Catalog=MyDatabase;..."
"""
        violations = endpoint_registry_guard.scan_diff(diff, set())
        assert len(violations) == 1

    def test_detects_direct_env_var_reads_for_known_keys(self):
        """Detect direct Environment.GetEnvironmentVariable() for known keys"""
        diff = """diff --git a/startup.cs b/startup.cs
+++ b/startup.cs
@@ -1,6 +1,7 @@
+var connStr = Environment.GetEnvironmentVariable("MY_DB_CONN");
"""
        known_keys = {"MY_DB_CONN"}
        violations = endpoint_registry_guard.scan_diff(diff, known_keys)
        assert len(violations) == 1
        assert "direct env var read" in violations[0]["reason"].lower()

    def test_allows_unknown_env_var_keys(self):
        """Allow Environment.GetEnvironmentVariable() for unknown keys"""
        diff = """diff --git a/app.cs b/app.cs
+++ b/app.cs
@@ -1,6 +1,7 @@
+var unknown = Environment.GetEnvironmentVariable("SOME_OTHER_VAR");
"""
        known_keys = {"MY_DB_CONN"}
        violations = endpoint_registry_guard.scan_diff(diff, known_keys)
        assert len(violations) == 0

    def test_skips_comment_lines(self):
        """Skip comment lines starting with // or #"""
        diff = """diff --git a/config.cs b/config.cs
+++ b/config.cs
@@ -1,6 +1,7 @@
+// Server=tcp:hardcoded.database.windows.net
"""
        violations = endpoint_registry_guard.scan_diff(diff, set())
        assert len(violations) == 0

    def test_skips_html_comments(self):
        """Skip HTML comment lines"""
        diff = """diff --git a/page.html b/page.html
+++ b/page.html
@@ -1,6 +1,7 @@
+<!-- Initial Catalog=secret -->
"""
        violations = endpoint_registry_guard.scan_diff(diff, set())
        assert len(violations) == 0

    def test_ignores_removed_lines(self):
        """Ignore lines starting with - (removed)"""
        diff = """diff --git a/app.cs b/app.cs
--- a/app.cs
+++ b/app.cs
@@ -1,7 +1,6 @@
-var badConn = "Server=tcp:db.database.windows.net";
"""
        violations = endpoint_registry_guard.scan_diff(diff, set())
        assert len(violations) == 0

    def test_ignores_context_lines(self):
        """Ignore context lines (without +/-)"""
        diff = """diff --git a/app.cs b/app.cs
+++ b/app.cs
@@ -1,6 +1,7 @@
 var conn = "Server=tcp:db.database.windows.net";
"""
        violations = endpoint_registry_guard.scan_diff(diff, set())
        assert len(violations) == 0

    def test_handles_empty_diff(self):
        """Handle empty diff gracefully"""
        violations = endpoint_registry_guard.scan_diff("", set())
        assert len(violations) == 0

    def test_handles_empty_known_keys(self):
        """Handle empty known_keys set gracefully"""
        diff = """diff --git a/app.cs b/app.cs
+++ b/app.cs
@@ -1,6 +1,7 @@
+var x = Environment.GetEnvironmentVariable("SOME_VAR");
"""
        violations = endpoint_registry_guard.scan_diff(diff, set())
        assert len(violations) == 0

    def test_detects_config_bracket_notation(self):
        """Detect config["ConnectionStrings notation"""
        diff = """diff --git a/startup.cs b/startup.cs
+++ b/startup.cs
@@ -5,6 +5,7 @@
+var cs = config["ConnectionStrings:Default"];
"""
        violations = endpoint_registry_guard.scan_diff(diff, set())
        assert len(violations) == 1

    def test_case_insensitive_matching(self):
        """Pattern matching is case-insensitive"""
        diff = """diff --git a/app.cs b/app.cs
+++ b/app.cs
@@ -1,6 +1,7 @@
+var cs = "server=tcp:mydb.database.windows.net";
"""
        violations = endpoint_registry_guard.scan_diff(diff, set())
        assert len(violations) == 1

    def test_multiple_violations_in_single_diff(self):
        """Detect multiple violations in a single diff"""
        diff = """diff --git a/app.cs b/app.cs
+++ b/app.cs
@@ -1,6 +1,8 @@
+var cs = "Server=tcp:mydb.database.windows.net";
+var key = Environment.GetEnvironmentVariable("MY_DB_CONN");
"""
        known_keys = {"MY_DB_CONN"}
        violations = endpoint_registry_guard.scan_diff(diff, known_keys)
        assert len(violations) == 2

    def test_tracks_file_and_line_number(self):
        """Track file path and line number for violations"""
        diff = """diff --git a/Program.cs b/Program.cs
+++ b/Program.cs
@@ -10,6 +10,7 @@
+var cs = "Server=tcp:db.database.windows.net";
"""
        violations = endpoint_registry_guard.scan_diff(diff, set())
        assert len(violations) == 1
        assert violations[0]["file"] == "Program.cs"
        assert violations[0]["line"] == 10


class TestValidateEndpoints:
    """Test endpoint_schema_validator.validate_endpoints()"""

    def test_valid_minimal_document_passes(self, tmp_path):
        """Valid minimal endpoints.json passes validation"""
        endpoints_file = tmp_path / "endpoints.json"
        endpoints_file.write_text(json.dumps({
            "$schema": "endpoints.schema.json",
            "project": "test-project",
            "environments": {
                "dev": {}
            }
        }))

        errors = endpoint_schema_validator.validate_endpoints(str(endpoints_file))
        assert len(errors) == 0

    def test_valid_env_source_passes(self, tmp_path):
        """Valid env source entry passes"""
        endpoints_file = tmp_path / "endpoints.json"
        endpoints_file.write_text(json.dumps({
            "$schema": "endpoints.schema.json",
            "project": "test-project",
            "environments": {
                "dev": {
                    "database": {
                        "source": "env",
                        "key": "DB_CONN"
                    }
                }
            }
        }))

        errors = endpoint_schema_validator.validate_endpoints(str(endpoints_file))
        assert len(errors) == 0

    def test_valid_keyvault_source_passes(self, tmp_path):
        """Valid keyvault source entry passes"""
        endpoints_file = tmp_path / "endpoints.json"
        endpoints_file.write_text(json.dumps({
            "$schema": "endpoints.schema.json",
            "project": "test-project",
            "environments": {
                "prod": {
                    "database": {
                        "source": "keyvault",
                        "vault": "my-vault",
                        "secret": "db-conn-string"
                    }
                }
            }
        }))

        errors = endpoint_schema_validator.validate_endpoints(str(endpoints_file))
        assert len(errors) == 0

    def test_valid_literal_source_passes(self, tmp_path):
        """Valid literal source entry passes"""
        endpoints_file = tmp_path / "endpoints.json"
        endpoints_file.write_text(json.dumps({
            "$schema": "endpoints.schema.json",
            "project": "test-project",
            "environments": {
                "dev": {
                    "endpoint": {
                        "source": "literal",
                        "value": "http://localhost:3000"
                    }
                }
            }
        }))

        errors = endpoint_schema_validator.validate_endpoints(str(endpoints_file))
        assert len(errors) == 0

    def test_missing_schema_is_error(self, tmp_path):
        """Missing $schema is an error"""
        endpoints_file = tmp_path / "endpoints.json"
        endpoints_file.write_text(json.dumps({
            "project": "test-project",
            "environments": {"dev": {}}
        }))

        errors = endpoint_schema_validator.validate_endpoints(str(endpoints_file))
        assert any("$schema" in err for err in errors)

    def test_missing_project_is_error(self, tmp_path):
        """Missing project is an error"""
        endpoints_file = tmp_path / "endpoints.json"
        endpoints_file.write_text(json.dumps({
            "$schema": "endpoints.schema.json",
            "environments": {"dev": {}}
        }))

        errors = endpoint_schema_validator.validate_endpoints(str(endpoints_file))
        assert any("project" in err for err in errors)

    def test_missing_environments_is_error(self, tmp_path):
        """Missing environments is an error"""
        endpoints_file = tmp_path / "endpoints.json"
        endpoints_file.write_text(json.dumps({
            "$schema": "endpoints.schema.json",
            "project": "test-project"
        }))

        errors = endpoint_schema_validator.validate_endpoints(str(endpoints_file))
        assert any("environments" in err for err in errors)

    def test_invalid_source_is_error(self, tmp_path):
        """Invalid source value is an error"""
        endpoints_file = tmp_path / "endpoints.json"
        endpoints_file.write_text(json.dumps({
            "$schema": "endpoints.schema.json",
            "project": "test-project",
            "environments": {
                "dev": {
                    "endpoint": {
                        "source": "invalid_source",
                        "value": "http://localhost"
                    }
                }
            }
        }))

        errors = endpoint_schema_validator.validate_endpoints(str(endpoints_file))
        assert any("invalid source" in err for err in errors)

    def test_env_source_missing_key_is_error(self, tmp_path):
        """env source missing 'key' is an error"""
        endpoints_file = tmp_path / "endpoints.json"
        endpoints_file.write_text(json.dumps({
            "$schema": "endpoints.schema.json",
            "project": "test-project",
            "environments": {
                "dev": {
                    "database": {
                        "source": "env"
                    }
                }
            }
        }))

        errors = endpoint_schema_validator.validate_endpoints(str(endpoints_file))
        assert any("missing 'key'" in err for err in errors)

    def test_keyvault_source_missing_vault_is_error(self, tmp_path):
        """keyvault source missing 'vault' is an error"""
        endpoints_file = tmp_path / "endpoints.json"
        endpoints_file.write_text(json.dumps({
            "$schema": "endpoints.schema.json",
            "project": "test-project",
            "environments": {
                "prod": {
                    "database": {
                        "source": "keyvault",
                        "secret": "db-conn"
                    }
                }
            }
        }))

        errors = endpoint_schema_validator.validate_endpoints(str(endpoints_file))
        assert any("missing 'vault'" in err for err in errors)

    def test_keyvault_source_missing_secret_is_error(self, tmp_path):
        """keyvault source missing 'secret' is an error"""
        endpoints_file = tmp_path / "endpoints.json"
        endpoints_file.write_text(json.dumps({
            "$schema": "endpoints.schema.json",
            "project": "test-project",
            "environments": {
                "prod": {
                    "database": {
                        "source": "keyvault",
                        "vault": "my-vault"
                    }
                }
            }
        }))

        errors = endpoint_schema_validator.validate_endpoints(str(endpoints_file))
        assert any("missing 'secret'" in err for err in errors)

    def test_literal_secret_in_prod_is_error(self, tmp_path):
        """Literal connection string in prod is an error"""
        endpoints_file = tmp_path / "endpoints.json"
        endpoints_file.write_text(json.dumps({
            "$schema": "endpoints.schema.json",
            "project": "test-project",
            "environments": {
                "prod": {
                    "database": {
                        "source": "literal",
                        "value": "Server=tcp:mydb.database.windows.net;Password=secret123"
                    }
                }
            }
        }))

        errors = endpoint_schema_validator.validate_endpoints(str(endpoints_file))
        assert any("looks like a secret" in err for err in errors)

    def test_valid_compound_endpoint(self, tmp_path):
        """Valid compound endpoint passes"""
        endpoints_file = tmp_path / "endpoints.json"
        endpoints_file.write_text(json.dumps({
            "$schema": "endpoints.schema.json",
            "project": "test-project",
            "environments": {
                "prod": {
                    "api": {
                        "host": {
                            "source": "keyvault",
                            "vault": "my-vault",
                            "secret": "api-host"
                        },
                        "port": {
                            "source": "literal",
                            "value": "443"
                        }
                    }
                }
            }
        }))

        errors = endpoint_schema_validator.validate_endpoints(str(endpoints_file))
        assert len(errors) == 0

    def test_malformed_json_returns_error(self, tmp_path):
        """Malformed JSON returns error"""
        endpoints_file = tmp_path / "endpoints.json"
        endpoints_file.write_text("{invalid json")

        errors = endpoint_schema_validator.validate_endpoints(str(endpoints_file))
        assert any("Invalid JSON" in err for err in errors)

    def test_empty_environments_is_error(self, tmp_path):
        """Empty environments object is an error"""
        endpoints_file = tmp_path / "endpoints.json"
        endpoints_file.write_text(json.dumps({
            "$schema": "endpoints.schema.json",
            "project": "test-project",
            "environments": {}
        }))

        errors = endpoint_schema_validator.validate_endpoints(str(endpoints_file))
        assert any("non-empty" in err for err in errors)

    def test_compound_with_description(self, tmp_path):
        """Compound entry with description field passes"""
        endpoints_file = tmp_path / "endpoints.json"
        endpoints_file.write_text(json.dumps({
            "$schema": "endpoints.schema.json",
            "project": "test-project",
            "environments": {
                "prod": {
                    "api": {
                        "description": "API endpoint configuration",
                        "host": {
                            "source": "keyvault",
                            "vault": "my-vault",
                            "secret": "api-host"
                        }
                    }
                }
            }
        }))

        errors = endpoint_schema_validator.validate_endpoints(str(endpoints_file))
        assert len(errors) == 0

    def test_url_not_flagged_as_suspicious_key(self, tmp_path):
        """Long URL in prod literal is not flagged as suspicious key"""
        endpoints_file = tmp_path / "endpoints.json"
        endpoints_file.write_text(json.dumps({
            "$schema": "endpoints.schema.json",
            "project": "test-project",
            "environments": {
                "prod": {
                    "endpoint": {
                        "source": "literal",
                        "value": "https://verylongdomainnamethatisveryverylongindeed.azurewebsites.net/path/to/api"
                    }
                }
            }
        }))

        errors = endpoint_schema_validator.validate_endpoints(str(endpoints_file))
        assert len(errors) == 0


class TestMainExitCodes:
    """Test main() function exit codes"""

    def test_returns_0_for_non_commit_tool(self):
        """Returns 0 when tool is not Bash"""
        hook_input = json.dumps({
            "tool_name": "Python",
            "tool_input": {"command": "git commit"}
        })

        with patch("json.load", return_value=json.loads(hook_input)):
            result = endpoint_registry_guard.main()

        assert result == 0

    def test_returns_0_for_non_commit_command(self):
        """Returns 0 when command is not 'git commit'"""
        hook_input = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "git status"}
        })

        with patch("json.load", return_value=json.loads(hook_input)):
            result = endpoint_registry_guard.main()

        assert result == 0

    def test_returns_0_for_empty_stdin(self):
        """Returns 0 when stdin is empty"""
        with patch("json.load", side_effect=EOFError):
            result = endpoint_registry_guard.main()

        assert result == 0

    def test_returns_0_for_invalid_json(self):
        """Returns 0 when stdin is invalid JSON"""
        with patch("json.load", side_effect=json.JSONDecodeError("msg", "doc", 0)):
            result = endpoint_registry_guard.main()

        assert result == 0

    def test_validator_returns_0_for_non_commit_tool(self):
        """Validator returns 0 when tool is not Bash"""
        hook_input = json.dumps({
            "tool_name": "Python",
            "tool_input": {"command": "git commit"}
        })

        with patch("json.load", return_value=json.loads(hook_input)):
            result = endpoint_schema_validator.main()

        assert result == 0

    def test_validator_returns_0_for_empty_stdin(self):
        """Validator returns 0 when stdin is empty"""
        with patch("json.load", side_effect=EOFError):
            result = endpoint_schema_validator.main()

        assert result == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
