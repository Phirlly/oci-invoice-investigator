# OCI Invoice Exception Investigator

Build a portable demonstration that FDEs and customers can deploy on OCI to
investigate invoices, inspect cited evidence and approve an internal follow-up
task. The selected agent runtime is **OpenAI Agents SDK for Python**.

**Implemented locally:** invoice comparison, two synthetic cases, a Django
reviewer interface, sign-in, protected PDF/record evidence, persistent case
revisions and duplicate-safe approved follow-up tasks in PostgreSQL.

**Still unimplemented:** uploads, OCI extraction, the agent and GitHub deployment.
This is not yet a deployable cloud demo.

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

## Intended GitHub deployment

The planned experience is **configure once → deploy → open the demo →
verify/reset/reuse → remove**. Deployment automation is not implemented yet;
the existing [GitHub workflow](.github/workflows/validation.yml) validates code.

An administrator will configure one GitHub environment with a central non-secret
`DEPLOYMENT_CONFIG` JSON value and scoped secrets for OCI signing, OpenAI access
and the chosen presenter password. It requires an authorized OCI deployment
identity and a repository with supported Actions/environment controls. The release
will include the exact setup and permission requirements. Authorized FDEs can reuse
a configured team repository; they also need authorized application sign-in access.

| Operation | Intended result |
| --- | --- |
| Deploy | Provision one OCI Resource Manager workload stack, enroll secrets in Vault, install the application/database, create presenter access and load synthetic records |
| Open demo | Receive the HTTPS URL, username, deployed version and verification status; passwords stay out of output |
| Verify | Run real login, extraction, agent investigation, evidence viewing and approved-task checks before a meeting |
| Reset demo | Restore selected synthetic cases while preserving accounts |
| Remove | Remove owned resources through OCI APIs even when the VM is unavailable; report anything awaiting scheduled deletion |

The same workflow will provide Status, Resume, Backup, Restore, Upgrade and
Recover access. Interrupted operations must resume from durable OCI state.
Credential recovery/restore uses a replacement password supplied through the
existing protected GitHub secret; ordinary deploy, verify and reset do not require
secret edits. Pending service deletion remains visible until confirmed complete.

Configuration is entered once; automation generates Terraform inputs and manages
the web interface, background worker, PostgreSQL and service connections together.
Secret values stay out of Terraform state. Routine use requires GitHub Actions and
the demo page, without Cloud Shell, SSH or manual host configuration. The initial
scope is a non-production OCI OC1 demo with generated HTTPS access and no customer
DNS setup. Supported regions, permissions, capacity and installation still need proof.

The Django workbench uses Bootstrap and PDF.js to show the invoice beside fields,
evidence and findings. Users will select samples or upload a supported invoice,
review cited findings and approve an exact follow-up proposal. Uploads/extraction
are not implemented; PDF is the current contract and JPEG/PNG support needs its
own validation and preview tests.

OCI will host the application and private evidence; selected evidence goes to
OpenAI through one Python Agents SDK agent. Application code enforces calculations,
purchasing authority, access and human approval. Purchasing records are the shipped
synthetic registers; an unknown PO yields missing evidence. The approved action
creates an internal demo task, with no payment or external message delivery.

**READY requires the complete real service and authenticated browser journey to
pass**, followed by cleanup of isolated acceptance data. The presenter account and
samples must work when the URL is returned. A successful infrastructure job alone
does not establish readiness. No cloud release or deployment command is available yet.

## License

Original project files use the [MIT License](LICENSE). Bundled assets retain
their upstream terms; see [third-party notices](THIRD_PARTY_NOTICES.md).
Corresponding Liberation font source is included with the application.
