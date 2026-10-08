"""Stateful service fakes for recovery tests; enforce the wire write conditions."""

import io
from types import SimpleNamespace as Record

from deployment.github_transport import Response


class Missing(Exception):
    status = 404


class ConditionalConflict(Exception):
    status = 412


class GitHub:
    def __init__(self):
        self.records = []
        self.posts = 0

    def request(self, method, path, body=None):
        if path == "/repos/example/invoices":
            return Response(200, {"id": 12345}, False)
        if method == "GET":
            return Response(200, list(self.records), False)
        self.posts += 1
        self.records.append({**body, "id": 101, "original_environment": "demo"})
        return Response(201, {}, False)


class ObjectStorage:
    def __init__(self):
        self.bucket = None
        self.body = None
        self.etag = "0"
        self.puts = 0
        self.lose_next_response = False

    def get_namespace(self, **kwargs):
        return Record(data="examplenamespace")

    def get_bucket(self, namespace, name):
        if self.bucket is None:
            raise Missing()
        assert (namespace, name) == (self.bucket.namespace, self.bucket.name)
        return Record(data=self.bucket)

    def create_bucket(self, namespace, details):
        self.bucket = Record(
            **{
                field: getattr(details, field)
                for field in (
                    "name",
                    "compartment_id",
                    "metadata",
                    "public_access_type",
                    "storage_tier",
                    "bucket_scope",
                    "versioning",
                    "auto_tiering",
                )
            },
            namespace=namespace,
            id="ocid1.bucket.oc1.uk-london-1.examplebucket",
            is_read_only=False,
            replication_enabled=False,
            object_lifecycle_policy_etag=None,
            kms_key_id=None,
        )

    def get_object(self, namespace, bucket, name):
        if self.body is None:
            raise Missing()
        stream = io.BytesIO(self.body)
        return Record(data=Record(raw=stream, close=stream.close), headers={"etag": self.etag})

    def put_object(self, namespace, bucket, name, body, **kwargs):
        self.puts += 1
        if kwargs.get("if_none_match") == "*":
            if self.body is not None:
                raise ConditionalConflict()
        elif kwargs.get("if_match") != self.etag:
            raise ConditionalConflict()
        self.body = body
        self.etag = str(int(self.etag) + 1)
        if self.lose_next_response:
            self.lose_next_response = False
            raise TimeoutError()
        return Record(headers={"etag": self.etag})
