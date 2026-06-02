"""
Passport Fee Scraper
Checks USPS and State Department websites for fee changes
and compares against the current known fees in fees.json.
"""

import json
import re
import sys
import smtplib
import urllib.request
import urllib.error
from html.parser import HTMLParser
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

FEES_FILE = Path(__file__).parent / "fees.json"

STATE_DEPT_URL = "https://travel.state.gov/content/travel/en/passports/how-apply/fees.html"
USPS_PRICES_URL = "https://www.usps.com/business/prices.htm"
# Individual service pages used only for delivery timeframes
USPS_EXPRESS_URL = "https://www.usps.com/ship/priority-mail-express.htm"
USPS_PRIORITY_URL = "https://www.usps.com/ship/priority-mail.htm"


class TextExtractor(HTMLParser):
    """Simple HTML to text converter."""

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            self.text_parts.append(data)

    def get_text(self):
        return " ".join(self.text_parts)


def fetch_page(url: str) -> str:
    """Fetch a web page and return its text content."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; PassportFeeChecker/1.0)"
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    parser = TextExtractor()
    parser.feed(html)
    return parser.get_text()


def find_dollar_amounts(text: str) -> list[tuple[str, float]]:
    """Extract all dollar amounts from text with surrounding context."""
    results = []
    for match in re.finditer(r'(\$[\d,]+\.?\d{0,2})', text):
        amount_str = match.group(1).replace("$", "").replace(",", "")
        try:
            amount = float(amount_str)
        except ValueError:
            continue
        # Grab ~80 chars of context around the match
        start = max(0, match.start() - 40)
        end = min(len(text), match.end() + 40)
        context = text[start:end].strip()
        results.append((context, amount))
    return results


def scrape_state_dept_fees() -> dict:
    """Scrape passport fees from the State Department website."""
    text = fetch_page(STATE_DEPT_URL)
    amounts = find_dollar_amounts(text)
    text_lower = text.lower()

    fees = {}

    # Strategy 1: Look for fee amounts near specific product labels
    # Use tight patterns that match "Passport Book" → next dollar amount
    # but NOT "Passport Book & Card" (which is a different product)
    row_patterns = {
        "adult_book": [
            # "Passport Book" followed by a dollar amount, but not "& Card" in between
            r'passport\s+book(?!\s*(?:&|and)\s*card).*?\$(\d+\.?\d*)',
        ],
        "child_book": [
            r'child\s+passport\s+book(?!\s*(?:&|and)\s*card).*?\$(\d+\.?\d*)',
        ],
        "adult_card": [
            # "Passport Card" followed by a dollar amount
            r'passport\s+card(?!\s*(?:&|and)).*?\$(\d+\.?\d*)',
        ],
        "child_card": [
            r'child\s+passport\s+card(?!\s*(?:&|and)).*?\$(\d+\.?\d*)',
        ],
        "adult_book_card": [
            r'passport\s+book\s*(?:&|and)\s*card.*?\$(\d+\.?\d*)',
        ],
        "child_book_card": [
            r'child\s+passport\s+book\s*(?:&|and)\s*card.*?\$(\d+\.?\d*)',
        ],
        "execution_fee": [
            r'(?:acceptance|execution)\s+fee.*?\$(\d+\.?\d*)',
            r'\$(\d+\.?\d*)\s+acceptance\s+fee',
        ],
        "expedite": [
            r'expedit\w*.*?\$(\d+\.?\d*)',
        ],
        "return_delivery": [
            r'1-3\s*day\s+delivery.*?\$(\d+\.?\d*)',
            r'add\s+1-3\s*day.*?\$(\d+\.?\d*)',
        ],
    }

    for fee_key, pattern_list in row_patterns.items():
        for pattern in pattern_list:
            match = re.search(pattern, text_lower)
            if match:
                fees[fee_key] = float(match.group(1))
                break

    # Strategy 2: Validate/fill gaps using known amounts found on the page
    # This catches fees the regex missed by recognizing known government-set amounts
    known_state_amounts = {
        130.0: "adult_book",
        100.0: "child_book",
        30.0: "adult_card",
        15.0: "child_card",
        160.0: "adult_book_card",
        115.0: "child_book_card",
        35.0: "execution_fee",
        60.0: "expedite",
        22.05: "return_delivery",
        150.0: "file_search",  # not in our fee schedule but on the page
    }

    for context, amount in amounts:
        if amount in known_state_amounts:
            key = known_state_amounts[amount]
            if key not in fees and key != "file_search":
                fees[key] = amount

    return fees


def scrape_usps_fees() -> dict:
    """Scrape USPS pricing from the consolidated prices page."""
    text = fetch_page(USPS_PRICES_URL)
    text_lower = text.lower()
    amounts = find_dollar_amounts(text)

    fees = {}

    # Look for the Priority Mail Express Flat Rate Envelope price at the Post Office.
    # The page has "Prices start at $33.00" (generic) AND the specific
    # "Flat Rate Envelope ... $33.25 at the Post Office" (what we want).
    # We need the specific flat rate envelope price, not the generic "starts at" price.
    # Match: "Flat Rate Envelope" (not Legal/Padded) near a price and "Post Office"
    express_match = re.search(
        r'(?:priority\s*mail\s*express\s+)?flat\s+rate\s+envelope'
        r'(?!\s*\()' # not followed by dimensions (to avoid matching in wrong context)
        r'[^$]*?\$(\d+\.\d{2})\s*(?:at\s+(?:the\s+)?)?post\s+office',
        text_lower
    )
    if express_match:
        fees["priority_express"] = float(express_match.group(1))

    # Fallback: scan dollar amounts for one near a flat rate envelope + post office context
    if "priority_express" not in fees:
        for context, amount in amounts:
            ctx_lower = context.lower()
            if "flat rate envelope" in ctx_lower and "post off" in ctx_lower:
                if "legal" not in ctx_lower and "padded" not in ctx_lower:
                    fees["priority_express"] = amount
                    break

    return fees


def scrape_delivery_times() -> dict:
    """Scrape delivery timeframes from USPS service pages and State Dept."""
    times = {}

    # USPS Priority Mail Express delivery time (from the service page, not prices)
    try:
        text = fetch_page(USPS_EXPRESS_URL)
        text_lower = text.lower()
        for pattern in [
            r'(?:deliver|arrival|arrives?|guaranteed).*?(\d+-\d+)\s*(?:business\s+)?day',
            r'(\d+-\d+)\s*(?:business\s+)?day\s*(?:deliver|guarant)',
            r'overnight.*?(\d+-?\d*)[- ]day',
        ]:
            match = re.search(pattern, text_lower)
            if match:
                times["usps_priority_express"] = f"{match.group(1)} Days"
                break
        if "usps_priority_express" not in times:
            if "overnight" in text_lower or "next-day" in text_lower:
                times["usps_priority_express"] = "1-2 Days"
    except Exception as e:
        print(f"  ERROR scraping USPS Express delivery times: {e}")

    # USPS Priority Mail delivery time (from the service page)
    try:
        text = fetch_page(USPS_PRIORITY_URL)
        text_lower = text.lower()
        match = re.search(r'(\d+-\d+)\s*(?:business\s+)?day', text_lower)
        if match:
            times["usps_priority_mail"] = f"{match.group(1)} Days"
    except Exception as e:
        print(f"  ERROR scraping USPS Priority Mail delivery times: {e}")

    # State Department 1-3 day delivery time (from fees page)
    try:
        text = fetch_page(STATE_DEPT_URL)
        text_lower = text.lower()
        match = re.search(r'(\d+-\d+)\s*day\s*delivery', text_lower)
        if match:
            times["state_dept_return_delivery"] = f"{match.group(1)} Days"
    except Exception as e:
        print(f"  ERROR scraping State Dept delivery times: {e}")

    return times


def compare_delivery_times(current: dict, scraped: dict) -> list[dict]:
    """Compare scraped delivery times against current known times."""
    changes = []
    current_times = current.get("delivery_times", {})

    for key, scraped_time in scraped.items():
        if key in current_times:
            current_time = current_times[key].get("timeframe", "")
            if current_time and scraped_time != current_time:
                changes.append({
                    "key": key,
                    "label": current_times[key].get("label", key),
                    "old_value": current_time,
                    "new_value": scraped_time,
                    "type": "delivery_time",
                })

    return changes


def load_current_fees() -> dict:
    """Load the current known fees from fees.json."""
    with open(FEES_FILE) as f:
        return json.load(f)


def save_fees(data: dict):
    """Save updated fees to fees.json."""
    with open(FEES_FILE, "w") as f:
        json.dump(data, f, indent=2)


def compare_fees(current: dict, scraped: dict) -> list[dict]:
    """
    Compare scraped fees against current known fees.
    Returns a list of changes found.
    """
    changes = []
    fee_sections = current["fees"]

    for section_key, section in fee_sections.items():
        for item_key, item in section["items"].items():
            current_amount = item["amount"]
            if item_key in scraped and scraped[item_key] != current_amount:
                changes.append({
                    "key": item_key,
                    "label": item["label"],
                    "section": section_key,
                    "old_amount": current_amount,
                    "new_amount": scraped[item_key],
                })

    return changes


def format_change_report(changes: list[dict]) -> str:
    """Format fee and delivery time changes into a readable report."""
    if not changes:
        return "No changes detected."

    lines = [
        "=== PASSPORT FEE/DELIVERY CHANGES DETECTED ===",
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]

    fee_changes = [c for c in changes if c.get("type") != "delivery_time"]
    time_changes = [c for c in changes if c.get("type") == "delivery_time"]

    if fee_changes:
        lines.append("FEE CHANGES:")
        for change in fee_changes:
            lines.append(
                f"  {change['label']}:"
                f"  ${change['old_amount']:.2f} -> ${change['new_amount']:.2f}"
            )
        lines.append("")

    if time_changes:
        lines.append("DELIVERY TIME CHANGES:")
        for change in time_changes:
            lines.append(
                f"  {change['label']}:"
                f"  {change['old_value']} -> {change['new_value']}"
            )
        lines.append("")

    lines.append("Action required: Update fees.json and both WordPress sites.")
    return "\n".join(lines)


def send_email_alert(changes: list[dict], config: dict):
    """Send an email alert about fee changes."""
    if not config.get("email_to"):
        return

    report = format_change_report(changes)

    msg = MIMEMultipart()
    msg["From"] = config.get("email_from", "passport-fees@localhost")
    msg["To"] = config["email_to"]
    msg["Subject"] = f"Passport Fee Changes Detected - {datetime.now().strftime('%Y-%m-%d')}"
    msg.attach(MIMEText(report, "plain"))

    try:
        with smtplib.SMTP(config.get("smtp_host", "localhost"),
                          config.get("smtp_port", 587)) as server:
            if config.get("smtp_tls", True):
                server.starttls()
            if config.get("smtp_user"):
                server.login(config["smtp_user"], config["smtp_password"])
            server.send_message(msg)
        print(f"Email alert sent to {config['email_to']}")
    except Exception as e:
        print(f"Failed to send email: {e}")


def check_fees(update: bool = False, verbose: bool = True) -> list[dict]:
    """
    Main function: scrape fees and compare against known values.

    Args:
        update: If True, update fees.json with new values
        verbose: If True, print detailed output

    Returns:
        List of changes detected
    """
    current_data = load_current_fees()

    if verbose:
        print("Checking State Department fees...")
    state_fees = {}
    try:
        state_fees = scrape_state_dept_fees()
        if verbose:
            print(f"  Found {len(state_fees)} fee(s) from State Department")
    except Exception as e:
        print(f"  ERROR scraping State Department: {e}")

    if verbose:
        print("Checking USPS fees...")
    usps_fees = {}
    try:
        usps_fees = scrape_usps_fees()
        if verbose:
            print(f"  Found {len(usps_fees)} fee(s) from USPS")
    except Exception as e:
        print(f"  ERROR scraping USPS: {e}")

    if verbose:
        print("Checking delivery timeframes...")
    delivery_times = {}
    try:
        delivery_times = scrape_delivery_times()
        if verbose:
            print(f"  Found {len(delivery_times)} delivery timeframe(s)")
    except Exception as e:
        print(f"  ERROR scraping delivery times: {e}")

    # Merge all scraped fees
    all_scraped = {**state_fees, **usps_fees}

    if verbose:
        print(f"\nScraped fees:")
        for key, amount in sorted(all_scraped.items()):
            print(f"  {key}: ${amount:.2f}")
        print(f"\nScraped delivery times:")
        for key, timeframe in sorted(delivery_times.items()):
            print(f"  {key}: {timeframe}")

    # Compare fees and delivery times
    fee_changes = compare_fees(current_data, all_scraped)
    time_changes = compare_delivery_times(current_data, delivery_times)
    changes = fee_changes + time_changes

    if verbose:
        print(f"\n{format_change_report(changes)}")

    if changes and update:
        # Update fees.json with new values
        for change in changes:
            if change.get("type") == "delivery_time":
                key = change["key"]
                if key in current_data.get("delivery_times", {}):
                    current_data["delivery_times"][key]["timeframe"] = change["new_value"]
                # Also update delivery_time in shipping items if applicable
                shipping_map = {
                    "usps_priority_express": "priority_express",
                    "state_dept_return_delivery": "return_delivery",
                }
                if key in shipping_map:
                    item_key = shipping_map[key]
                    if item_key in current_data["fees"]["shipping"]["items"]:
                        current_data["fees"]["shipping"]["items"][item_key]["delivery_time"] = change["new_value"]
            else:
                section = change["section"]
                key = change["key"]
                current_data["fees"][section]["items"][key]["amount"] = change["new_amount"]
        current_data["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        current_data["last_checked"] = datetime.now().strftime("%Y-%m-%d")
        save_fees(current_data)
        if verbose:
            print("\nfees.json has been updated with new values.")
    elif not changes:
        # Just update the check timestamp
        current_data["last_checked"] = datetime.now().strftime("%Y-%m-%d")
        save_fees(current_data)

    return changes


if __name__ == "__main__":
    update_flag = "--update" in sys.argv
    quiet_flag = "--quiet" in sys.argv

    changes = check_fees(update=update_flag, verbose=not quiet_flag)

    # Exit code: 0 = no changes, 1 = changes detected, 2 = error
    if changes:
        sys.exit(1)
    sys.exit(0)
