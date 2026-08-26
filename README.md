# Mailtea + Python Example

This example shows how to use [Mailtea](https://mailtea.app) with Python to send
transactional email from a plain script — one-off sends, scheduled sends you can
still move or cancel, and batches.

It is a single `main.py` with no framework and no runtime dependencies beyond the
Mailtea SDK, which itself has none.

## Prerequisites

To get the most out of this guide, you'll need to:

- [Create an API key](https://studio.mailtea.app/api-keys)
- [Verify your domain](https://docs.mailtea.app/docs/documentation/domains)

## Instructions

1. Install dependencies:
   ```bash
   uv sync
   ```
   Or with pip:
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and add your API key:
   ```bash
   cp .env.example .env
   ```
   Set `MAILTEA_FROM` to an address on your verified domain, and `MAILTEA_TO` to
   an inbox you can open.
3. Run it:
   ```bash
   uv run main.py
   ```
   Or, in the pip virtualenv above:
   ```bash
   python main.py
   ```

## What this example covers

- A minimal send — note `from_=`, since `from` is a Python keyword
- A fuller send with a plain-text alternative, `reply_to`, and tags
- Scheduling a send with `scheduled_at`
- Reading an email's delivery status back with `emails.get`
- Rescheduling and cancelling an email that hasn't gone out yet
- Sending a batch of distinct emails in one request
- Catching `MailteaError` and surfacing the API's message and request id,
  and reporting an unreachable API instead of printing a traceback

## Tests

```bash
uv run --extra test pytest
```

Or with pip:

```bash
pip install pytest && pytest
```

The tests run against a bundled mock Mailtea server, so they need no API key
and make no network calls.

## Learn more

- [Documentation](https://docs.mailtea.app)
- [API reference](https://docs.mailtea.app/docs/api-reference)
- [Node.js SDK](https://github.com/mailtea-app/mailtea-node) ·
  [Python SDK](https://github.com/mailtea-app/mailtea-python) ·
  [MCP server](https://github.com/mailtea-app/mailtea-mcp)
