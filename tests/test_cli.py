import contextlib
import io
import json
import unittest
from unittest.mock import Mock, call, patch

from fabutil.auth import FABRIC_SCOPE, POWER_BI_SCOPE
from fabutil.cli import main


CAPACITY_ID = "a0b1c2d3-e4f5-4678-9012-3456789abcde"


class CapacityListCommandTests(unittest.TestCase):
    @patch("fabutil.cli.list_tenant_capacities")
    @patch("fabutil.cli.acquire_access_token", return_value="user-token")
    def test_outputs_all_capacities_as_json(
        self, _acquire_token: Mock, list_capacities: Mock
    ) -> None:
        capacities = [
            {"id": CAPACITY_ID, "region": "West US"},
            {"id": "b0b1c2d3-e4f5-4678-9012-3456789abcde", "region": "East US"},
        ]
        list_capacities.return_value = capacities
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            result = main(
                [
                    "capacity",
                    "list",
                    "--tenant-id",
                    "tenant-id",
                    "--client-id",
                    "client-id",
                    "--output",
                    "json",
                ]
            )

        self.assertEqual(result, 0)
        self.assertEqual(json.loads(stdout.getvalue()), capacities)

    @patch("fabutil.cli.list_tenant_capacities", return_value=[])
    @patch("fabutil.cli.acquire_access_token", return_value="user-token")
    def test_separates_table_output_with_blank_lines(
        self, _acquire_token: Mock, _list_capacities: Mock
    ) -> None:
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            result = main(
                [
                    "capacity",
                    "list",
                    "--tenant-id",
                    "tenant-id",
                    "--client-id",
                    "client-id",
                ]
            )

        self.assertEqual(result, 0)
        self.assertTrue(stdout.getvalue().startswith("\nNAME"))
        self.assertTrue(stdout.getvalue().endswith("\n\n"))


class WorkspaceListCommandTests(unittest.TestCase):
    @patch("fabutil.cli.list_capacity_workspaces")
    @patch("fabutil.cli.acquire_access_token", return_value="fabric-token")
    def test_lists_workspaces_by_capacity_id(
        self, acquire_token: Mock, list_workspaces: Mock
    ) -> None:
        workspaces = [{"id": "workspace-id", "name": "Finance"}]
        list_workspaces.return_value = workspaces
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            result = main(
                [
                    "workspace",
                    "list",
                    "--capacity",
                    CAPACITY_ID,
                    "--tenant-id",
                    "tenant-id",
                    "--client-id",
                    "client-id",
                    "--output",
                    "json",
                ]
            )

        self.assertEqual(result, 0)
        self.assertEqual(json.loads(stdout.getvalue()), workspaces)
        acquire_token.assert_called_once_with("tenant-id", "client-id", FABRIC_SCOPE)
        list_workspaces.assert_called_once_with("fabric-token", CAPACITY_ID)

    @patch("fabutil.cli.list_capacity_workspaces", return_value=[])
    @patch("fabutil.cli.resolve_capacity_id", return_value=CAPACITY_ID)
    @patch(
        "fabutil.cli.acquire_access_token",
        side_effect=["powerbi-token", "fabric-token"],
    )
    def test_resolves_capacity_name_using_power_bi_then_fabric(
        self,
        acquire_token: Mock,
        resolve_capacity: Mock,
        list_workspaces: Mock,
    ) -> None:
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            result = main(
                [
                    "workspace",
                    "list",
                    "--capacity",
                    "Finance",
                    "--tenant-id",
                    "tenant-id",
                    "--client-id",
                    "client-id",
                ]
            )

        self.assertEqual(result, 0)
        self.assertTrue(stdout.getvalue().startswith("\nNAME"))
        self.assertTrue(stdout.getvalue().endswith("\n\n"))
        self.assertEqual(
            acquire_token.call_args_list,
            [
                call("tenant-id", "client-id", POWER_BI_SCOPE),
                call("tenant-id", "client-id", FABRIC_SCOPE),
            ],
        )
        resolve_capacity.assert_called_once_with("powerbi-token", "Finance")
        list_workspaces.assert_called_once_with("fabric-token", CAPACITY_ID)


if __name__ == "__main__":
    unittest.main()
