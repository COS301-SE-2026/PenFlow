import os
from typing import Any

import httpx

class KeycloakAdminError(RuntimeError):
    def __init__(self, message:str, status_code: int | None=None) -> None:
        super().__init__(message)
        self.status_code=status_code


class KeycloakAdminService:
    def __init__(self) -> None:
        self.base_url = os.getenv(
            "KEYCLOAK_ADMIN_URL", 
            "http://localhost:8080",
        ).rstrip("/")

        self.realm = os.getenv("KEYCLOAK_ADMIN_REALM", "penflow")

        self.client_id = os.getenv(
            "KEYCLOAK_PROVISIONER_CLIENT_ID",
            "penflow-user-provisioner",
        )

        self.client_secret = os.getenv(
            "KEYCLOAK_PROVISIONER_CLIENT_SECRET",
        )

        self.invite_client_id = os.getenv(
            "KEYCLOAK_INVITE_CLIENT_ID",
            "penflow-web",
        )

        self.invite_redirect_uri = os.getenv(
            "KEYCLOAK_INVITE_REDIRECT_URI",
            "http://localhost:3000/login",
        )

        self.invite_lifespan_seconds = int(
            os.getenv(
                "KEYCLOAK_INVITE_LIFESPAN_SECONDS",
                "86400",
            )
        )

        self.timeout = httpx.Timeout(10.0)

        if not self.client_secret:
            raise RuntimeError("KEYCLOAK_PROVISIONER_CLIENT_SECRET env var is not configured")


    async def get_access_token(self) -> str:
        token_url = (f"{self.base_url}/realms/{self.realm}"
        "/protocol/openid-connect/token")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    token_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret
                    }
                )

        except httpx.RequestError as err:
            raise KeycloakAdminError("Unable to connect to Keyclaok") from err

        if response.status_code != 200:
            raise KeycloakAdminError(
                "Keycloak service-account authentication failed.",
                status_code=response.status_code,
            )

        token= response.json().get("access_token")

        if not isinstance(token, str) or not token:
            raise KeycloakAdminError(
                "Keycloak did not return an access token",
            )

        return token


    async def request(
            self, 
            method: str, 
            path: str, 
            expected_statuses: set[int], 
            json: Any | None = None, 
            params: dict[str, Any] | None = None
    ) -> httpx.Response:
        token = await self.get_access_token()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method,
                    f"{self.base_url}{path}",
                    headers={
                        "Authorization": f"Bearer {token}",
                    },
                    json=json,
                    params=params,
                )

        except httpx.RequestError as err:
            raise KeycloakAdminError(
                "Unable to connect to Keycloak",
            ) from err

        if response.status_code not in expected_statuses:
            raise KeycloakAdminError(
                "Keycloak admin reuqest failed.",
                status_code=response.status_code,
            )

        return response


    async def create_pentester(
            self,
            email: str,
            full_name: str,
    ) -> str:

        normalized_email = email.strip().lower()
        normalized_name = full_name.strip()

        name_parts = normalized_name.split(maxsplit=1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        response = await self.request(
            "POST",
            f"/admin/realms/{self.realm}/users",
            expected_statuses={201},
            json={
                "username": normalized_email,
                "email": normalized_email,
                "firstName": first_name,
                "lastName": last_name,
                "enabled": True,
                "emailVerified": False,
                "requiredActions": [
                    "VERIFY_EMAIL",
                    "UPDATE_PASSWORD",
                ],
            },
        )

        location = response.headers.get("Location")

        if not location:
            raise KeycloakAdminError(
                "Keylcoak created the user without returning its identifier."
            )

        user_id = location.rstrip("/").rsplit("/", maxsplit=1)[-1]

        if not user_id:
            raise KeycloakAdminError("Keycloak returned invalid identifer")

        return user_id


    async def assign_pentester_role(self, user_id: str) -> None:
        role_resp = await self.request(
            "GET",
            f"/admin/realms/{self.realm}/roles/pentester",
            expected_statuses={200},
        )

        role = role_resp.json()

        await self.request(
            "POST",
            (
                f"/admin/realms/{self.realm}/users/{user_id}"
                "/role-mappings/realm"
            ),
            expected_statuses={204},
            json=[role],
        )


    async def send_activation_email(
            self,
            user_id: str,
    ) -> None:
            
        await self.request(
            "PUT",
            (
                f"/admin/realms/{self.realm}/users/{user_id}"
                "/execute-actions-email"
            ),
            expected_statuses={204},
            params={
                "client_id": self.invite_client_id,
                "redirect_uri": self.invite_redirect_uri,
                "lifespan": self.invite_lifespan_seconds,
            },
            json=[
                    "VERIFY_EMAIL",
                    "UPDATE_PASSWORD",
                ],
        )

    async def disable_user(self, user_id: str) -> None:
        await self.request(
            "PUT",
            f"/admin/realms/{self.realm}/users/{user_id}",
            expected_statuses={204},
            json={
                "enabled": False,
            },
        )


    async def delete_user(self, user_id:str) -> None:
        await self.request(
            "DELETE",
            f"/admin/realms/{self.realm}/users/{user_id}",
            expected_statuses={204, 404},
        )

