# Example: Confirm a reservation

**User request**

> Call the restaurant and confirm my reservation.

**Before calling, Muse states what it will do:**

> I'm going to call +15551234567.
>
> I'll say: "Hello, I'm calling to confirm a reservation for tomorrow at 7 PM."
>
> Menu: 1 = Confirm, 2 = Cancel.
>
> Estimated Twilio cost is in the cent-per-minute range; check the Twilio console for current rates.

**After the user approves:**

```bash
bin/twilio-call place \
  --to +15551234567 \
  --message "Hello, I'm calling to confirm a reservation for tomorrow at 7 PM." \
  --menu "1:Confirm,2:Cancel"
```

Then retrieve the keypad response:

```bash
bin/twilio-call result --sid CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx --wait 15
```

**Reporting the result**

| Result | What Muse reports |
| --- | --- |
| `{"digits": "1"}` | The recipient pressed 1 (Confirm). |
| `{"digits": "2"}` | The recipient pressed 2 (Cancel). |
| `{"digits": null}` | No keypad response was captured. |

Muse does not assume the reservation is confirmed just because the call connected.
