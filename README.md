# OCI Invoice Exception Investigator

Build a portable demonstration that FDEs and customers can deploy on OCI to
investigate invoices, inspect cited evidence and approve an internal follow-up
task. The selected agent runtime is **OpenAI Agents SDK for Python**.

**Implemented locally:** invoice comparison, two synthetic cases, a Django
reviewer interface, sign-in, protected PDF/record evidence, persistent case
revisions and duplicate-safe approved follow-up tasks in PostgreSQL.
**Still unimplemented:** OCI extraction, the agent and guided Resource Manager
deployment. This is not yet a deployable cloud demo.

## Run the offline sample

Requires Python 3.12 and uv (validated with Python 3.12.12 and uv 0.12.19).
From the repository root:

```sh
uv sync --locked --python 3.12
uv run --locked invoice-investigator \
  --invoice examples/invoices/case-002/normalized_invoice.json \
  --evidence examples/invoices/case-002
```

The result is `needs_review`: the approved amendment supports USD12.00 per unit,
while receipts support 80 of the 100 invoiced units. Exactly 20 units lack
receiving evidence; this does not establish physical nondelivery.
For the matched control, substitute `case-001` in both paths.

Results include the case/version, invoice PDF digest, purchasing version,
evidence cutoff, per-line facts, findings, source locations and proposed next
steps. The command prints JSON without network calls or file changes.
A completed comparison exits 0, including `needs_review` and `incomplete`;
invalid or unsupported input exits 2 with an `Input error:` message.

The normalized JSON is hand-authored synthetic input. This command does not
extract PDF fields, run an agent, verify real approvals or create tasks.
Source hashes establish file integrity, not extraction accuracy or authenticity.

## Included data

All organizations and records are fictional. No external dataset, API key or
customer data is required for the offline run.

| Bundle | Source documents and records | Demonstration |
| --- | --- | --- |
| `examples/invoices/case-001` | Invoice PDF, PO/receiving register, hash manifest | 100 units at USD10.00; 100 received |
| `examples/invoices/case-002` | Invoice and amendment PDFs, PO/amendment/receiving register, hash manifest | Approved USD12.00 price; 80 received |

Expected answers remain separately under `tests/fixtures/invoices`.
They are not purchasing evidence or part of the runtime wheel. The source
distribution includes samples, test fixtures and development tools.

Each bundle's `sample-input.json` identifies the hand-normalized input and its
digest. The web application loads these shipped inputs, never expected answers.

Each case has an isolated register. Schema version 1 accepts one supplier and
PO, USD, EA, positive whole quantities up to 1,000,000, amounts below 1,000,000,000
as two-decimal strings, and at most 1,000 records per collection. JSON files are
limited to 1 MiB; source PDFs to 10 MiB. No tax, freight, discounts, credits or
cross-invoice receipt allocation is supported.

An incomplete amendment or receiving lookup cannot produce a final expected
price or receiving shortfall. Conflicting evidence remains explicit. Unknown
fields, unsupported formats and mismatched case snapshots are rejected.

To regenerate the included PDFs and manifests from the reviewed fixtures:

```sh
uv run --locked python tools/generate_sample_documents.py
```

Regeneration is optional.

## Verify the local reviewer workflow

Local verification needs Python 3.12, uv and a running Docker-compatible Linux
container engine. No OCI or OpenAI credential is needed. From this checkout:

```sh
uv sync --locked --python 3.12
PLAYWRIGHT_BROWSERS_PATH=.cache/ms-playwright uv run --locked playwright install chromium
uv run --locked python tools/run_web_checks.py
```

The check starts a digest-pinned PostgreSQL 17.11 container on a random loopback
port, applies migrations, loads synthetic cases and tests sign-in, evidence
viewing and explicit task approval in Chromium. It checks competing approvals,
revision changes and access revocation, then removes its test database/container.
The selected image supports Linux amd64/arm64; this run has been verified with
the local ARM64 Podman backend. Browser binaries are cached locally.

The interface accurately labels its supplied fields and deterministic findings.
Invoice uploads, extraction and agent execution are not simulated. This command
verifies the local implementation; it is not the future customer deployment entry.

## Intended cloud deployment

The frontend uses Django, Bootstrap and PDF.js. It shows the invoice beside its
evidence and findings, then lets a reviewer approve an exact follow-up proposal
and inspect the saved task. Frontend assets ship with the application.
The frontend, background worker and PostgreSQL database will install together.

One guided OCI Cloud Shell installer will collect the target compartment/region,
your chosen sign-in and OpenAI API key. It will enroll secrets automatically,
run one Resource Manager workload stack, initialize data and load sample cases.
Non-secret settings will have one centralized `deployment.tfvars`; credentials
will never go in that file or Terraform state.

The non-production OCI OC1 design provides an API Gateway HTTPS URL without
customer DNS. Before reporting **READY**, installation must pass real OCI Document
Understanding, OpenAI agent/tool execution and an authenticated browser check of
evidence viewing and duplicate-safe task approval. Then you sign in and demo;
there is no separate database, secret setup or host configuration step.

An OCI account/compartment with the documented deployment permissions and OpenAI
API access remain prerequisites. Exact release versions, IAM, regional artifact
access, service capacity and the complete installation path still require testing.
These cloud installation commitments have not yet been implemented.

OCI will host the application and private case/document storage. Selected
evidence will be sent to OpenAI for inference. Application code will enforce
calculations, purchasing authority, access and human approval. The only approved
business action will create an internal demo task; no payment, invoice approval,
external email or ticket will be sent.

The same installer will provide status, resume, reset, backup/restore, upgrade
and cleanup. No cloud release or deployment command is available yet.

## License

Original project files use the [MIT License](LICENSE). Bundled assets retain
their upstream terms; see [third-party notices](THIRD_PARTY_NOTICES.md).
Corresponding Liberation font source is included with the application.
