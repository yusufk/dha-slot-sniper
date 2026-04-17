#!/usr/bin/env python3
"""
DHA Slot Sniper — Automatically find and book Department of Home Affairs appointments.

Uses the services.dha.gov.za API to poll for available passport/ID slots
and auto-books the first one found.

Usage:
    python3 sniper.py --id <ID_NUMBER> --name <FORENAMES> --surname <SURNAME>
    python3 sniper.py --config config.json
"""

import argparse, json, os, sys, time, urllib.request
import requests
from datetime import datetime, timedelta

API = "https://services.dha.gov.za/api/booking"

SERVICES = {
    "passport":      {"product": "IDs / Travel Documents", "service": "Passport Application"},
    "id":            {"product": "IDs / Travel Documents", "service": "ID Application"},
    "id-collection": {"product": "IDs / Travel Documents", "service": "ID Collection"},
}
DEFAULT_SERVICE = "passport"

# All branches — add/remove as needed
DEFAULT_BRANCHES = {
    "CSC": "Cresta",
    "YHH": "Randburg",
    "YCX": "Roodepoort",
    "YCH": "Johannesburg",
}


def send_telegram(token, chat_id, msg):
    if not token or not chat_id:
        return
    try:
        data = json.dumps({"chat_id": chat_id, "text": msg}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


def authenticate(session, id_number, forenames, surname, contact_number, email=""):
    """Authenticate with the DHA API. Returns True if successful."""
    # Check for existing appointments
    resp = session.get(f"{API}/checkappointments/", params={
        "identification_type": "ID",
        "identification_val": id_number,
        "send_date": str(int(time.time() * 1000))
    }, timeout=30)
    d = resp.json()
    if d.get("Payload", {}).get("found"):
        print(f"⚠️  You already have an active appointment!")
        print(f"   {d['Payload'].get('message', '')}")
        return False

    # Authenticate
    resp = session.post(f"{API}/authenticatedetails/", json={
        "identification_type": 1,
        "identification_val": id_number,
        "forenames": forenames,
        "surname": surname,
        "contact_number": contact_number,
        "email": email,
        "country_of_issue": ""
    }, timeout=30)
    d = resp.json()
    if not d["ResultSuccess"]:
        print(f"❌ Authentication failed: {d.get('AppInfo', {}).get('description', 'Unknown error')}")
        return False

    if d["Payload"].get("authenticated"):
        print(f"✅ Authenticated: {forenames} {surname}")
        return True

    print(f"❌ Not authenticated: {d['Payload'].get('message', '')}")
    return False


def get_branches(session):
    """Get all available branches."""
    resp = session.get(f"{API}/getbranchdetails/", timeout=30)
    d = resp.json()
    if d["ResultSuccess"]:
        return json.loads(d["Payload"])
    return []


def check_slots(session, branches, id_number, svc):
    """Check all branches with short date ranges for available slots."""
    today = datetime.now()
    for code, name in branches.items():
        for offset in range(0, 28, 4):
            start = today + timedelta(days=1 + offset)
            end = start + timedelta(days=4)
            try:
                resp = session.post(f"{API}/gettimeslotdetails/", json={
                    "branch_code": code,
                    "date_from": start.strftime("%d-%m-%Y"),
                    "date_to": end.strftime("%d-%m-%Y"),
                    "applicants": [{
                        "identity_value": id_number,
                        "identity_type": "ID",
                        "products": [svc["product"]]
                    }]
                }, timeout=30)
                d = resp.json()
                if d["ResultSuccess"]:
                    slots = d.get("Payload", [])
                    if isinstance(slots, str):
                        slots = json.loads(slots)
                    avail = [s for s in slots if s.get("SlotAvailable")]
                    if avail:
                        return name, code, avail
            except Exception:
                continue
    return None, None, []


def book_slot(session, code, slot, id_number, forenames, surname, svc):
    """Book a specific slot. Tries with product first, falls back to empty."""
    for products_and_services in [
        [{"product": svc["product"], "service": svc["service"]}],
        [{"product": "", "service": svc["service"]}],
        [],
    ]:
        resp = session.post(f"{API}/captureappointment/", json={
            "branch_code": code,
            "time_slot_id": slot["TimeSlotID"],
            "appointment_date": slot["Date"],
            "accepted_declaration": True,
            "appointment_request": json.dumps([{
                "identityValue": id_number,
                "identityType": "ID",
                "productsAndServices": products_and_services,
                "forenames": forenames,
                "surname": surname,
                "country": "ZAF"
            }])
        }, timeout=30)
        result = resp.json()
        if result["ResultSuccess"]:
            return result
    return result


def list_branches(session):
    """Print all available branches grouped by province."""
    branches = get_branches(session)
    if not branches:
        print("Could not fetch branches.")
        return

    by_province = {}
    for b in branches:
        prov = b["Province"]
        if prov not in by_province:
            by_province[prov] = []
        by_province[prov].append(b)

    for prov in sorted(by_province):
        print(f"\n{prov}:")
        for b in sorted(by_province[prov], key=lambda x: x["Descr"]):
            web = "🌐" if b.get("isWebSM") == "1" or b.get("isWebSM") == 1 else "  "
            print(f"  {web} {b['ID']:4s}  {b['Descr']:<30s}  ({b['City']})")


def main():
    parser = argparse.ArgumentParser(
        description="DHA Slot Sniper — Find and book Home Affairs appointments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 sniper.py --id 7801015009087 --name JOHN --surname DOE --phone 0821234567
  python3 sniper.py --id 7801015009087 --name JOHN --surname DOE --branches CSC,YHH
  python3 sniper.py --list-branches
  python3 sniper.py --check-only --id 7801015009087

Tips:
  - Slots appear to drop around midnight and early morning (6-8am SAST)
  - Use short date ranges (the tool does this automatically)
  - Run overnight for best results
  - Add --telegram-token and --telegram-chat for mobile alerts
        """)

    parser.add_argument("--id", help="SA ID number (13 digits)")
    parser.add_argument("--name", help="Forenames (as on ID)")
    parser.add_argument("--surname", help="Surname (as on ID)")
    parser.add_argument("--phone", default="", help="Contact number")
    parser.add_argument("--email", default="", help="Email address")
    parser.add_argument("--branches", default="",
                        help="Comma-separated branch codes (e.g. CSC,YHH). If not set, auto-selects from --city")
    parser.add_argument("--city", default="",
                        help="City to search (e.g. JOHANNESBURG, CAPE TOWN, PRETORIA). Auto-selects all branches in that city")
    parser.add_argument("--interval", type=int, default=300,
                        help="Seconds between checks (default: 300 = 5 min)")
    parser.add_argument("--service", default=DEFAULT_SERVICE, choices=SERVICES.keys(),
                        help=f"Service type (default: {DEFAULT_SERVICE}). Options: {', '.join(SERVICES.keys())}")
    parser.add_argument("--check-only", action="store_true",
                        help="Only check for slots, don't book")
    parser.add_argument("--list-branches", action="store_true",
                        help="List all available branches and exit")
    parser.add_argument("--telegram-token", default="", help="Telegram bot token for alerts")
    parser.add_argument("--telegram-chat", default="", help="Telegram chat ID for alerts")

    args = parser.parse_args()
    session = requests.Session()

    if args.list_branches:
        list_branches(session)
        return

    if not args.id or not args.name or not args.surname:
        parser.error("--id, --name, and --surname are required")

    # Resolve branches
    all_branches = get_branches(session)
    branch_map = {b["ID"]: b for b in all_branches} if all_branches else {}

    if args.branches:
        branch_codes = [b.strip() for b in args.branches.split(",")]
        branches = {code: branch_map.get(code, {}).get("Descr", code) for code in branch_codes}
    elif args.city:
        city_upper = args.city.upper()
        branches = {}
        for b in all_branches:
            if city_upper in b.get("City", "").upper() or city_upper in b.get("Descr", "").upper() or city_upper in b.get("Province", "").upper():
                branches[b["ID"]] = b["Descr"]
        if not branches:
            print(f"❌ No branches found matching '{args.city}'. Use --list-branches to see all options.")
            sys.exit(1)
    else:
        # Default: Johannesburg area
        branches = {"CSC": "Cresta", "YHH": "Randburg", "YCX": "Roodepoort"}

    svc = SERVICES[args.service]

    print(f"🎯 DHA Slot Sniper")
    print(f"   Service: {svc['service']}")
    print(f"   Checking: {', '.join(f'{v} ({k})' for k, v in branches.items())}")
    print(f"   Interval: {args.interval}s")
    print(f"   Mode: {'Check only' if args.check_only else 'Auto-book'}")
    print()

    # Authenticate
    if not authenticate(session, args.id, args.name, args.surname, args.phone, args.email):
        sys.exit(1)

    tg = lambda msg: send_telegram(args.telegram_token, args.telegram_chat, msg)
    tg(f"🔍 DHA Sniper active — checking {', '.join(branches.values())} every {args.interval}s")

    print(f"\n🔍 Polling for slots...\n")

    while True:
        ts = time.strftime("%H:%M:%S")
        name, code, avail = check_slots(session, branches, args.id, svc)

        if avail:
            slot = avail[0]
            print(f"[{ts}] 🚨 {len(avail)} slot(s) at {name}!")
            print(f"        First: {slot['Date']} {slot['StartTime']}-{slot['EndTime']}")

            if args.check_only:
                tg(f"🚨 {len(avail)} DHA slots at {name}!\n{slot['Date']} {slot['StartTime']}-{slot['EndTime']}\nBook at: https://services.dha.gov.za")
                print(f"        (check-only mode — not booking)")
            else:
                tg(f"🚨 {len(avail)} DHA slots at {name}! Auto-booking...")
                result = book_slot(session, code, slot, args.id, args.name, args.surname, svc)

                if result["ResultSuccess"]:
                    ref = result["Payload"].get("ReferenceNo", "?")
                    date = slot["Date"]
                    stime = slot["StartTime"]
                    print(f"[{ts}] ✅ BOOKED! Ref: {ref}")
                    print(f"        Branch: {name}")
                    print(f"        Date: {date} at {stime}")
                    tg(f"✅ BOOKED at {name}!\nRef: {ref}\nDate: {date} {stime}\n\nBring your ID and old passport!")
                    break
                else:
                    err = result.get("AppInfo", {}).get("description", "Unknown error")
                    print(f"[{ts}] ⚠️  Booking failed: {err}")
                    tg(f"⚠️ Slots found at {name} but booking failed: {err}")
        else:
            print(f"[{ts}] No slots")

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
