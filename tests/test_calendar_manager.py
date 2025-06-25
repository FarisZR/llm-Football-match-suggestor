import unittest
from datetime import datetime, timezone, timedelta
from football_suggester.calendar_manager import _generate_event_uid, _format_datetime_for_caldav

class TestCalendarManagerHelpers(unittest.TestCase):

    def test_generate_event_uid(self):
        fixture_id = 12345
        expected_uid_suffix = f"-fixture-{fixture_id}@my-domain.com"
        generated_uid = _generate_event_uid(fixture_id)
        self.assertTrue(generated_uid.startswith("football-suggester"))
        self.assertTrue(generated_uid.endswith(expected_uid_suffix))

    def test_format_datetime_for_caldav_utc(self):
        # ISO format with Z for UTC
        dt_str_zulu = "2023-10-26T10:30:00Z"
        expected_caldav_format = "20231026T103000Z"
        self.assertEqual(_format_datetime_for_caldav(dt_str_zulu), expected_caldav_format)

        # ISO format with +00:00 for UTC
        dt_str_offset = "2023-10-26T10:30:00+00:00"
        self.assertEqual(_format_datetime_for_caldav(dt_str_offset), expected_caldav_format)

    def test_format_datetime_for_caldav_with_timezone_conversion(self):
        # Non-UTC timezone, should be converted to UTC
        # Example: Europe/Berlin is UTC+2 during summer time (CEST)
        # For simplicity, let's use a fixed offset that's not UTC
        dt_str_cest = "2023-08-15T12:00:00+02:00" # Noon CEST
        expected_caldav_format_utc = "20230815T100000Z" # 10 AM UTC
        self.assertEqual(_format_datetime_for_caldav(dt_str_cest), expected_caldav_format_utc)

        dt_str_est = "2023-11-10T14:00:00-05:00" # 2 PM EST (UTC-5)
        expected_caldav_format_utc_est = "20231110T190000Z" # 7 PM UTC
        self.assertEqual(_format_datetime_for_caldav(dt_str_est), expected_caldav_format_utc_est)

    def test_format_datetime_for_caldav_naive_datetime(self):
        # Naive datetime string (no timezone info) - should be assumed UTC by the formatter as a fallback
        # The current implementation of _format_datetime_for_caldav:
        # dt_obj = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        # if dt_obj.tzinfo is None: dt_obj = dt_obj.replace(tzinfo=timezone.utc)
        # This means it will treat naive as UTC.
        dt_str_naive = "2023-12-25T08:00:00"
        expected_caldav_format_naive_as_utc = "20231225T080000Z"
        self.assertEqual(_format_datetime_for_caldav(dt_str_naive), expected_caldav_format_naive_as_utc)


    def test_format_datetime_for_caldav_invalid_string(self):
        # Test with an invalid date string
        # The function currently logs an error and returns current time as fallback.
        invalid_dt_str = "not a date"
        # We can't easily assert the exact fallback time, but we can check format.
        fallback_output = _format_datetime_for_caldav(invalid_dt_str)

        # Check if it's a valid CalDAV UTC datetime string format
        self.assertEqual(len(fallback_output), 16) # YYYYMMDDTHHMMSSZ
        self.assertTrue(fallback_output.endswith("Z"))
        try:
            datetime.strptime(fallback_output, "%Y%m%dT%H%M%SZ")
        except ValueError:
            self.fail("Fallback output is not in the expected CalDAV UTC format.")

if __name__ == '__main__':
    unittest.main()
