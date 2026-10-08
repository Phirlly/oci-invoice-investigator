import hashlib
import json

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from invoice_investigator.case_storage.models import EvidenceDocument

from .access import authorized_revision


@login_required
@require_GET
def document(request, case_id, number, name):
    revision = authorized_revision(request.user, case_id, number)
    if name not in {"invoice.pdf", "amendment.pdf"}:
        raise Http404("Document is unavailable.")
    document = get_object_or_404(EvidenceDocument, revision=revision, name=name)
    content = bytes(document.content)
    if hashlib.sha256(content).hexdigest() != document.sha256:
        return HttpResponse(
            "Evidence integrity check failed.", status=503, content_type="text/plain"
        )
    response = HttpResponse(content, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{name}"'
    response["Cache-Control"] = "private, no-store"
    response["Content-Security-Policy"] = "sandbox; default-src 'none'"
    return response


def pointed_record(value, pointer):
    if len(pointer) > 256 or pointer and not pointer.startswith("/"):
        raise Http404("Evidence location is unavailable.")
    try:
        for encoded in pointer.split("/")[1:]:
            key = encoded.replace("~1", "/").replace("~0", "~")
            if isinstance(value, list):
                if not key.isdecimal():
                    raise ValueError
                value = value[int(key)]
            elif isinstance(value, dict):
                value = value[key]
            else:
                raise ValueError
    except (ValueError, IndexError, KeyError) as error:
        raise Http404("Evidence location is unavailable.") from error
    return value


@login_required
@never_cache
@require_GET
def record(request, case_id, number, name):
    revision = authorized_revision(request.user, case_id, number)
    sources = {"normalized_invoice.json": revision.invoice, "purchasing.json": revision.register}
    if name not in sources:
        raise Http404("Source is unavailable.")
    pointer = request.GET.get("pointer", "")
    value = pointed_record(sources[name], pointer)
    return render(
        request,
        "review/record.html",
        {
            "revision": revision,
            "name": name,
            "pointer": pointer or "/",
            "record": json.dumps(value, indent=2),
        },
    )
