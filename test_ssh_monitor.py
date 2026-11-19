import json
import unittest

from ssh_monitor import detect_bursts, failed_password_events


class TestDetectBursts(unittest.TestCase):
    def test_four_failures_do_not_trigger_alert(self):
        events = [
            (seconds * 1_000_000, "192.0.2.1")
            for seconds in (0, 20, 40, 60)
        ]

        alerts = list(detect_bursts(events))

        self.assertEqual(alerts, [])

    def test_fifth_failure_at_120_seconds_triggers_alert(self):
        events = [
            (seconds * 1_000_000, "192.0.2.1")
            for seconds in (0, 20, 40, 60, 120)
        ]

        alerts = list(detect_bursts(events))

        self.assertEqual(alerts, [(120_000_000, "192.0.2.1")])

    def test_fifth_failure_at_121_seconds_does_not_trigger_alert(self):
        events = [
            (seconds * 1_000_000, "192.0.2.1")
            for seconds in (0, 20, 40, 60, 121)
        ]

        alerts = list(detect_bursts(events))

        self.assertEqual(alerts, [])

    def test_failures_from_different_ips_do_not_combine(self):
        events = [
            (0, "192.0.2.1"),
            (20_000_000, "192.0.2.2"),
            (40_000_000, "192.0.2.1"),
            (60_000_000, "192.0.2.2"),
            (80_000_000, "192.0.2.1"),
        ]

        alerts = list(detect_bursts(events))

        self.assertEqual(alerts, [])

class TestFailedPasswordEvents(unittest.TestCase):
    def test_existing_user_failure_is_parsed(self):
        line = json.dumps({
            "MESSAGE": (
                "Failed password for ubuntu "
                "from 192.0.2.1 port 42000 ssh2"
            ),
            "__REALTIME_TIMESTAMP": "1000000",
        })

        events = list(failed_password_events([line]))

        self.assertEqual(events, [(1_000_000, "192.0.2.1")])

    def test_invalid_user_failure_is_parsed(self):
        line = json.dumps({
            "MESSAGE": (
                "Failed password for invalid user demo "
                "from 192.0.2.2 port 42000 ssh2"
            ),
            "__REALTIME_TIMESTAMP": "2000000",
        })

        events = list(failed_password_events([line]))

        self.assertEqual(events, [(2_000_000, "192.0.2.2")])

    def test_successful_login_is_ignored(self):
        line = json.dumps({
            "MESSAGE": (
                "Accepted password for ubuntu "
                "from 192.0.2.1 port 42000 ssh2"
            ),
            "__REALTIME_TIMESTAMP": "1000000",
        })

        events = list(failed_password_events([line]))

        self.assertEqual(events, [])

    def test_invalid_entries_are_skipped_and_parsing_continues(self):
        message = (
            "Failed password for ubuntu "
            "from 192.0.2.1 port 42000 ssh2"
        )
        lines = [
            "this is not JSON",
            json.dumps([]),
            json.dumps({"MESSAGE": None}),
            json.dumps({"MESSAGE": message}),
            json.dumps({
                "MESSAGE": message,
                "__REALTIME_TIMESTAMP": "invalid",
            }),
            json.dumps({
                "MESSAGE": (
                    "Failed password for ubuntu "
                    "from invalid-ip port 42000 ssh2"
                ),
                "__REALTIME_TIMESTAMP": "1000000",
            }),
            json.dumps({
                "MESSAGE": message,
                "__REALTIME_TIMESTAMP": "3000000",
            }),
        ]

        events = list(failed_password_events(lines))

        self.assertEqual(events, [(3_000_000, "192.0.2.1")])


if __name__ == "__main__":
    unittest.main()

    