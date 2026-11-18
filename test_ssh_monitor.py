import unittest

from ssh_monitor import detect_bursts


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


if __name__ == "__main__":
    unittest.main()