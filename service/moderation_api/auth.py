from __future__ import annotations

import hmac
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Header, HTTPException, status

from .config import ClientCredential


@dataclass(frozen=True, slots=True)
class Principal:
    client_id: str
    permissions: frozenset[str]


class Authenticator:
    def __init__(self, clients: tuple[ClientCredential, ...]) -> None:
        self._clients = {client.client_id: client for client in clients}

    def authenticate(self, client_id: str | None, authorization: str | None) -> Principal:
        if not client_id or not authorization:
            raise _unauthorized()
        credential = self._clients.get(client_id)
        token = _bearer_token(authorization)
        if credential is None or token is None:
            raise _unauthorized()
        if not hmac.compare_digest(credential.token, token):
            raise _unauthorized()
        return Principal(credential.client_id, credential.permissions)


def permission_dependency(
    authenticator: Authenticator,
    permission: str,
) -> Callable[..., Awaitable[Principal]]:
    async def dependency(
        x_client_id: Annotated[str | None, Header()] = None,
        authorization: Annotated[str | None, Header()] = None,
    ) -> Principal:
        principal = authenticator.authenticate(x_client_id, authorization)
        if permission not in principal.permissions:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="permission denied")
        return principal

    return dependency


def _bearer_token(value: str) -> str | None:
    scheme, separator, token = value.partition(" ")
    if separator and scheme.lower() == "bearer" and token:
        return token
    return None


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid client credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
