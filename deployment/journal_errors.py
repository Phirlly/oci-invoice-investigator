"""Closed diagnostics for the private deployment controller protocol."""

CODES = frozenset(
    {
        "journal_invalid",
        "identity_mismatch",
        "initial_target_changed",
        "anchor_conflict",
        "anchor_missing",
        "github_unavailable",
        "bucket_conflict",
        "storage_unavailable",
        "journal_missing",
        "journal_conflict",
        "operation_busy",
        "operation_conflict",
        "outcome_unknown",
        "controller_failed",
    }
)


class JournalError(ValueError):
    def __init__(self, code="journal_invalid"):
        self.code = code if code in CODES else "controller_failed"
        super().__init__(self.code)


def require(condition, code="journal_invalid"):
    if not condition:
        raise JournalError(code)
