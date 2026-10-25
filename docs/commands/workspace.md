# `workspace` command group

## `list` command
List workspaces assigned to a capacity.

`--capacity` option may be specified as the capacity name or ID.

By default, output is written to `stdout` in tabular format. The `--output json` option overrides this behavior.

```sh
fabutil workspace list --capacity "Finance" --output json
```
List workspaces under the Finance capacity. Output to `stdout` as a JSON array.

```sh
fabutil workspace list --capacity "a0b1c2d3-e4f5-4678-9012-3456789abcde"
```
List workspaces under the given capacity. Output to `stdout` in tabular format.


> [!WARNING]
> Capacity names are matched exactly, without regard to case. If more than one
capacity has that name, provide its ID instead.
