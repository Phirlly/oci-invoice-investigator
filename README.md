# OCI Invoice Exception Investigator

A portable OCI demo for FDEs and customers to investigate invoice discrepancies,
inspect cited evidence and approve an internal follow-up task.

**Selected stack:** Django, PostgreSQL, OCI Document Understanding and
OpenAI Agents SDK for Python.

**Working locally:** invoice comparison, two synthetic cases, sign-in, evidence
viewing and persistent, duplicate-safe approved tasks.
**Not implemented:** invoice uploads, extraction, agent execution and cloud deployment.

## Try the offline sample

Requires Python 3.12 and uv. No OCI or OpenAI credentials are needed.
From the repository root:

```sh
uv sync --locked --python 3.12
uv run --locked invoice-investigator \
  --invoice examples/invoices/case-002/normalized_invoice.json \
  --evidence examples/invoices/case-002
```

Expected result: `needs_review`. The approved price is USD12.00 per unit;
receipts support 80 of 100 invoiced units, leaving 20 without receiving evidence.
Use `case-001` in both paths for the matched control.

The command compares hand-normalized synthetic JSON against the supplied
purchasing records; it does not extract fields from PDFs or create tasks.

## Check the local browser workflow

After the setup above, with a running Docker-compatible Linux container engine:

```sh
PLAYWRIGHT_BROWSERS_PATH=.cache/ms-playwright uv run --locked playwright install chromium
uv run --locked python tools/run_web_checks.py
```

This runs isolated PostgreSQL/Chromium tests for sign-in, evidence and approval,
then removes the test database. It does not leave a demo server running.

## Planned deployment and demo

**Configure once → deploy → open → verify/reset/reuse → remove.**

1. Configure one GitHub environment with central settings and scoped OCI/OpenAI
   credentials and presenter password.
2. Run one GitHub Actions workflow. It provisions through OCI Resource Manager,
   enrolls secrets, installs the application/database and loads synthetic records.
3. Open the returned HTTPS URL, sign in, select a sample or upload a supported
   synthetic PDF, inspect findings and approve a follow-up.
4. Verify before a meeting, reset samples while preserving accounts, or remove
   the deployment through the same workflow.

Routine use requires GitHub Actions and the demo page, with no SSH or manual host
configuration. **Ready** requires real extraction, agent execution and the complete
authenticated browser journey to pass. The result includes URL, username, version
and verification status; passwords stay out of output.

This deployment workflow is not available yet. The existing
[GitHub workflow](.github/workflows/validation.yml) runs code validation only.

## Scope

Synthetic invoices and supplied PO, amendment and receipt records; one supplier/PO,
USD and whole-unit quantities. No tax, freight, discounts, credits, ERP integration,
payments or external message delivery. The planned cloud demo sends selected
evidence to OpenAI and targets non-production OCI OC1 environments.

## License

[MIT](LICENSE) for original code; bundled assets retain their
[third-party licenses](THIRD_PARTY_NOTICES.md).
