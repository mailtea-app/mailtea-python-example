"""Tests for the example, run against the bundled mock Mailtea API.

No API key, no network. Each test points the SDK at the mock through
MAILTEA_API_BASE_URL, which is exactly how you point it at a local dev or
self-hosted Mailtea.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main  # noqa: E402
from mock_mailtea import EMAIL_ID, mock_mailtea  # noqa: E402

SENDER = "Acme <hello@acme.com>"
RECIPIENT = "reader@acme.dev"


@pytest.fixture
def server(monkeypatch):
    """A running mock API, with the environment pointed at it."""
    # Neutralised so a developer's own .env cannot leak into a test run.
    monkeypatch.setattr(main, "load_dotenv", lambda *args, **kwargs: None)
    with mock_mailtea() as mock:
        monkeypatch.setenv("MAILTEA_API_KEY", "mt_pat_test")
        monkeypatch.setenv("MAILTEA_API_BASE_URL", mock.url)
        monkeypatch.setenv("MAILTEA_FROM", SENDER)
        monkeypatch.setenv("MAILTEA_TO", RECIPIENT)
        yield mock


def test_simple_send_posts_to_the_configured_base_url(server, capsys):
    email_id = main.simple_send(main.build_client(), SENDER, RECIPIENT)

    request = server.last
    assert request["method"] == "POST"
    assert request["path"] == "/v1/emails"
    assert request["authorization"] == "Bearer mt_pat_test"
    assert request["body"]["from"] == SENDER
    assert request["body"]["to"] == RECIPIENT
    assert "python example" in request["body"]["subject"]
    assert request["body"]["html"] == "<p>Sent with Mailtea.</p>"

    # The id the API returned has to reach both the caller and the console.
    assert email_id == EMAIL_ID
    assert EMAIL_ID in capsys.readouterr().out


def test_send_with_options_carries_text_reply_to_and_tags(server):
    main.send_with_options(main.build_client(), SENDER, RECIPIENT)

    body = server.last["body"]
    assert body["text"].startswith("Thanks for your order.")
    assert body["html"].startswith("<p>Thanks for your order.")
    # Reply-To has to reach a monitored inbox, not the person who got the mail.
    assert body["reply_to"] == "support@acme.com"
    assert body["reply_to"] != RECIPIENT
    assert {"name": "category", "value": "receipt"} in body["tags"]


def test_scheduled_send_sends_an_iso_8601_scheduled_at(server):
    main.schedule_send(main.build_client(), SENDER, RECIPIENT)

    body = server.last["body"]
    assert body["subject"].startswith("Scheduled for later")
    assert body["scheduled_at"].endswith("Z")


def test_get_reschedule_and_cancel_hit_the_right_routes(server, capsys):
    mailtea = main.build_client()

    main.show_status(mailtea, "txemail_abc")
    assert server.last["method"] == "GET"
    assert server.last["path"] == "/v1/emails/txemail_abc"
    # `status` is the SDK's friendly alias of the wire field `last_event`.
    assert "delivered" in capsys.readouterr().out

    main.reschedule(mailtea, "txemail_abc")
    assert server.last["method"] == "PATCH"
    assert server.last["path"] == "/v1/emails/txemail_abc"
    assert server.last["body"]["scheduled_at"].endswith("Z")

    main.cancel(mailtea, "txemail_abc")
    assert server.last["method"] == "POST"
    assert server.last["path"] == "/v1/emails/txemail_abc/cancel"


def test_batch_send_posts_a_list_of_emails(server):
    ids = main.send_batch(main.build_client(), SENDER, RECIPIENT)

    request = server.last
    assert request["path"] == "/v1/emails/batch"
    assert len(request["body"]) == 2
    # Every batch item carries its own From — the route has no shared one.
    assert all(item["from"] == SENDER for item in request["body"])
    assert ids == [f"txemail_{n:032d}" for n in (0, 1)]


def test_main_runs_every_step_in_order(server, capsys):
    assert main.main() == 0

    routes = [f"{r['method']} {r['path']}" for r in server.requests]
    assert routes == [
        "POST /v1/emails",
        "POST /v1/emails",
        "POST /v1/emails",
        f"GET /v1/emails/{EMAIL_ID}",
        f"PATCH /v1/emails/{EMAIL_ID}",
        f"POST /v1/emails/{EMAIL_ID}/cancel",
        "POST /v1/emails/batch",
    ]
    assert "cancelled" in capsys.readouterr().out


def test_a_failed_send_is_reported_not_raised(server, monkeypatch, capsys):
    # A base URL pointing at the wrong place is the everyday way sends fail.
    monkeypatch.setenv("MAILTEA_API_BASE_URL", server.url + "/wrong")

    assert main.main() == 1
    assert "Mailtea error (404): Not Found" in capsys.readouterr().out


def test_an_unreachable_api_is_reported_not_raised(server, monkeypatch, capsys):
    # Nothing is listening on port 1, so this fails at the socket rather than
    # with an HTTP status — the shape of every DNS, TLS, or timeout failure.
    # It reaches the caller as a plain OSError, not a MailteaError.
    monkeypatch.setenv("MAILTEA_API_BASE_URL", "http://127.0.0.1:1")

    assert main.main() == 1
    assert "Could not reach Mailtea" in capsys.readouterr().out


def test_a_missing_api_key_is_reported_not_raised(server, monkeypatch, capsys):
    monkeypatch.delenv("MAILTEA_API_KEY")

    assert main.main() == 1
    assert "Missing Mailtea API key" in capsys.readouterr().out


def test_load_dotenv_never_overrides_a_real_environment_variable(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# a comment\nMAILTEA_API_KEY=mt_pat_from_file\nMAILTEA_TO=file@acme.dev\n"
    )
    # A throwaway copy, so what the file loads cannot leak into other tests.
    environ = dict(os.environ, MAILTEA_API_KEY="mt_pat_exported")
    environ.pop("MAILTEA_TO", None)
    monkeypatch.setattr(os, "environ", environ)

    main.load_dotenv(env_file)

    assert environ["MAILTEA_API_KEY"] == "mt_pat_exported"
    assert environ["MAILTEA_TO"] == "file@acme.dev"
