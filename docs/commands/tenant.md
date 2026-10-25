# `tenant` command group

## `settings` sub-command group
The settings sub-command group is scoped to the Fabric tenant settings.

### `list` command
List all Fabric tenant settings.

By default, output is written to `stdout` in tabular format. The `--output json` option overrides this behavior.

```sh
fabutil tenant settings list
```
List tenant settings to `stdout` in tabular format.

```sh
fabutil tenant settings list --output json
```
List tenant settings to `stdout` as a JSON array.

## `overrides` sub-command group
The overrides sub-command group is scoped to operations against tenant settings overridden by a capacity, domain, or workspace.

### `list` command
List capacity, domain, and workspace tenant setting overrides to `stdout` in tabular format, or restrict the results to one scope.

```sh
fabutil tenant overrides list
```
List capacity, domain, and workspace tenant setting overrides.

```sh
fabutil tenant overrides list --scope capacity
```
List only capacity tenant setting overrides.

```sh
fabutil tenant overrides list --scope domain
```
List only domain tenant setting overrides.

```sh
fabutil tenant overrides list --scope workspace --output json
```
List only workspace tenant setting overrides. Output to `stdout` as a JSON array.
