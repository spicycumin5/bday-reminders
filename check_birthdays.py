"""Daily birthday check: emails you about upcoming birthdays (via Gmail).

Usage:
    python check_birthdays.py               # check today, send email if needed
    python check_birthdays.py --dry-run     # print instead of sending
    python check_birthdays.py --date 2026-03-07 --dry-run
    python check_birthdays.py --test        # send one test email

Environment:
    EMAIL_USER          Gmail address that sends the email (required unless --dry-run)
    EMAIL_APP_PASSWORD  Gmail App Password for that account (required unless --dry-run)
    EMAIL_TO            where to send reminders (defaults to EMAIL_USER)
    SMTP_HOST/SMTP_PORT default to smtp.gmail.com / 465
    TZ_NAME             IANA time zone for "today", e.g. America/Los_Angeles (default UTC)
"""

from __future__ import annotations

import argparse
import calendar
import csv
import os
import sys
import smtplib
from dataclasses import dataclass, field
from datetime import date, datetime
from email.message import EmailMessage
from pathlib import Path
from zoneinfo import ZoneInfo

DEFAULT_LEAD_DAYS = (7,)
CSV_PATH = Path(__file__).with_name("birthdays.csv")


@dataclass
class Friend:
    name: str
    month: int
    day: int
    year: int | None = None
    lead_days: tuple[int, ...] = field(default=DEFAULT_LEAD_DAYS)


def parse_birthday(text: str) -> tuple[int | None, int, int]:
    """Parse 'MM-DD' or 'YYYY-MM-DD' into (year, month, day)."""
    parts = text.strip().split("-")
    if len(parts) == 2:
        year, (month, day) = None, map(int, parts)
    elif len(parts) == 3:
        year, month, day = map(int, parts)
    else:
        raise ValueError(f"birthday '{text}' must be MM-DD or YYYY-MM-DD")
    # Validate against a leap year so 02-29 is allowed.
    date(year if year else 2000, month, day)
    return year, month, day


def parse_lead_days(text: str) -> tuple[int, ...]:
    text = (text or "").strip()
    if not text:
        return DEFAULT_LEAD_DAYS
    values = tuple(int(v) for v in text.replace(",", ";").split(";") if v.strip())
    if any(v < 0 for v in values):
        raise ValueError(f"remind_days_before '{text}' can't be negative")
    return values or DEFAULT_LEAD_DAYS


def load_friends(path: Path) -> tuple[list[Friend], list[str]]:
    """Return (friends, errors). Bad rows are skipped and reported."""
    friends: list[Friend] = []
    errors: list[str] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        lines = (line for line in f if line.strip() and not line.lstrip().startswith("#"))
        for n, row in enumerate(csv.DictReader(lines), start=1):
            name = (row.get("name") or "").strip()
            try:
                if not name:
                    raise ValueError("missing name")
                year, month, day = parse_birthday(row.get("birthday") or "")
                lead = parse_lead_days(row.get("remind_days_before") or "")
                friends.append(Friend(name, month, day, year, lead))
            except ValueError as e:
                errors.append(f"Friend #{n} ({name or 'no name'}): {e}")
    return friends, errors


def occurrence_in(year: int, month: int, day: int) -> date:
    """Birthday date in a given year; Feb 29 falls back to Feb 28 in non-leap years."""
    if month == 2 and day == 29 and not calendar.isleap(year):
        return date(year, 2, 28)
    return date(year, month, day)


def next_birthday(friend: Friend, today: date) -> date:
    d = occurrence_in(today.year, friend.month, friend.day)
    if d < today:
        d = occurrence_in(today.year + 1, friend.month, friend.day)
    return d


def reminders_for(friends: list[Friend], today: date) -> list[str]:
    messages: list[tuple[int, str]] = []
    for fr in friends:
        bday = next_birthday(fr, today)
        days = (bday - today).days
        if days != 0 and days not in fr.lead_days:
            continue
        age = bday.year - fr.year if fr.year else None
        if days == 0:
            msg = f"🎂 Today is {fr.name}'s birthday!"
            if age:
                msg = f"🎂 Today is {fr.name}'s birthday! They turn {age}."
        else:
            when = "tomorrow" if days == 1 else f"in {days} days"
            what = f"turns {age}" if age else "has a birthday"
            msg = f"{fr.name} {what} {when} ({bday:%a, %b} {bday.day})"
        messages.append((days, msg))
    return [m for _, m in sorted(messages, key=lambda x: x[0])]


def send_email(subject: str, body: str) -> None:
    user = os.environ.get("EMAIL_USER", "").strip()
    password = os.environ.get("EMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    if not user or not password:
        raise SystemExit("EMAIL_USER and EMAIL_APP_PASSWORD must be set to send email.")
    to = os.environ.get("EMAIL_TO", "").strip() or user
    host = os.environ.get("SMTP_HOST", "").strip() or "smtp.gmail.com"
    port = int(os.environ.get("SMTP_PORT", "").strip() or 465)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"Birthday Reminder <{user}>"
    msg["To"] = to
    msg.set_content(body)
    with smtplib.SMTP_SSL(host, port, timeout=30) as smtp:
        smtp.login(user, password)
        smtp.send_message(msg)


def subject_for(messages: list[str]) -> str:
    if len(messages) == 1:
        return messages[0]
    return f"🎂 {len(messages)} birthday reminders"


def today_in_tz() -> date:
    tz_name = os.environ.get("TZ_NAME", "").strip() or "UTC"
    return datetime.now(ZoneInfo(tz_name)).date()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true", help="print instead of sending")
    p.add_argument("--date", help="pretend today is YYYY-MM-DD")
    p.add_argument("--test", action="store_true", help="send a single test email")
    p.add_argument("--file", type=Path, default=CSV_PATH, help="path to birthdays.csv")
    args = p.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")  # emoji-safe output on Windows consoles

    if args.test:
        msg = "✅ Test from your birthday reminder. Emails are working!"
        if args.dry_run:
            print(f"(dry run) {msg}")
        else:
            send_email("Birthday reminder test", msg)
            print("Test email sent.")
        return 0

    today = date.fromisoformat(args.date) if args.date else today_in_tz()
    friends, errors = load_friends(args.file)
    messages = reminders_for(friends, today)

    print(f"Today: {today.isoformat()} - {len(friends)} friend(s) loaded")
    if messages:
        body = "\n".join(messages)
        print(body)
        if not args.dry_run:
            footer = "\n\nTo add or change friends, edit birthdays.csv in your bday-reminders repo."
            send_email(subject_for(messages), body + footer)
            print("Email sent.")
    else:
        print("No reminders today.")

    if errors:
        print("\nProblems in birthdays.csv (these rows were skipped):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
