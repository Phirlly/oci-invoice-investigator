"""One public deployment locator; ambiguous creation never permits another POST."""

from dataclasses import asdict

from . import journal_schema as schema
from .journal_errors import JournalError, require
from .journal_locator import Anchor, Locator
from .journal_request import repository_path

TASK = "invoice-control-v1"
PAGE_SIZE = 10
PAGE_LIMIT = 20


class GitHubAnchor:
    def __init__(self, transport, repository, repository_id):
        repository_path(repository)
        schema.integer(repository_id, 1)
        self.transport = transport
        self.path = "/repos/" + repository
        self.repository_id = repository_id

    def find(self):
        response = self.transport.request("GET", self.path)
        require(response.status == 200 and isinstance(response.data, dict), "github_unavailable")
        server_id = response.data.get("id")
        require(type(server_id) is int and server_id == self.repository_id, "identity_mismatch")
        found = []
        for page in range(1, PAGE_LIMIT + 1):
            path = (
                self.path + f"/deployments?task={TASK}&environment=demo"
                f"&per_page={PAGE_SIZE}&page={page}"
            )
            response = self.transport.request("GET", path)
            require(
                response.status == 200 and isinstance(response.data, list), "github_unavailable"
            )
            require(len(response.data) <= PAGE_SIZE, "github_unavailable")
            for record in response.data:
                require(isinstance(record, dict), "anchor_conflict")
                require(
                    record.get("task") == TASK
                    and record.get("environment") == "demo"
                    and record.get("original_environment") == "demo",
                    "anchor_conflict",
                )
                locator = Locator.parse(schema.encode(record.get("payload")))
                require(locator.repository_id == self.repository_id, "anchor_conflict")
                found.append(Anchor(record.get("id"), locator))
                require(len(found) == 1, "anchor_conflict")
            if len(response.data) < PAGE_SIZE:
                require(not response.has_next, "github_unavailable")
                return found[0] if found else None
        raise JournalError("github_unavailable")

    def initialize(self, locator, release):
        schema.pattern(release, r"[a-f0-9]{40}")
        require(locator.repository_id == self.repository_id, "identity_mismatch")
        existing = self.find()
        if existing is not None:
            require(existing.locator == locator, "anchor_conflict")
            return existing
        try:
            response = self.transport.request(
                "POST",
                self.path + "/deployments",
                {
                    "ref": release,
                    "task": TASK,
                    "environment": "demo",
                    "auto_merge": False,
                    "payload": asdict(locator),
                    "description": "Invoice demo control locator",
                },
            )
        except JournalError:
            response = None
        if response is not None:
            require(response.status == 201 or response.status >= 500, "github_unavailable")
        try:
            observed = self.find()
        except JournalError as error:
            if error.code == "anchor_conflict":
                raise
            raise JournalError("outcome_unknown") from None
        require(observed is not None, "outcome_unknown")
        require(observed.locator == locator, "anchor_conflict")
        return observed
