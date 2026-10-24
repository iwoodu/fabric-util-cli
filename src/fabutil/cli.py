"""Command-line entry point."""

import argparse
import json
import os
import sys
from collections.abc import Sequence

import requests

from fabutil.auth import AuthenticationError, acquire_access_token
from fabutil.powerbi import PowerBIAPIError, list_tenant_capacities


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fabutil",
        description="Command-line tools for Microsoft Fabric and Power BI.",
    )
    groups = parser.add_subparsers(dest="command_group", required=True)
    capacity_parser = groups.add_parser("capacity", help="Manage capacities.")
    capacity_commands = capacity_parser.add_subparsers(
        dest="command", required=True
    )
    list_parser = capacity_commands.add_parser(
        "list", help="List capacities across the tenant."
    )
    list_parser.add_argument(
        "--tenant-id",
        default=os.getenv("FABUTIL_TENANT_ID"),
        help="Microsoft Entra tenant ID (or FABUTIL_TENANT_ID).",
    )
    list_parser.add_argument(
        "--client-id",
        default=os.getenv("FABUTIL_CLIENT_ID"),
        help="Entra public-client app ID (or FABUTIL_CLIENT_ID).",
    )
    list_parser.add_argument(
        "--output",
        choices=("table", "json"),
        default="table",
        help="Output format (default: table).",
    )
    return parser


def _format_table(capacities: list[dict[str, object]]) -> str:
    columns = ("displayName", "sku", "state", "region", "id")
    headers = ("NAME", "SKU", "STATE", "REGION", "ID")
    rows = [
        [str(capacity.get(column) or "-") for column in columns]
        for capacity in capacities
    ]
    widths = [
        max(len(header), *(len(row[index]) for row in rows))
        for index, header in enumerate(headers)
    ]
    lines = [
        "  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)),
        "  ".join("-" * width for width in widths),
    ]
    lines.extend(
        "  ".join(value.ljust(widths[index]) for index, value in enumerate(row))
        for row in rows
    )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.tenant_id:
        parser.error("provide --tenant-id or set FABUTIL_TENANT_ID")
    if not args.client_id:
        parser.error("provide --client-id or set FABUTIL_CLIENT_ID")

    try:
        access_token = acquire_access_token(args.tenant_id, args.client_id)
        capacities = list_tenant_capacities(access_token)
    except AuthenticationError as exc:
        print(f"Authentication error: {exc}", file=sys.stderr)
        return 1
    except PowerBIAPIError as exc:
        print(f"Power BI API error: {exc}", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"Network error communicating with Microsoft APIs: {exc}", file=sys.stderr)
        return 1

    if args.output == "json":
        print(json.dumps(capacities, indent=2))
    else:
        print(_format_table(capacities))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
