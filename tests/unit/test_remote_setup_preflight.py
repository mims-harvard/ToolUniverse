import json
import os
import unittest
from unittest.mock import patch

from scripts.remote_validation import setup_skill_preflight as preflight
from tooluniverse.cli import _remote_tool_install_hint


class RemoteSetupPreflightTests(unittest.TestCase):
    def test_catalog_matches_the_runtime_deployment_table(self):
        """The preflight catalog and the runtime table are the same inventory.

        This used to assert the literals 30 and 41. It went red the moment the
        thirty-first provider landed and stayed red through fifteen more, which
        is what a written-down count always does: it stops testing the thing and
        starts testing the number. `test_remote_runtime` asserts the table's own
        size; this asserts that the two agree, slug for slug and port for port,
        which is the property that actually matters -- a provider present in one
        and absent from the other is a provider an operator cannot preflight.
        """
        from tooluniverse.remote_runtime import REMOTE_DEPLOYMENTS

        catalog = {item.slug: item for item in preflight.DEPLOYMENTS}
        runtime = {item.slug: item for item in REMOTE_DEPLOYMENTS}
        self.assertEqual(sorted(catalog), sorted(runtime))
        self.assertEqual(
            {slug: item.port for slug, item in catalog.items()},
            {slug: item.port for slug, item in runtime.items()},
        )
        self.assertEqual(
            {slug: tuple(item.operations) for slug, item in catalog.items()},
            {slug: tuple(item.operations) for slug, item in runtime.items()},
        )
        # Ports are the scheduling identity of a provider; two sharing one would
        # make the second unreachable.
        self.assertEqual(
            len({item.port for item in preflight.DEPLOYMENTS}), len(catalog)
        )

    def test_every_setup_skill_matches_the_shared_contract(self):
        failures = {
            item.slug: preflight._skill_contract(item)
            for item in preflight.DEPLOYMENTS
            if not preflight._skill_contract(item)["ok"]
        }
        self.assertEqual(failures, {})

    def test_secret_preflight_reports_presence_without_value(self):
        secret = "must-not-appear-in-preflight-output"
        deployment = preflight.BY_SLUG["uspto-downloader"]
        with patch.dict(os.environ, {"USPTO_API_KEY": secret}, clear=True):
            result = preflight._provider_environment(deployment)
        rendered = json.dumps(result)
        self.assertTrue(result["ok"])
        self.assertNotIn(secret, rendered)
        self.assertEqual(
            result["variables"],
            [{"name": "USPTO_API_KEY", "set": True, "secret": True}],
        )

    def test_connect_preflight_never_discloses_service_key(self):
        secret = "must-not-appear-in-connect-output"
        with (
            patch.dict(os.environ, {"TOOLUNIVERSE_SERVICE_KEY": secret}, clear=True),
            patch("importlib.util.find_spec", return_value=None),
        ):
            result = preflight._connect_prerequisites()
        self.assertFalse(result["ok"])
        self.assertTrue(result["service_key_set"])
        self.assertFalse(result["service_key_value_disclosed"])
        self.assertNotIn(secret, json.dumps(result))

    def test_cli_install_hint_explains_private_distribution_prerequisite(self):
        hint = _remote_tool_install_hint()
        self.assertIn("not published on PyPI", hint)
        self.assertIn("public wheel", hint)
        self.assertIn("connect.aiscientist.tools/downloads", hint)
        self.assertIn(
            "3fad5eee5ecf7887a693d93ccd1aa112dc0955617a885d1fc3daded0030f9ae0", hint
        )
        self.assertNotIn("github.com", hint)


if __name__ == "__main__":
    unittest.main()
