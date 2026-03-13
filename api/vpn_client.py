from typing import Any

import httpx

from bot.config import config


class VPNAPIError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class VPNClient:
    def __init__(self):
        self.base_url = config.VPN_API_URL
        self.email = config.VPN_API_EMAIL
        self.password = config.VPN_API_PASSWORD
        self._token: str | None = None
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def _ensure_token(self) -> str:
        if self._token:
            return self._token

        client = await self._get_client()
        response = await client.post(
            f"{self.base_url}/api/auth/token",
            data={"email": self.email, "password": self.password},
        )

        if response.status_code != 200:
            raise VPNAPIError(
                "Failed to authenticate with VPN API", response.status_code
            )

        data = response.json()
        self._token = data.get("access_token") or data.get("token")
        return self._token

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        json_data: dict | None = None,
        files: dict | None = None,
    ) -> dict[str, Any]:
        client = await self._get_client()
        token = await self._ensure_token()

        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}{endpoint}"

        response = await client.request(
            method, url, headers=headers, params=params, json=json_data, files=files
        )

        if response.status_code == 401:
            self._token = None
            token = await self._ensure_token()
            headers["Authorization"] = f"Bearer {token}"
            response = await client.request(
                method, url, headers=headers, params=params, json=json_data, files=files
            )

        if response.status_code not in (200, 201):
            try:
                error_data = response.json()
                message = error_data.get(
                    "detail", error_data.get("message", "Unknown error")
                )
            except Exception:
                message = response.text or "Unknown error"
            raise VPNAPIError(message, response.status_code)

        return response.json()

    async def get_servers(self) -> list[dict]:
        """Get list of all servers"""
        response = await self._request("GET", "/api/servers")
        return response.get("servers", [])

    async def get_server_clients(self, server_id: int) -> list[dict]:
        """Get clients on a specific server"""
        response = await self._request("GET", f"/api/servers/{server_id}/clients")
        return response.get("clients", [])

    async def get_clients(self) -> list[dict]:
        """Get list of all clients"""
        response = await self._request("GET", "/api/clients")
        return response.get("clients", [])

    async def get_client_details(self, client_id: int) -> dict:
        """Get client details with stats, config and QR code"""
        response = await self._request("GET", f"/api/clients/{client_id}/details")
        return response.get("client", response)

    async def get_client_qr(self, client_id: int) -> dict:
        """Get client QR code"""
        response = await self._request("GET", f"/api/clients/{client_id}/qr")
        qr_data = response.get("qr", response)

        # Если QR-код в формате data:image/png;base64,...
        if isinstance(qr_data, dict) and "qr_code" in qr_data:
            qr_code = qr_data["qr_code"]
            if qr_code.startswith("data:image/"):
                # Извлекаем base64 часть
                base64_part = qr_code.split(",", 1)[1] if "," in qr_code else qr_code
                qr_data["qr_code_base64"] = base64_part

        return qr_data

    async def create_client(
        self, server_id: int, name: str, expires_in_days: int | None = None
    ) -> dict:
        """Create new client (returns config and QR code)"""
        data = {"server_id": server_id, "name": name}
        if expires_in_days is not None:
            data["expires_in_days"] = expires_in_days
        response = await self._request("POST", "/api/clients/create", json_data=data)
        return response.get("client", response)

    async def revoke_client(self, client_id: int) -> dict:
        """Revoke client access"""
        return await self._request("POST", f"/api/clients/{client_id}/revoke")

    async def restore_client(self, client_id: int) -> dict:
        """Restore client access"""
        return await self._request("POST", f"/api/clients/{client_id}/restore")

    async def delete_client(self, client_id: int) -> dict:
        """Delete client by ID"""
        return await self._request("DELETE", f"/api/clients/{client_id}/delete")

    async def set_client_expiration(
        self, client_id: int, expires_at: str | None
    ) -> dict:
        """Set client expiration date"""
        data = {"expires_at": expires_at}
        return await self._request(
            "POST", f"/api/clients/{client_id}/set-expiration", json_data=data
        )

    async def extend_client(self, client_id: int, days: int) -> dict:
        """Extend client expiration"""
        data = {"days": days}
        return await self._request(
            "POST", f"/api/clients/{client_id}/extend", json_data=data
        )

    async def create_backup(self, server_id: int) -> dict:
        """Create server backup"""
        return await self._request("POST", f"/api/servers/{server_id}/backup")

    async def get_backups(self, server_id: int) -> list[dict]:
        """Get list of server backups"""
        response = await self._request("GET", f"/api/servers/{server_id}/backups")
        return response.get("backups", [])
        """Set client traffic limit"""
        data = {"limit_bytes": limit_bytes}
        return await self._request(
            "POST", f"/api/clients/{client_id}/set-traffic-limit", json_data=data
        )

    async def get_traffic_limit_status(self, client_id: int) -> dict:
        """Get traffic limit status"""
        return await self._request(
            "GET", f"/api/clients/{client_id}/traffic-limit-status"
        )

    async def close(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None


vpn_client = VPNClient()
