"""Private worker entrypoint; never invoke outside the bounded parent process."""

import json
import logging
import sys

from . import journal_schema as schema
from .configuration import parse_configuration
from .credentials import load_signing_credentials
from .github_anchor import GitHubAnchor
from .github_transport import GitHubTransport
from .journal_controller import JournalController
from .journal_errors import JournalError
from .journal_request import Command, Context
from .oci_client import build_client
from .oci_read_checks import check_read_access
from .oci_storage_client import build_storage_client


def journal_payload(raw):
    try:
        data = schema.decode(raw)
        schema.fields(
            data,
            {"configuration", "private_key", "passphrase", "github_token", "context", "command"},
        )
        config = parse_configuration(schema.encode(data["configuration"]))
        credentials = load_signing_credentials(
            {"OCI_API_PRIVATE_KEY": data["private_key"], "OCI_KEY_PASSPHRASE": data["passphrase"]},
            config.fingerprint,
        )
        context, command = Context.parse(data["context"]), Command.parse(data["command"])
        anchors = GitHubAnchor(
            GitHubTransport(data["github_token"]), context.repository, context.repository_id
        )
        controller = JournalController(
            config,
            context,
            anchors,
            lambda region: build_storage_client(config, credentials, region),
            lambda: check_read_access(
                config, lambda region: build_client(config, credentials, region)
            ),
        )
        return controller.execute(command)
    except JournalError as error:
        return {"status": "FAILED", "code": error.code}
    except Exception:
        return {"status": "FAILED", "code": "outcome_unknown"}


def main():
    logging.disable(logging.CRITICAL)
    result = journal_payload(sys.stdin.read(schema.LIMIT + 1))
    print(json.dumps(result))
    return 1 if result["status"] == "FAILED" else 0


if __name__ == "__main__":
    sys.exit(main())
