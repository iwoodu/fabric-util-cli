import contextlib
import io
import json
import unittest
from unittest.mock import Mock, patch

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


if __name__ == "__main__":
    unittest.main()
