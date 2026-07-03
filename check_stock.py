#!/usr/bin/env python3
"""
Woot restock watcher for the Eureka J20 Robot Vacuum.

Does two things every run:
  1. Checks the known offer URL to see if it's back in stock.
  2. Scans Woot search results for any NEW Eureka J20 listing
     (Woot usually relists under a new URL, e.g. ...-5).

Sends a Discord webhook when either happens. Uses state.json to
avoid spamming you with duplicate notifications.
"""

import json
import os
import re
import sys
import urllib.request

# ----------------------------------------------------------------------
# Config — edit these if you want to watch a different product
# ----------------------------------------------------------------------
OFFER_URL = "https://www.woot.com/offers/new-eureka-j20-robot-vacuum-and-mop-4"
SEARCH_URL = "https://www.woot.com/searchresults?query=eureka%20j20"
# Regex that a relisted offer URL would match (the -4 suffix may change)
OFFER_PATTERN = re.compile(r"/offers/[a-z0-9-]*eureka-j20[a-z0-9-]*", re.I)

STATE_FILE = "state.json"
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

SOLD_OUT_MARKERS = [
    "sold out",
    '"soldout":true',
    '"issoldout":true',
    '"isSoldOut":true'.lower(),
]

IN_STOCK_MARKERS = [
    '"soldout":false',
    '"issoldout":false',
    "add to cart",
    "buy now",
]


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace").lower()


def load_state() -> dict:
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"notified_in_stock": False, "known_urls": []}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def notify_discord(message: str) -> None:
    if not WEBHOOK_URL:
        print("WARNING: DISCORD_WEBHOOK_URL not set; would have sent:")
        print(message)
        return
    payload = json.dumps({
        "content": message,
        "username": "Woot Watcher",
        "allowed_mentions": {"parse": ["everyone"]},
    }).encode("utf-8")
    req = urllib.request.Request(
        WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": HEADERS["User-Agent"]},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(f"Discord webhook sent, status {resp.status}")


def check_known_offer(state: dict) -> None:
    """Check the original listing URL for a restock."""
    try:
        html = fetch(OFFER_URL)
    except Exception as e:
        print(f"Could not fetch offer page: {e}")
        return

    sold_out = any(m in html for m in SOLD_OUT_MARKERS)
    in_stock = any(m in html for m in IN_STOCK_MARKERS)

    print(f"Offer page: sold_out={sold_out}, in_stock_signals={in_stock}")

    if in_stock and not sold_out:
        if not state.get("notified_in_stock"):
            notify_discord(
                f"@everyone 🟢 **Eureka J20 is BACK IN STOCK on Woot!**\n{OFFER_URL}"
            )
            state["notified_in_stock"] = True
    else:
        # Reset so we re-notify if it restocks again later
        state["notified_in_stock"] = False


def check_for_new_listings(state: dict) -> None:
    """Scan Woot search results for new J20 offer URLs."""
    try:
        html = fetch(SEARCH_URL)
    except Exception as e:
        print(f"Could not fetch search page: {e}")
        return

    found = set(OFFER_PATTERN.findall(html))
    known = set(state.get("known_urls", []))
    # Seed with the original so we don't alert on the dead listing
    known.add("/offers/new-eureka-j20-robot-vacuum-and-mop-4")

    new = found - known
    print(f"Search page: found {len(found)} J20 URLs, {len(new)} new")

    for path in sorted(new):
        notify_discord(
            f"@everyone 🆕 **New Eureka J20 listing spotted on Woot!**\nhttps://www.woot.com{path}"
        )

    state["known_urls"] = sorted(known | found)


def run_once() -> None:
    state = load_state()
    check_known_offer(state)
    check_for_new_listings(state)
    save_state(state)


def main() -> int:
    """
    If LOOP_SECONDS is set (GitHub Actions mode), keep checking every
    CHECK_INTERVAL seconds until LOOP_SECONDS elapses, then exit so the
    workflow can relaunch a fresh job. Otherwise run a single check.
    """
    import time

    loop_seconds = int(os.environ.get("LOOP_SECONDS", "0"))
    interval = int(os.environ.get("CHECK_INTERVAL", "60"))

    if loop_seconds <= 0:
        run_once()
        return 0

    deadline = time.time() + loop_seconds
    n = 0
    while time.time() < deadline:
        n += 1
        print(f"--- check #{n} ---", flush=True)
        try:
            run_once()
        except Exception as e:
            print(f"Check failed (will retry): {e}", flush=True)
        # Sleep, but don't overshoot the deadline
        remaining = deadline - time.time()
        if remaining <= interval:
            break
        time.sleep(interval)
    print(f"Loop finished after {n} checks; exiting for relaunch.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
