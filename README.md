# fabutil

A CLI for Microsoft Fabric and Power BI administrators. All commands require Fabric Administrator access and do not assume access to workspaces.

## Get started
### What you need
* Python 3.10 or later

### Install the CLI

Install Python 3.10 or later and Git. Create and activate a virtual environment.

Python is needed on `PATH` when creating the virtual environment and installing or upgrading `fabutil`. When the virtual environment is activated, you can run fabutil directly without prefixing it with `python`.

Install `fabutil` from GitHub:

**macOS / Linux**

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "git+https://github.com/iwoodu/fabric-util-cli.git"
```

**Windows PowerShell**

```powershell
py -3.10 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install "git+https://github.com/iwoodu/fabric-util-cli.git"
```

**Verify installation**

```sh
fabutil --help
```

### Upgrade CLI
To upgrade, activate the same virtual environment and run:

```sh
python -m pip install --upgrade "git+https://github.com/iwoodu/fabric-util-cli.git"
```

### Authentication
The CLI requires user authentication. Service principals are not supported.

The CLI checks if you are authenticated with Microsoft Fabric. If you are not signed in, then the CLI will initiate an interactive user sign-in flow.

## Usage Instructions
Commands use this shape:

```text
fabutil [command-group] [command] [options]
```

Commands by default output in console friendly, tabular format.

Commands support JSON output using the `--output json` option.

Use OS utilities, like `jq` to apply custom filtering, sorting, and other decorations. For example:

```sh
fabutil capacity list --output json | jq '[.[] | select(.sku == "PP3" and (.state | ascii_downcase) == "active")]'
```

## CLI command groups

The CLI supports the following command groups:

* [capacity](docs/commands/capacity.md)
* [item](docs/commands/item.md)
* [refreshable](docs/commands/refreshable.md)
* [tenant](docs/commands/tenant.md)
* [workspace](docs/commands/workspace.md)

For usage details, run `fabutil --help` or see the [command reference](docs/commands.md).
