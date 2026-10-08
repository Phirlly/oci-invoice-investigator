from copy import deepcopy

import pytest

from deployment.github_anchor import GitHubAnchor
from deployment.github_transport import Response
from deployment.journal_errors import JournalError


class API:
    def __init__(self, pages):
        self.pages = iter(pages)
        self.calls = []

    def request(self, method, path, body=None):
        self.calls.append((method, path, body))
        if path == "/repos/example/invoices":
            return Response(200, {"id": 12345}, False)
        value = next(self.pages)
        if isinstance(value, Exception):
            raise value
        return value


def adapter(api):
    return GitHubAnchor(api, "example/invoices", 12345)


def test_discovery_verifies_server_identity_and_returns_anchor(github_record, anchor):
    api = API([Response(200, [github_record], False)])
    assert adapter(api).find() == anchor
    assert api.calls[0][1] == "/repos/example/invoices"
    assert "task=invoice-control-v1&environment=demo" in api.calls[1][1]


@pytest.mark.parametrize("records", [[], [{"id": True}], [{"payload": "secret-value"}]])
def test_empty_is_distinct_from_malformed(records):
    api = API([Response(200, records, False)])
    if not records:
        assert adapter(api).find() is None
    else:
        with pytest.raises(JournalError):
            adapter(api).find()


def test_multiple_or_duplicate_anchor_records_fail_closed(github_record):
    for second_id in (101, 102):
        other = {**deepcopy(github_record), "id": second_id}
        with pytest.raises(JournalError, match="anchor_conflict"):
            adapter(API([Response(200, [github_record, other], False)])).find()


@pytest.mark.parametrize("status", [201, 500, None])
def test_create_always_rediscovers_and_never_reposts(status, locator, github_record, anchor):
    response = Response(status, {}, False) if status else JournalError("github_unavailable")
    api = API([Response(200, [], False), response, Response(200, [github_record], False)])
    assert adapter(api).initialize(locator, "a" * 40) == anchor
    post = [call for call in api.calls if call[0] == "POST"]
    assert len(post) == 1
    assert post[0][2]["auto_merge"] is False
    assert post[0][2]["ref"] == "a" * 40
    assert "ocid1." not in str(post[0][2])


def test_successful_create_followed_by_competing_anchor_fails(locator, github_record):
    other = {**deepcopy(github_record), "id": 102}
    api = API(
        [
            Response(200, [], False),
            Response(201, {}, False),
            Response(200, [github_record, other], False),
        ]
    )
    with pytest.raises(JournalError, match="anchor_conflict"):
        adapter(api).initialize(locator, "a" * 40)


@pytest.mark.parametrize("response", [Response(403, {}, False), Response(202, {}, False)])
def test_denied_or_merge_response_is_not_creation(response, locator):
    api = API([Response(200, [], False), response])
    with pytest.raises(JournalError, match="github_unavailable"):
        adapter(api).initialize(locator, "a" * 40)


def test_incomplete_lookup_cannot_authorize_post(locator):
    api = API([Response(200, [], True)])
    with pytest.raises(JournalError):
        adapter(api).initialize(locator, "a" * 40)
    assert all(call[0] == "GET" for call in api.calls)


@pytest.mark.parametrize("after", [Response(200, [], False), Response(403, {}, False)])
def test_unobservable_post_outcome_never_reposts(locator, after):
    api = API([Response(200, [], False), JournalError("github_unavailable"), after])
    with pytest.raises(JournalError, match="outcome_unknown"):
        adapter(api).initialize(locator, "a" * 40)
    assert len([call for call in api.calls if call[0] == "POST"]) == 1


def test_existing_anchor_is_reused_without_post(locator, github_record, anchor):
    api = API([Response(200, [github_record], False)])
    assert adapter(api).initialize(locator, "a" * 40) == anchor
    assert all(call[0] == "GET" for call in api.calls)
