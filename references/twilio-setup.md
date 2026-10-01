# Twilio Setup

How to prepare a Twilio account for the `phone-calls` skill.

## 1. Create an account

Sign up at <https://www.twilio.com/try-twilio>. A trial account works for testing, but it can generally only call **verified** destination numbers. Verify your own number in the Twilio console under *Phone Numbers → Verified Caller IDs*. Calling real businesses typically requires upgrading to a paid account.

## 2. Get a Twilio phone number

Buy or claim a voice-capable number in the Twilio console (*Phone Numbers → Manage → Buy a number*). Calls are placed from a number on your own account. Never spoof caller ID. Numbers have a monthly rental charge.

## 3. Find your credentials

In the Twilio console dashboard, copy:

- **Account SID** (starts with `AC`)
- **Auth Token**

## 4. Set environment variables

The CLI reads credentials from the process environment:

| Variable | Description |
| --- | --- |
| `TWILIO_ACCOUNT_SID` | Your Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | Your Twilio Auth Token |

```bash
export TWILIO_ACCOUNT_SID="<your account sid>"
export TWILIO_AUTH_TOKEN="<your auth token>"
```

To persist them, add the exports to your shell profile, or use a `.env` file that you load yourself. `.env` files are git-ignored in this repo.

**Never** paste these values into chat, commit them, log them, or write them into source files.

## 5. Run setup

```bash
bin/twilio-call setup
# or choose the caller number explicitly:
bin/twilio-call setup --from +15551234567
```

Setup creates a Serverless Service and gather-handler Function, a Sync Service and Map for keypad results, deploys them, picks a caller number, and writes `~/.config/muse-phone-calls/config.json`. Do not commit that file. Re-running setup redeploys safely.

## 6. Test

```bash
bin/twilio-call place --to +15551234567 --message "Test." --dry-run
```

Replace the example number with a number you are allowed to call. Check current Twilio pricing in the console before placing real calls.
