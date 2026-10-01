---
name: phone-calls
description: "Place fully-automated outbound voice calls via Twilio as part of any Muse workflow: dial a number, speak a message, optionally collect a keypad response (press 1/2), and check call status/results. Triggers on requests to call or phone someone, e.g. 'call the restaurant', 'phone them and confirm', 'dial this number and ask'."
---

# Phone Calls

## Purpose

Place outbound voice calls through Twilio with zero manual steps per call.

After a one-time `setup`, the skill dials numbers, speaks messages with `<Say>`, and can present an interactive keypad menu whose answer is captured automatically.

No webhook server is required: calls use inline TwiML, and digit capture is handled by a Twilio Function (serverless) that the `setup` command provisions and deploys for you.

## Tooling

CLI: `bin/twilio-call`

- Python 3
- Standard library only — no pip dependencies

### setup

One-time provisioning:

```bash
bin/twilio-call setup
```

Optionally specify the Twilio caller number:

```bash
bin/twilio-call setup --from +15551234567
```

Setup automatically:

1. Creates the Twilio Serverless Service.
2. Creates the gather-handler Function.
3. Creates a Sync Service and Map for keypad results.
4. Sets the Function environment variables.
5. Builds and deploys everything.
6. Picks the Twilio caller number.
7. Writes local configuration to `~/.config/muse-phone-calls/config.json`.

Re-running setup redeploys the Function and is safe to repeat.

### place

Place an outbound call:

```bash
bin/twilio-call place \
  --to +15551234567 \
  --message "Hello, I'm calling to confirm my reservation."
```

Optional caller number:

```bash
bin/twilio-call place \
  --to +15551234567 \
  --message "Hello." \
  --from +15557654321
```

Optional keypad menu:

```bash
bin/twilio-call place \
  --to +15551234567 \
  --message "Please confirm your reservation." \
  --menu "1:Confirm,2:Cancel"
```

With `--menu`, the call speaks:

> Press 1 to Confirm. Press 2 to Cancel.

The deployed Function records the pressed digit.

Menu format: `"1:Label,2:Label"`. Only single digits 0-9 are supported.

Preview the TwiML without placing a call:

```bash
bin/twilio-call place \
  --to +15551234567 \
  --message "Hello." \
  --dry-run
```

### status

Check call status:

```bash
bin/twilio-call status --sid CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Returns JSON containing the Call SID, status, duration, and timestamps.

### result

Retrieve a keypad result:

```bash
bin/twilio-call result --sid CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Poll for a result:

```bash
bin/twilio-call result \
  --sid CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
  --wait 15
```

The result contains the digit pressed by the recipient.

If no digit was captured:

```json
{
  "sid": "CA...",
  "digits": null
}
```

`digits: null` means no keypad input was recorded. This may mean the recipient did not answer, hung up, or timed out. Never guess the result.

Results expire after 24 hours.

## Auth

Twilio authenticates with HTTP Basic:

- Account SID
- Auth Token

The custom connector credential flow cannot hold a two-secret scheme, so it is not used here.

Instead, the CLI reads these from the process environment:

```
TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN
```

Set them yourself in your shell according to the setup instructions in [references/twilio-setup.md](references/twilio-setup.md).

Never:

- Ask the user to provide these values in chat.
- Write them into source files.
- Commit them to GitHub.
- Log them.
- Echo them.
- Store them in memory.

The deployed Twilio Function receives its own credentials automatically from its Twilio Function context (`IncludeCredentials`) and does not require these secrets to be written into the skill.

## Operating Rules

### 1. User-requested calls only

Calls are placed ONLY as part of a workflow explicitly requested by the user.

Examples:

- Confirming the user's reservation.
- Cancelling the user's appointment.
- Calling a business about an existing order.
- Contacting a service provider at the user's request.

Never place:

- Unprompted calls.
- Cold calls.
- Bulk calls.
- Marketing calls.
- Telemarketing blasts.
- Spam calls.

### 2. Confirm the call before placing it

Before placing a call, state:

1. The exact number being dialed.
2. The exact message being spoken.
3. The keypad menu, if one is being used.
4. The expected Twilio cost when practical.

Example:

> I'm going to call +15551234567.
>
> I'll say:
> "Hello, I'm calling to confirm my reservation for tomorrow at 7 PM."
>
> Estimated Twilio cost: approximately $0.01–$0.02/minute.

Use `--dry-run` when useful to preview the TwiML.

### 3. Keep costs visible

Twilio voice calls and phone numbers have usage and rental charges.

US voice pricing is commonly in the cent-per-minute range, but prices can change. Confirm current rates in the Twilio console before relying on a specific price.

Do not present an estimate as an exact price.

### 4. Robocall / TCPA caution

Use this skill only for legitimate, user-requested first-party business calls.

Examples include:

- Confirming the user's own reservation.
- Cancelling the user's own appointment.
- Contacting a business about an existing order.
- Calling a business to obtain information requested by the user.

Never use this skill to:

- Robocall consumers.
- Conduct telemarketing blasts.
- Make unsolicited bulk calls.
- Circumvent consent requirements.
- Spoof caller ID.

Users are responsible for complying with applicable telecommunications, privacy, and other laws.

### 5. Caller ID

Never spoof caller ID.

Use a legitimate Twilio phone number assigned to the user's Twilio account.

### 6. Trial accounts

Trial Twilio accounts can generally only call verified destination numbers.

Real-world use may require an upgraded paid account and a purchased Twilio phone number.

### 7. API errors

On API errors:

1. Surface Twilio's error code.
2. Surface Twilio's error message.
3. Do not silently suppress the error.
4. Do not retry blindly.

Example:

> Twilio error 21211:
> The 'To' phone number is not a valid phone number.

### 8. Never guess call results

A successful connection does not prove that the requested task was completed.

Do not infer confirmation from:

- A connected call.
- Call duration.
- The recipient answering.
- The user expecting a particular outcome.

For keypad workflows, only report what was actually captured.

If `{"digits": "1"}`, the recipient pressed 1. If `{"digits": null}`, no keypad response was captured. Report that plainly.

## Example Workflows

### Confirm a reservation

User:

> Call the restaurant and confirm my reservation.

Before calling, show the exact destination and message:

> Number: +15551234567
>
> Message:
> "Hello, I'm calling to confirm a reservation for tomorrow at 7 PM."

After approval, place the call.

### Cancel an appointment

```bash
bin/twilio-call place \
  --to +15551234567 \
  --message "Hello, I'm calling to cancel an appointment scheduled for tomorrow."
```

Do not claim that the appointment was cancelled unless the call workflow actually establishes that result.

### Interactive confirmation

Place:

```bash
bin/twilio-call place \
  --to +15551234567 \
  --message "Please confirm the appointment." \
  --menu "1:Confirm,2:Cancel"
```

Then retrieve:

```bash
bin/twilio-call result \
  --sid CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
  --wait 15
```

Possible results:

```json
{ "sid": "CA...", "digits": "1" }
```

Report: "The recipient pressed 1 (Confirm)."

```json
{ "sid": "CA...", "digits": "2" }
```

Report: "The recipient pressed 2 (Cancel)."

```json
{ "sid": "CA...", "digits": null }
```

Report: "No keypad response was captured."

## Security

Treat phone numbers and call contents as potentially sensitive.

Never expose:

- Twilio authentication credentials.
- Private configuration files.
- User secrets.
- Authentication tokens.

Never commit these to source control:

```
.env
.env.*
~/.config/muse-phone-calls/config.json
```

## Limitations

This skill currently supports:

- Outbound calls.
- Text-to-speech messages.
- Single-digit keypad menus.
- Call status.
- Keypad result retrieval.

It does not currently provide:

- General speech-to-text conversation.
- Natural-language two-way voice conversation.
- Inbound calling.
- Call recording.
- Call transcription.
- Multi-turn voice agents.
- Bulk calling.

These capabilities can be added separately in future versions.

## Workflow

The skill provides a bridge from Muse workflows into the telephone network:

```
User request
     ↓
Muse
     ↓
Phone Calls Skill
     ↓
Twilio
     ↓
Phone Network
     ↓
Business
     ↓
Call / keypad result
     ↓
Muse
```

The goal is reliable, user-authorized automation of real-world phone interactions.
