"""Bounded GitHub HTTPS transport; no proxies, redirects, retries or raw errors."""

from dataclasses import dataclass
from http.client import HTTPSConnection

from . import journal_schema as schema
from .journal_errors import JournalError, require


@dataclass(frozen=True, repr=False)
class Response:
    status: int
    data: object
    has_next: bool


class GitHubTransport:
    def __init__(self, token):
        schema.pattern(token, r"[A-Za-z0-9_.-]{1,8192}")
        self._token = token

    def request(self, method, path, body=None):
        require(method in ("GET", "POST"))
        schema.pattern(
            path, r"/repos/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/deployments(?:\?[A-Za-z0-9_=&.-]+)?)?"
        )
        connection = HTTPSConnection("api.github.com", timeout=8)
        try:
            connection.request(
                method,
                path,
                body=None if body is None else schema.encode(body),
                headers={
                    "Authorization": "Bearer " + self._token,
                    "Accept": "application/vnd.github+json",
                    "Content-Type": "application/json",
                    "X-GitHub-Api-Version": "2026-03-10",
                    "User-Agent": "oci-invoice-investigator",
                },
            )
            response = connection.getresponse()
            require(not 300 <= response.status < 400, "github_unavailable")
            raw = response.read(schema.LIMIT + 1)
            # Error bodies can contain private diagnostics; they have no authority.
            data = schema.decode(raw) if response.status in (200, 201) else None
            require(len(raw) <= schema.LIMIT, "github_unavailable")
            link = response.getheader("Link", "")
            return Response(response.status, data, 'rel="next"' in link)
        except Exception:
            raise JournalError("github_unavailable") from None
        finally:
            connection.close()
