# Birthday Reminder

Sends a push notification to your phone (via the free [ntfy](https://ntfy.sh) app) when a friend's birthday is coming up. A GitHub Action runs it once a day, so it works even when your PC is off.

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
1. Install **ntfy** on your phone (App Store / Google Play) and subscribe to your private topic name. Treat it like a password: anyone who knows it can read your reminders.
2. In the GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**, name it `NTFY_TOPIC`, and paste the same topic name as the value.
3. **Actions → Birthday reminders → Run workflow**, tick **test**, and run it. Your phone should buzz.

## Settings
- **Time zone:** `TZ_NAME` in `.github/workflows/reminders.yml` (e.g. `America/Los_Angeles`, `Europe/London`).
- **Time of day:** the `cron` line in the same file. It's in UTC, so `0 17 * * *` = 17:00 UTC (9 AM Pacific).

## Running locally
```
python check_birthdays.py --dry-run                    # what would be sent today
python check_birthdays.py --dry-run --date 2026-03-07  # pretend it's another day
python -m unittest                                     # run the tests
```
