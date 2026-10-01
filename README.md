# Meta Muse Phone Calls

This skill gives Meta Muse the ability to make outbound phone calls through [Twilio](https://www.twilio.com/). Muse can dial a number, speak a message, optionally collect a single keypad response (for example "press 1 to confirm"), and report the call status and result.

The full skill definition Muse loads is in [`SKILL.md`](SKILL.md).

## How it works

```
Meta Muse → Phone Calls Skill → Twilio → Phone Network → Business
```

- Calls use inline TwiML with text-to-speech (`<Say>`), so no webhook server is needed.
- Keypad digits are captured by a Twilio Function that `setup` provisions and deploys in your own Twilio account.
- The CLI (`bin/twilio-call`) is Python 3, standard library only — no pip dependencies.

## Supported use cases

- **Cancel appointments** — call a business to cancel your own appointment.
- **Confirm reservations** — call a restaurant or venue to confirm your own reservation.
- **Call businesses** — place a spoken message about an existing order or a question you asked Muse to relay.
- **Collect keypad responses** — offer a single-digit menu (`1:Confirm,2:Cancel`) and read back which digit was pressed.

## Installation

1. Create a Twilio account and get a Twilio phone number. See [`references/twilio-setup.md`](references/twilio-setup.md).
2. Export your credentials in your shell (never commit them):

   ```bash
   export TWILIO_ACCOUNT_SID="..."
   export TWILIO_AUTH_TOKEN="..."
   ```

3. Clone this repo and run the one-time setup:

   ```bash
   git clone https://github.com/battisbog/muse-phone-calls.git
   cd muse-phone-calls
   bin/twilio-call setup
   ```

   Setup provisions the Twilio resources, picks a caller number, and writes local config to `~/.config/muse-phone-calls/config.json`. That file stays on your machine and is git-ignored. Re-running setup is safe.

4. Make `SKILL.md` available to Meta Muse as the `phone-calls` skill.

## Example commands

```bash
# Preview the TwiML without placing a call
bin/twilio-call place --to +15551234567 --message "Hello." --dry-run

# Place a call
bin/twilio-call place \
  --to +15551234567 \
  --message "Hello, I'm calling to confirm my reservation."

# Place a call with a keypad menu
bin/twilio-call place \
  --to +15551234567 \
  --message "Please confirm the appointment." \
  --menu "1:Confirm,2:Cancel"

# Check call status
bin/twilio-call status --sid CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Get the keypad result (waits up to 15 seconds)
bin/twilio-call result --sid CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx --wait 15
```

Worked examples: [confirm a reservation](examples/confirm-reservation.md), [cancel an appointment](examples/cancel-appointment.md).

## Testing

The test suite runs fully offline against a fake Twilio API, so it needs no credentials and places no calls:

```bash
python3 -m unittest discover tests
```

It covers setup provisioning and re-runs, call placement and TwiML, status, result polling, Twilio error reporting, and (when Node.js is installed) the deployed keypad Function. Before relying on the skill, also run `setup` and place one test call to a number you have verified in Twilio.

## Limitations

Supported: outbound calls, text-to-speech messages, single-digit keypad menus, call status, and keypad result retrieval.

Not supported: speech-to-text or two-way voice conversation, inbound calls, recording, transcription, multi-turn voice agents, or bulk calling.

A connected call does not prove a task was completed. Only a captured keypad digit is reported as a result; `digits: null` means nothing was captured.

## Responsible use

Twilio usage and phone-number rental are billed to your account; trial accounts can generally only call verified numbers. Use this only for legitimate, user-requested, first-party calls. Do not use it for robocalls, telemarketing, bulk calling, or caller-ID spoofing. You are responsible for complying with applicable laws. See the operating rules in [`SKILL.md`](SKILL.md).

## License

[MIT](LICENSE)
