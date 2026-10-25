# `item` command group

## `list` command
List active items across the Fabric tenant, or narrow the displayed results by workspace, capacity and/or item type.

```sh
fabutil item list
```
List all active items to `stdout` in tabular format.

```sh
fabutil item list --workspace "Finance"
```
List active items in the Finance workspace.

```sh
fabutil item list --capacity "Premium"
```
List active items in workspaces assigned to the Premium capacity.

By default, output is written to `stdout` in tabular format. The `--output json` option overrides this behavior.

```sh
fabutil item list --capacity "a0b1c2d3-e4f5-4678-9012-3456789abcde" --workspace "aaaaaaaa-0000-1111-2222-bbbbbbbbbbbb" --type "Lakehouse" --output json
```
List active Lakehouse items in the workspace with the given workspace id, provided the workspace is under the capacity with the given capacity id. List the items as a JSON array.


`--workspace` and `--capacity` each accept an ID or a case-insensitive exact name match. Duplicate names are ambiguous; provide an ID instead.


> [!CAUTION]
> This command uses functionality that is in Preview. It is not recommended for production use or business critical tasks.

> [!NOTE]
> See the official reference for
[supported item types](https://learn.microsoft.com/en-us/rest/api/fabric/core/items/list-items#itemtype).
