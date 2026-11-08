"""Interactive Microsoft Entra authentication for the current user."""

import os
from pathlib import Path

import msal
from msal_extensions import PersistedTokenCache, build_encrypted_persistence


class AuthenticationError(Exception):
    """Raised when interactive sign-in cannot provide an access token."""


POWER_BI_SCOPE = "https://analysis.windows.net/powerbi/api/Tenant.Read.All"
FABRIC_SCOPE = "https://api.fabric.microsoft.com/Tenant.Read.All"
AZURE_MANAGEMENT_SCOPE = "https://management.azure.com/user_impersonation"


def _create_token_cache() -> PersistedTokenCache:
    cache_directory = Path.home() / ".fabutil"
    cache_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name == "posix":
        cache_directory.chmod(0o700)
    return PersistedTokenCache(
        build_encrypted_persistence(str(cache_directory / "token_cache.bin"))
    )


def acquire_access_token(tenant_id: str, client_id: str, scope: str) -> str:
    app = msal.PublicClientApplication(
        client_id=client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        token_cache=_create_token_cache(),
    )
    accounts = app.get_accounts()
    account = accounts[0] if len(accounts) == 1 else None
    if account is not None:
        result = app.acquire_token_silent(scopes=[scope], account=account)
    else:
        result = None

    if not result or not result.get("access_token"):
        result = app.acquire_token_interactive(
            scopes=[scope],
            prompt="select_account",
        )

    access_token = result.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        detail = result.get(
            "error_description",
            "Interactive sign-in did not return an access token.",
        )
        raise AuthenticationError(detail)

    return access_token
