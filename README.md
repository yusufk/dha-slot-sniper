# DHA Slot Sniper 🎯

Automatically find and book Department of Home Affairs (South Africa) appointments for passport renewals, ID applications, and other services.

Built out of frustration with the broken ehome.dha.gov.za booking system. This tool uses the newer `services.dha.gov.za` API which doesn't require CAPTCHA or OTP.

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-yusufk-yellow?style=flat&logo=buy-me-a-coffee)](https://buymeacoffee.com/yusufk)

## How It Works

1. Authenticates with the DHA services API using your ID number
2. Polls multiple branches every 60 seconds using short date ranges (4-day windows)
3. When a slot appears, auto-books it immediately
4. Sends you a Telegram notification (optional)

## Quick Start

```bash
# Install dependency
pip install requests

# Run the sniper
python3 sniper.py --id <YOUR_ID_NUMBER> --name <FORENAMES> --surname <SURNAME> --phone <PHONE>

# Example
python3 sniper.py --id 7801015009087 --name JOHN --surname DOE --phone 0821234567
```

## Options

```
--id            SA ID number (13 digits) [required]
--name          Forenames as on ID [required]
--surname       Surname as on ID [required]
--phone         Contact number
--email         Email address
--branches      Comma-separated branch codes (default: CSC,YHH,YCX)
--interval      Seconds between checks (default: 60)
--check-only    Only check for slots, don't auto-book
--list-branches List all available branches
--telegram-token  Telegram bot token for mobile alerts
--telegram-chat   Telegram chat ID for alerts
```

## List Available Branches

```bash
python3 sniper.py --list-branches
```

This shows all DHA branches with their codes. Use the codes with `--branches`:

```bash
# Check Cresta, Randburg, and Cape Town
python3 sniper.py --id ... --name ... --surname ... --branches CSC,YHH,CPT
```

## Tips

- **Run overnight** — slots appear to drop around midnight and early morning (6-8am SAST)
- **Short date ranges** — the tool automatically uses 4-day windows which work better than full month queries
- **Multiple branches** — check several nearby branches to maximize your chances
- **Telegram alerts** — set up a bot via [@BotFather](https://t.me/BotFather) so you get notified on your phone

## Telegram Setup (Optional)

1. Message [@BotFather](https://t.me/BotFather) on Telegram → `/newbot` → follow prompts → get token
2. Message [@userinfobot](https://t.me/userinfobot) → get your chat ID
3. Run with alerts:

```bash
python3 sniper.py --id ... --name ... --surname ... \
  --telegram-token "123456:ABC..." \
  --telegram-chat "12345678"
```

## Background

The DHA has two booking systems:

1. **ehome.dha.gov.za** (old) — CAPTCHA + SMS OTP + sessions that expire in minutes. Nearly impossible to automate.
2. **services.dha.gov.za** (new) — REST API, no CAPTCHA, no OTP. This is what this tool uses.

The new system has slots available but they're scarce for passport/ID services and get snapped up quickly. This tool polls continuously and books the moment one appears.

## Disclaimer

This tool interacts with a public government API in the same way the official website does. It does not bypass any security measures. Use responsibly.

## License

MIT

---

*If this saved you hours of refreshing the DHA website, consider [buying me a coffee](https://buymeacoffee.com/yusufk) ☕*
