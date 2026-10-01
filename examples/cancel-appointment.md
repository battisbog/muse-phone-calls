# Example: Cancel an appointment

**User request**

> Call the clinic and cancel my appointment tomorrow.

**Before calling, Muse states what it will do:**

> I'm going to call +15551234567.
>
> I'll say: "Hello, I'm calling to cancel an appointment scheduled for tomorrow."

**After the user approves:**

```bash
bin/twilio-call place \
  --to +15551234567 \
  --message "Hello, I'm calling to cancel an appointment scheduled for tomorrow."
```

Check the call status:

```bash
bin/twilio-call status --sid CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Optional: ask for a keypad acknowledgement**

```bash
bin/twilio-call place \
  --to +15551234567 \
  --message "I'm calling to cancel tomorrow's appointment. Please press 1 if this is cancelled." \
  --menu "1:Cancelled,2:Not cancelled"
```

**Reporting the result**

The call status shows only that a call happened. Muse does not claim the appointment was cancelled unless a keypad response (for example `{"digits": "1"}`) establishes it. If `digits` is `null`, Muse reports that no response was captured and suggests the user follow up directly.
