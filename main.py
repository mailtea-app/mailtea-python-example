"""Send email with Mailtea from plain Python.

Run it with `python main.py`. Each step below is a separate function so you can
copy just the one you need.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from mailtea import Mailtea, MailteaError

# A per-run id in the subject keeps repeated demo runs apart in the dashboard
# and in your inbox. Real sends do not need it.
RUN_ID = uuid.uuid4().hex[:8]


def load_dotenv(path: Path | None = None) -> None:
    """Load KEY=value lines from a local .env, if there is one.

    The Mailtea SDK has zero dependencies and this example keeps it that way,
    so there is no python-dotenv here. Existing environment variables win, so
    an exported value always beats the file.
    """
    env_file = path or Path(__file__).parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def build_client() -> Mailtea:
    """The client reads MAILTEA_API_KEY, and MAILTEA_API_BASE_URL if it is set.

    The base URL is an optional override. Unset, the SDK talks to
    https://api.mailtea.app.
    """
    return Mailtea(os.environ.get("MAILTEA_API_KEY"))


def support_address(sender: str) -> str:
    """`support@` on the From address's own domain.

    Reply-To is what makes a reply land somewhere other than the From address —
    a monitored inbox rather than a no-reply one. Pointing it back at the
    recipient, which an early draft easily does, mails their reply to
    themselves.
    """
    domain = sender.rsplit("@", 1)[-1].strip(">").strip()
    return "support@" + domain


def simple_send(mailtea: Mailtea, sender: str, recipient: str) -> str:
    """The smallest useful send."""
    sent = mailtea.emails.send(
        # `from` is a Python keyword, so the SDK spells the From address `from_`.
        from_=sender,
        to=recipient,
        subject=f"Hello from the Mailtea python example ({RUN_ID})",
        html="<p>Sent with Mailtea.</p>",
    )
    # Responses allow attribute and ["..."] access alike.
    print(f"sent          {sent.id}")
    return sent.id


def send_with_options(mailtea: Mailtea, sender: str, recipient: str) -> str:
    """A fuller send: a plain-text alternative, a reply-to, and tags.

    Sending `text` alongside `html` is worth the two extra lines — it is what
    plain-text clients and most spam filters read.
    """
    sent = mailtea.emails.send(
        from_=sender,
        to=recipient,
        subject=f"Your receipt ({RUN_ID})",
        text="Thanks for your order. Reply to this email if anything looks wrong.",
        html=(
            "<p>Thanks for your order.</p>"
            "<p>Reply to this email if anything looks wrong.</p>"
        ),
        reply_to=support_address(sender),
        # Tags are how you slice delivery analytics later.
        tags=[
            {"name": "category", "value": "receipt"},
            {"name": "example", "value": "python"},
        ],
    )
    print(f"sent          {sent.id}")
    return sent.id


def schedule_send(mailtea: Mailtea, sender: str, recipient: str) -> str:
    """Schedule a send for later. `scheduled_at` is ISO 8601, in UTC."""
    when = datetime.now(timezone.utc) + timedelta(hours=1)
    sent = mailtea.emails.send(
        from_=sender,
        to=recipient,
        subject=f"Scheduled for later ({RUN_ID})",
        html="<p>This one was queued an hour ahead.</p>",
        scheduled_at=when.isoformat().replace("+00:00", "Z"),
    )
    print(f"scheduled     {sent.id} for {when:%Y-%m-%d %H:%M} UTC")
    return sent.id


def show_status(mailtea: Mailtea, email_id: str) -> None:
    """Retrieve one email and its delivery state."""
    email = mailtea.emails.get(email_id)
    print(f"status        {email.id} -> {email.status}")


def reschedule(mailtea: Mailtea, email_id: str) -> None:
    """Move a scheduled email. Only emails that have not sent yet can change."""
    when = datetime.now(timezone.utc) + timedelta(hours=3)
    mailtea.emails.reschedule(email_id, when.isoformat().replace("+00:00", "Z"))
    print(f"rescheduled   {email_id} for {when:%Y-%m-%d %H:%M} UTC")


def cancel(mailtea: Mailtea, email_id: str) -> None:
    """Cancel a scheduled email before it goes out."""
    mailtea.emails.cancel(email_id)
    print(f"cancelled     {email_id}")


def send_batch(mailtea: Mailtea, sender: str, recipient: str) -> list[str]:
    """Send up to 100 distinct emails in one request.

    Batch items each need their own `from`, and cannot carry attachments or a
    schedule.
    """
    result = mailtea.emails.batch(
        [
            {
                "from": sender,
                "to": recipient,
                "subject": f"Batch message {n} ({RUN_ID})",
                "html": f"<p>Message {n} of 2.</p>",
            }
            for n in (1, 2)
        ]
    )
    ids = [email["id"] for email in result["data"]]
    print(f"batch sent    {', '.join(ids)}")
    return ids


def main() -> int:
    load_dotenv()

    sender = os.environ.get("MAILTEA_FROM", "Acme <hello@acme.com>")
    recipient = os.environ.get("MAILTEA_TO", "reader@yourdomain.com")

    try:
        mailtea = build_client()

        simple_send(mailtea, sender, recipient)
        send_with_options(mailtea, sender, recipient)

        scheduled_id = schedule_send(mailtea, sender, recipient)
        show_status(mailtea, scheduled_id)
        reschedule(mailtea, scheduled_id)
        cancel(mailtea, scheduled_id)

        send_batch(mailtea, sender, recipient)
    except MailteaError as error:
        # What you want in production: the API's own message, plus the request
        # id to quote if you need support to look the send up.
        print(f"Mailtea error ({error.status}): {error.message}")
        if error.request_id:
            print(f"request id: {error.request_id}")
        return 1
    except OSError as error:
        # The API was never reached at all — DNS, TLS, a refused connection, a
        # timeout. The SDK's standard-library transport lets these through
        # unchanged, and they are what a send hits far more often than a 4xx.
        print(f"Could not reach Mailtea: {error}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
