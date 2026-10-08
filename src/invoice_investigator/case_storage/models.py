import uuid

from django.conf import settings
from django.db import models


class Installation(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    identity = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    enrollment_id = models.UUIDField(null=True)
    enrollment_digest = models.CharField(max_length=64, blank=True)
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(id=1), name="one_installation")]


class Case(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    title = models.CharField(max_length=160)
    current_revision = models.PositiveIntegerField(default=0)


class Membership(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    active = models.BooleanField(default=True)
    can_review = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["case", "user"], name="one_membership")]


class CaseRevision(models.Model):
    case = models.ForeignKey(Case, on_delete=models.PROTECT, related_name="revisions")
    number = models.PositiveIntegerField()
    content_digest = models.CharField(max_length=64)
    invoice = models.JSONField()
    register = models.JSONField()
    manifest = models.JSONField()
    result = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["case", "number"], name="one_case_revision"),
            models.CheckConstraint(condition=models.Q(number__gte=1), name="positive_revision"),
        ]


class EvidenceDocument(models.Model):
    revision = models.ForeignKey(CaseRevision, on_delete=models.PROTECT, related_name="documents")
    name = models.CharField(max_length=32)
    sha256 = models.CharField(max_length=64)
    content = models.BinaryField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["revision", "name"], name="one_document")]


class Proposal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    revision = models.ForeignKey(CaseRevision, on_delete=models.PROTECT, related_name="proposals")
    payload = models.JSONField()
    digest = models.CharField(max_length=64)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["revision", "digest"], name="one_proposal")]


class Approval(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proposal = models.OneToOneField(Proposal, on_delete=models.PROTECT)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    digest = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)


class FollowUpTask(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    approval = models.OneToOneField(Approval, on_delete=models.PROTECT, related_name="task")
    created_at = models.DateTimeField(auto_now_add=True)


class AuditEntry(models.Model):
    approval = models.OneToOneField(Approval, on_delete=models.PROTECT)
    event = models.CharField(max_length=32, default="follow_up_created")
    created_at = models.DateTimeField(auto_now_add=True)
