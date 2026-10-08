from urllib.parse import urlencode

from django.urls import reverse


def evidence_links(revision, evidence):
    links = []
    for item in evidence:
        source = item["source"]
        if source not in {"normalized_invoice.json", "purchasing.json"}:
            continue
        url = reverse("record", args=[revision.case_id, revision.number, source])
        links.append(
            {
                "label": f"{source} v{item['version']} {item['locator'] or '/'}",
                "url": url + "?" + urlencode({"pointer": item["locator"]}),
            }
        )
    return links


def findings_for(revision):
    return [
        {
            **finding,
            "title": finding["code"].replace("_", " ").capitalize(),
            "links": evidence_links(revision, finding["evidence"]),
        }
        for finding in revision.result["findings"]
    ]
