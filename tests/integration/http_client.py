"""Thin HTTP helpers for integration tests."""

from __future__ import annotations

from typing import Any

import httpx

from settings import StackSettings


class ControlPlaneClient:
    """Authenticated client spanning IAM, registry, inventory, and projects."""

    def __init__(self, http: httpx.Client, stack: StackSettings, token: str) -> None:
        self._http = http
        self._stack = stack
        self._token = token
        self._auth = {"Authorization": f"Bearer {token}"}

    @property
    def token(self) -> str:
        return self._token

    @property
    def stack(self) -> StackSettings:
        return self._stack

    def _request(
        self,
        method: str,
        url: str,
        *,
        auth: bool = True,
        **kwargs: Any,
    ) -> httpx.Response:
        headers = dict(kwargs.pop("headers", {}) or {})
        if auth:
            headers.update(self._auth)
        return self._http.request(method, url, headers=headers, **kwargs)

    def get(self, url: str, *, auth: bool = True, **kwargs: Any) -> httpx.Response:
        return self._request("GET", url, auth=auth, **kwargs)

    def post(self, url: str, *, auth: bool = True, **kwargs: Any) -> httpx.Response:
        return self._request("POST", url, auth=auth, **kwargs)

    def put(self, url: str, *, auth: bool = True, **kwargs: Any) -> httpx.Response:
        return self._request("PUT", url, auth=auth, **kwargs)

    def delete(self, url: str, *, auth: bool = True, **kwargs: Any) -> httpx.Response:
        return self._request("DELETE", url, auth=auth, **kwargs)

    def _url(self, base: str, path: str) -> str:
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{base}{path}"

    def iam(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        return self._request(method.upper(), self._url(self._stack.iam_url, path), **kwargs)

    def registry(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        return self._request(method.upper(), self._url(self._stack.registry_url, path), **kwargs)

    def inventory(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        return self._request(method.upper(), self._url(self._stack.inventory_url, path), **kwargs)

    def projects(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        return self._request(method.upper(), self._url(self._stack.projects_url, path), **kwargs)

    def web(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        return self._request(method.upper(), self._url(self._stack.web_url, path), **kwargs)
