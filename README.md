# Birthday Reminder

Emails you (through Gmail) when a friend's birthday is coming up. A GitHub Action runs it once a day, so it works even when your PC is off.

## Adding friends
Edit `birthdays.csv`, either on github.com (open the file, click the pencil icon, then **Commit changes**) or locally and push.

```
name,birthday,remind_days_before
Sam,03-14,
Alex,1995-07-02,14
Jordan,02-29,3;1
```

| Column | Meaning |
|---|---|
| `name` | Friend's name |
| `birthday` | `MM-DD`, or `YYYY-MM-DD` if you know the year (then the message says how old they're turning) |
| `remind_days_before` | Blank = 7 days. Several are allowed, e.g. `14;3;1`. You always get a reminder on the day too. |

Lines starting with `#` are ignored. Feb 29 birthdays are celebrated on Feb 28 in non-leap years.
Each time you change the file, GitHub checks it for typos. If there's a problem, the run fails and GitHub emails you.

## One-time setup
1. Turn on **2-Step Verification** for your Google account (myaccount.google.com → Security).
2. Create an **App Password** at https://myaccount.google.com/apppasswords (any name, e.g. "bday reminders"). Google shows a 16-letter password once, so copy it.
3. In the GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**. Add:
   - `EMAIL_USER`: your Gmail address
   - `EMAIL_APP_PASSWORD`: the 16-letter App Password (spaces are fine)
   - `EMAIL_TO` *(optional)*: a different address to send reminders to. If you skip it, they go to `EMAIL_USER`.
4. **Actions → Birthday reminders → Run workflow**, tick **test**, and run it. You should get a test email within a minute (check spam the first time).

Secrets are hidden even though the repo is public. To stop the emails, delete the App Password in your Google account.

## Settings
- **Time zone:** `TZ_NAME` in `.github/workflows/reminders.yml` (e.g. `America/Los_Angeles`, `Europe/London`).
- **Time of day:** the `cron` line in the same file. It's in UTC, so `0 17 * * *` = 17:00 UTC (9 AM Pacific).

## Running locally
```
python check_birthdays.py --dry-run                    # what would be sent today
python check_birthdays.py --dry-run --date 2026-03-07  # pretend it's another day
python -m unittest                                     # run the tests
```
