import unittest
import os
from unittest import mock
import importlib
# Import config initially to have a reference, but it will be reloaded in tests
from football_suggester import config as initial_config_module

class TestConfigLoading(unittest.TestCase):

    def tearDown(self):
        # Ensure config is reloaded to its original state after each test
        # This is important if tests modify os.environ and then reload config
        # A bit of a blunt instrument, but helps isolate tests.
        # This assumes the initial import captured a "default" state or that
        # subsequent tests will also manage their own environment for config.
        importlib.reload(initial_config_module)

    @mock.patch.dict(os.environ, {}, clear=True)
    def test_whitelist_mode_league_ids_not_set(self):
        # Ensure the key is not in environ for this test
        if 'WHITELIST_MODE_LEAGUE_IDS' in os.environ:
             del os.environ['WHITELIST_MODE_LEAGUE_IDS'] # Should be handled by clear=True but defensive

        reloaded_config = importlib.reload(initial_config_module)
        self.assertEqual(reloaded_config.WHITELIST_MODE_LEAGUE_IDS, [])

    @mock.patch.dict(os.environ, {'WHITELIST_MODE_LEAGUE_IDS': ""}, clear=True)
    def test_whitelist_mode_league_ids_empty_string(self):
        reloaded_config = importlib.reload(initial_config_module)
        self.assertEqual(reloaded_config.WHITELIST_MODE_LEAGUE_IDS, [])

    @mock.patch.dict(os.environ, {'WHITELIST_MODE_LEAGUE_IDS': "39"}, clear=True)
    def test_whitelist_mode_league_ids_valid_single(self):
        reloaded_config = importlib.reload(initial_config_module)
        self.assertEqual(reloaded_config.WHITELIST_MODE_LEAGUE_IDS, [39])

    @mock.patch.dict(os.environ, {'WHITELIST_MODE_LEAGUE_IDS': "39,140, 78"}, clear=True) # Note the space
    def test_whitelist_mode_league_ids_valid_multiple_with_spaces(self):
        reloaded_config = importlib.reload(initial_config_module)
        self.assertEqual(reloaded_config.WHITELIST_MODE_LEAGUE_IDS, [39, 140, 78])

    @mock.patch.dict(os.environ, {'WHITELIST_MODE_LEAGUE_IDS': "39,,140, ,78,"}, clear=True) # Empty parts, trailing comma
    def test_whitelist_mode_league_ids_valid_with_empty_parts_and_trailing_comma(self):
        reloaded_config = importlib.reload(initial_config_module)
        self.assertEqual(reloaded_config.WHITELIST_MODE_LEAGUE_IDS, [39, 140, 78])

    @mock.patch.dict(os.environ, {'WHITELIST_MODE_LEAGUE_IDS': "39,abc,78"}, clear=True) # Non-integer value
    def test_whitelist_mode_league_ids_invalid_non_integer(self):
        # Expect it to log an error and default to an empty list
        with self.assertLogs(level='ERROR') as log_watcher:
            reloaded_config = importlib.reload(initial_config_module)
            self.assertEqual(reloaded_config.WHITELIST_MODE_LEAGUE_IDS, [])

        found_error_log = False
        for record in log_watcher.records:
            if "Invalid format for WHITELIST_MODE_LEAGUE_IDS" in record.getMessage():
                found_error_log = True
                break
        self.assertTrue(found_error_log, "Expected error log for invalid format not found.")

    @mock.patch.dict(os.environ, {'WHITELIST_MODE_LEAGUE_IDS': "  "}, clear=True) # Only spaces
    def test_whitelist_mode_league_ids_only_spaces(self):
        reloaded_config = importlib.reload(initial_config_module)
        self.assertEqual(reloaded_config.WHITELIST_MODE_LEAGUE_IDS, [])

    # Example test for another config variable to show the pattern
    @mock.patch.dict(os.environ, {'LOG_LEVEL': "DEBUG"}, clear=True)
    def test_log_level_loading(self):
        import logging
        reloaded_config = importlib.reload(initial_config_module)
        # This tests the LOG_LEVEL variable itself, not the direct effect on the logger immediately
        # as basicConfig might have already run. A more thorough test would check logger's effective level.
        self.assertEqual(reloaded_config.LOG_LEVEL_STR, "DEBUG")
        self.assertEqual(reloaded_config.LOG_LEVEL, logging.DEBUG)


if __name__ == '__main__':
    unittest.main()
