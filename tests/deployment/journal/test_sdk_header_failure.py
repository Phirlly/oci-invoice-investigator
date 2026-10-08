import io
import json
from types import SimpleNamespace as Record

from deployment.configuration import parse_configuration
from deployment.credentials import load_signing_credentials
from deployment.journal_process import run_journal_command
from deployment.journal_request import Command, Context
from deployment.journal_store import JournalStore
from deployment.oci_storage_client import build_storage_client


class Stream(io.BytesIO):
    def release_conn(self):
        pass


def test_malformed_put_response_is_sent_once_then_reconciled(
    credential_environment,
    journal,
    anchor,
    monkeypatch,
):
    config = parse_configuration(credential_environment["DEPLOYMENT_CONFIG"])
    credentials = load_signing_credentials(credential_environment, config.fingerprint)
    environment = {}

    def child(*args, **kwargs):
        environment.update(kwargs["env"])
        return Record(
            returncode=0,
            stdout=json.dumps({"status": "JOURNAL_STATUS", "revision": 0, "operation": None}),
        )

    with monkeypatch.context() as process_patch:
        process_patch.setattr("deployment.journal_process.subprocess.run", child)
        run_journal_command(
            config,
            credentials,
            "synthetic-token",
            Context("example/invoices", 12345, "a" * 40),
            Command("status"),
        )
    monkeypatch.delenv("OCI_HEADER_PARSING_ERROR_MAX_RETRIES", raising=False)
    for key, value in environment.items():
        monkeypatch.setenv(key, value)
    import oci
    from oci.base_client import HeaderParsingError

    client = build_storage_client(config, credentials, "uk-london-1")
    calls = []

    def send(request, **kwargs):
        calls.append(request.method)
        if request.method == "PUT":
            # The service may already have accepted the conditional write.
            raise HeaderParsingError(defects=[], unparsed_data="sensitive")
        response = oci._vendor.requests.Response()
        response.status_code = 200
        response.headers["etag"] = "observed-etag"
        response.headers["content-type"] = "application/json"
        response.raw = Stream(journal.to_bytes())
        return response

    # SDK session copies preserve the class, not monkeypatched instance attributes.
    monkeypatch.setattr(
        type(client.base_client.session),
        "send",
        lambda self, request, **kwargs: send(request, **kwargs),
    )
    storage = JournalStore(
        client, anchor, journal.namespace, journal.bucket_ocid, journal.compartment_ocid
    )
    assert storage.initialize(journal).journal == journal
    assert calls == ["PUT", "GET"]
