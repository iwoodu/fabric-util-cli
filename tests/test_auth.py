import unittest
from unittest.mock import Mock, patch

from fabutil.auth import (
    POWER_BI_SCOPE,
    AuthenticationError,
    acquire_access_token,
)


class InteractiveAuthenticationTests(unittest.TestCase):
    @patch("fabutil.auth.msal.PublicClientApplication")
    @patch("fabutil.auth._create_token_cache", return_value="token-cache")
    def test_acquires_token_interactively_as_current_user(
        self, _create_token_cache: Mock, public_client: Mock
    ) -> None:
        app = public_client.return_value
        app.get_accounts.return_value = []
        app.acquire_token_interactive.return_value = {"access_token": "user-token"}

        token = acquire_access_token("tenant-id", "client-id")

        self.assertEqual(token, "user-token")
        public_client.assert_called_once_with(
            client_id="client-id",
            authority="https://login.microsoftonline.com/tenant-id",
            token_cache="token-cache",
        )
        app.acquire_token_interactive.assert_called_once_with(
            scopes=[POWER_BI_SCOPE],
            prompt="select_account",
        )
        app.acquire_token_silent.assert_not_called()

    @patch("fabutil.auth.msal.PublicClientApplication")
    @patch("fabutil.auth._create_token_cache", return_value="token-cache")
    def test_reuses_cached_token_without_interactive_sign_in(
        self, _create_token_cache: Mock, public_client: Mock
    ) -> None:
        app = public_client.return_value
        account = {"username": "user@example.com"}
        app.get_accounts.return_value = [account]
        app.acquire_token_silent.return_value = {"access_token": "cached-token"}

        token = acquire_access_token("tenant-id", "client-id")

        self.assertEqual(token, "cached-token")
        app.acquire_token_silent.assert_called_once_with(
            scopes=[POWER_BI_SCOPE],
            account=account,
        )
        app.acquire_token_interactive.assert_not_called()

    @patch("fabutil.auth.msal.PublicClientApplication")
    @patch("fabutil.auth._create_token_cache", return_value="token-cache")
    def test_falls_back_to_interactive_sign_in_when_silent_acquisition_fails(
        self, _create_token_cache: Mock, public_client: Mock
    ) -> None:
        app = public_client.return_value
        app.get_accounts.return_value = [{"username": "user@example.com"}]
        app.acquire_token_silent.return_value = None
        app.acquire_token_interactive.return_value = {"access_token": "new-token"}

        token = acquire_access_token("tenant-id", "client-id")

        self.assertEqual(token, "new-token")
        app.acquire_token_interactive.assert_called_once_with(
            scopes=[POWER_BI_SCOPE],
            prompt="select_account",
        )

    @patch("fabutil.auth.msal.PublicClientApplication")
    @patch("fabutil.auth._create_token_cache", return_value="token-cache")
    def test_asks_user_to_select_when_multiple_accounts_are_cached(
        self, _create_token_cache: Mock, public_client: Mock
    ) -> None:
        app = public_client.return_value
        app.get_accounts.return_value = [
            {"username": "one@example.com"},
            {"username": "two@example.com"},
        ]
        app.acquire_token_interactive.return_value = {"access_token": "user-token"}

        token = acquire_access_token("tenant-id", "client-id")

        self.assertEqual(token, "user-token")
        app.acquire_token_silent.assert_not_called()
        app.acquire_token_interactive.assert_called_once_with(
            scopes=[POWER_BI_SCOPE],
            prompt="select_account",
        )

    @patch("fabutil.auth.msal.PublicClientApplication")
    @patch("fabutil.auth._create_token_cache", return_value="token-cache")
    def test_reports_interactive_sign_in_failure(
        self, _create_token_cache: Mock, public_client: Mock
    ) -> None:
        public_client.return_value.get_accounts.return_value = []
        public_client.return_value.acquire_token_interactive.return_value = {
            "error": "invalid_grant",
            "error_description": "User cancelled sign-in.",
        }

        with self.assertRaisesRegex(AuthenticationError, "User cancelled"):
            acquire_access_token("tenant-id", "client-id")


if __name__ == "__main__":
    unittest.main()
