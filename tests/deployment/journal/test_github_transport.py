import io

import pytest

from deployment.github_transport import GitHubTransport
from deployment.journal_errors import JournalError


class Connection:
    def __init__(self, status=200, body=b'{"id":12345}'):
        self.status, self.body = status, body
        self.calls = []
        self.closed = False

    def request(self, *args, **kwargs):
        self.calls.append((args, kwargs))

    def getresponse(self):
        result = io.BytesIO(self.body)
        result.status = self.status
        result.getheader = lambda name, default="": default
        return result

    def close(self):
        self.closed = True


def test_fixed_https_origin_token_header_and_bounded_response(monkeypatch):
    connection = Connection()
    constructors = []

    def connect(host, **kwargs):
        constructors.append((host, kwargs))
        return connection

    monkeypatch.setattr("deployment.github_transport.HTTPSConnection", connect)
    result = GitHubTransport("synthetic-github-token").request("GET", "/repos/example/invoices")
    assert result.data == {"id": 12345}
    assert constructors == [("api.github.com", {"timeout": 8})]
    args, kwargs = connection.calls[0]
    assert args == ("GET", "/repos/example/invoices")
    assert kwargs["headers"]["Authorization"] == "Bearer synthetic-github-token"
    assert connection.closed


@pytest.mark.parametrize("body", [b"sensitive-invalid", b" " * 65_537, b'{"id":1,"id":2}'])
def test_bad_response_is_bounded_and_not_echoed(monkeypatch, body):
    connection = Connection(body=body)
    monkeypatch.setattr("deployment.github_transport.HTTPSConnection", lambda *a, **k: connection)
    with pytest.raises(JournalError) as failure:
        GitHubTransport("synthetic-token").request("GET", "/repos/example/invoices")
    assert "sensitive" not in str(failure.value)
    assert connection.closed


def test_redirect_is_never_followed(monkeypatch):
    connection = Connection(status=302)
    monkeypatch.setattr("deployment.github_transport.HTTPSConnection", lambda *a, **k: connection)
    with pytest.raises(JournalError):
        GitHubTransport("synthetic-token").request("GET", "/repos/example/invoices")
    assert len(connection.calls) == 1
