#!/usr/bin/env python3 

"""Check the logs for repeated failed SSH logins from the same IP address"""

import json
import re
import sys
import argparse
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address


THRESHOLD = 5
WINDOW_SECONDS = 120
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
FAILED_PASSWORD = re.compile(r"^Failed password .+? from (\S+) port \d+\b")

def failed_password_events(lines):
    for line in lines:
        try:
            entry = json.loads(line)
            if not isinstance(entry, dict):
                continue
            message = entry.get("MESSAGE")
            if not isinstance(message, str):
                continue
            match = FAILED_PASSWORD.match(message)
            if match:
                timestamp = int(entry["__REALTIME_TIMESTAMP"])
                yield timestamp, str(ip_address(match.group(1)))
        except (KeyError, TypeError, ValueError):
            continue


def detect_bursts(events):
    """Flag an IP address when it reaches 5 failed ssh attempts within 2 minutes"""
    recent_by_ip = defaultdict(deque)
    window_microseconds = WINDOW_SECONDS * 1_000_000

    for timestamp, source_ip in sorted(events):
        recent = recent_by_ip[source_ip]
        while recent and timestamp - recent[0] > window_microseconds:
            recent.popleft()
        recent.append(timestamp)

        if len(recent) == THRESHOLD:
            yield timestamp, source_ip


def demo_lines():
    start = 1_790_000_000_000_000
    events = [(seconds, "203.0.113.10") for seconds in (0, 20, 40, 60, 80)]
    events.append((30, "198.51.100.20"))
    for seconds, source_ip in sorted(events):
        yield json.dumps({
            "MESSAGE": f"Failed password for invalid user demo from {source_ip} port 42000 ssh2",
            "__REALTIME_TIMESTAMP": str(start + seconds * 1_000_000),
        })

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="use built-in synthetic logs")
    args = parser.parse_args()
    if not args.demo and sys.stdin.isatty():
        parser.error("use --demo or pipe journalctl JSON output into this script")


    lines = demo_lines() if args.demo else sys.stdin
    events = list(failed_password_events(lines))
    alerted = set()
    for timestamp, source_ip in detect_bursts(events):
        if source_ip in alerted:
            continue
        alerted.add(source_ip)
        time_utc = EPOCH + timedelta(microseconds=timestamp)
        print(
            f"ALERT {source_ip} at {time_utc.isoformat()} "
            f"({THRESHOLD} failed SSH passwords within {WINDOW_SECONDS} seconds)"
        )
    print(f"Analysed {len(events)} matching password failures. Sources alerted: {len(alerted)}.")

if __name__ == "__main__":
    main()