import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from check_birthdays import (
    Friend, load_friends, next_birthday, parse_lead_days, reminders_for, send_email, subject_for,
)


def f(name, month, day, year=None, lead=(7,)):
    return Friend(name, month, day, year, lead)


class NextBirthdayTests(unittest.TestCase):
    def test_later_this_year(self):
        self.assertEqual(next_birthday(f("A", 3, 14), date(2026, 3, 1)), date(2026, 3, 14))

    def test_today(self):
        self.assertEqual(next_birthday(f("A", 3, 14), date(2026, 3, 14)), date(2026, 3, 14))

    def test_wraps_to_next_year(self):
        self.assertEqual(next_birthday(f("A", 1, 3), date(2026, 12, 30)), date(2027, 1, 3))

    def test_feb29_non_leap_year(self):
        self.assertEqual(next_birthday(f("A", 2, 29), date(2026, 2, 1)), date(2026, 2, 28))

    def test_feb29_leap_year(self):
        self.assertEqual(next_birthday(f("A", 2, 29), date(2028, 2, 1)), date(2028, 2, 29))


class ReminderTests(unittest.TestCase):
    def test_day_of_always(self):
        msgs = reminders_for([f("Sam", 3, 14, lead=(30,))], date(2026, 3, 14))
        self.assertEqual(msgs, ["🎂 Today is Sam's birthday!"])

    def test_default_seven_days(self):
        msgs = reminders_for([f("Sam", 3, 14)], date(2026, 3, 7))
        self.assertEqual(msgs, ["Sam has a birthday in 7 days (Sat, Mar 14)"])

    def test_not_on_other_days(self):
        self.assertEqual(reminders_for([f("Sam", 3, 14)], date(2026, 3, 8)), [])

    def test_multiple_lead_days_and_tomorrow(self):
        fr = f("Jo", 5, 10, lead=(3, 1))
        self.assertEqual(len(reminders_for([fr], date(2026, 5, 7))), 1)
        self.assertIn("tomorrow", reminders_for([fr], date(2026, 5, 9))[0])
        self.assertEqual(reminders_for([fr], date(2026, 5, 3)), [])

    def test_age(self):
        msgs = reminders_for([f("Alex", 7, 2, year=1995, lead=(14,))], date(2026, 6, 18))
        self.assertEqual(msgs, ["Alex turns 31 in 14 days (Thu, Jul 2)"])

    def test_age_across_new_year(self):
        msgs = reminders_for([f("B", 1, 2, year=2000, lead=(3,))], date(2026, 12, 30))
        self.assertIn("turns 27", msgs[0])

    def test_sorted_soonest_first(self):
        friends = [f("Later", 3, 21, lead=(7,)), f("Now", 3, 14)]
        msgs = reminders_for(friends, date(2026, 3, 14))
        self.assertTrue(msgs[0].startswith("🎂 Today is Now"))


class LoadTests(unittest.TestCase):
    def test_parse_lead_days(self):
        self.assertEqual(parse_lead_days(""), (7,))
        self.assertEqual(parse_lead_days("14;3;1"), (14, 3, 1))
        with self.assertRaises(ValueError):
            parse_lead_days("-2")

    def test_load_with_comments_and_bad_rows(self):
        content = (
            "# comment\n"
            "name,birthday,remind_days_before\n"
            "Sam,03-14,\n"
            "\n"
            "Bad,13-40,\n"
            ",01-01,\n"
            "Alex,1995-07-02,14\n"
            "Leap,02-29,3;1\n"
        )
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "b.csv"
            p.write_text(content, encoding="utf-8")
            friends, errors = load_friends(p)
        self.assertEqual([x.name for x in friends], ["Sam", "Alex", "Leap"])
        self.assertEqual(friends[1].year, 1995)
        self.assertEqual(friends[2].lead_days, (3, 1))
        self.assertEqual(len(errors), 2)


class EmailTests(unittest.TestCase):
    def test_subject(self):
        self.assertEqual(subject_for(["Sam has a birthday tomorrow"]), "Sam has a birthday tomorrow")
        self.assertEqual(subject_for(["a", "b"]), "🎂 2 birthday reminders")

    def test_send_email_uses_gmail_and_defaults_to_self(self):
        env = {"EMAIL_USER": "me@gmail.com", "EMAIL_APP_PASSWORD": "abcd efgh ijkl mnop"}
        with mock.patch.dict(os.environ, env, clear=False), \
                mock.patch.dict(os.environ, {"EMAIL_TO": ""}), \
                mock.patch("smtplib.SMTP_SSL") as smtp_cls:
            send_email("Subj", "Body")
        smtp_cls.assert_called_once_with("smtp.gmail.com", 465, timeout=30)
        smtp = smtp_cls.return_value.__enter__.return_value
        smtp.login.assert_called_once_with("me@gmail.com", "abcdefghijklmnop")
        sent = smtp.send_message.call_args[0][0]
        self.assertEqual(sent["To"], "me@gmail.com")
        self.assertEqual(sent["Subject"], "Subj")

    def test_missing_credentials(self):
        with mock.patch.dict(os.environ, {"EMAIL_USER": "", "EMAIL_APP_PASSWORD": ""}):
            with self.assertRaises(SystemExit):
                send_email("s", "b")


if __name__ == "__main__":
    unittest.main()
