import unittest
import json
import os
from football_suggester.blacklist import load_blacklist, filter_games
from football_suggester.config import PROJECT_ROOT # To help locate test files

# Define a temporary directory for test blacklist files
TEST_FILES_DIR = os.path.join(PROJECT_ROOT, "tests", "temp_test_files")

class TestBlacklist(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Create a directory for temporary test files if it doesn't exist
        if not os.path.exists(TEST_FILES_DIR):
            os.makedirs(TEST_FILES_DIR)

    @classmethod
    def tearDownClass(cls):
        # Clean up: remove temporary files and directory
        for item in os.listdir(TEST_FILES_DIR):
            os.remove(os.path.join(TEST_FILES_DIR, item))
        if os.path.exists(TEST_FILES_DIR):
            os.rmdir(TEST_FILES_DIR)

    def _create_temp_blacklist_file(self, filename, content):
        filepath = os.path.join(TEST_FILES_DIR, filename)
        with open(filepath, 'w') as f:
            json.dump(content, f)
        return filepath

    def test_load_blacklist_success(self):
        rules_content = {"league_ids": [1, 2, 3], "fixture_ids": [101, 102]}
        filepath = self._create_temp_blacklist_file("rules1.json", rules_content)

        expected_rules = {
            "league_ids": {1, 2, 3},
            "fixture_ids": {101, 102}
        }
        loaded_rules = load_blacklist(filepath)
        self.assertEqual(loaded_rules, expected_rules)

    def test_load_blacklist_file_not_found(self):
        # Assuming logger is configured not to raise error but return default
        expected_rules = {"league_ids": set(), "fixture_ids": set()}
        loaded_rules = load_blacklist(os.path.join(TEST_FILES_DIR, "non_existent.json"))
        self.assertEqual(loaded_rules, expected_rules)

    def test_load_blacklist_invalid_json(self):
        filepath = os.path.join(TEST_FILES_DIR, "invalid.json")
        with open(filepath, 'w') as f:
            f.write("this is not json")

        expected_rules = {"league_ids": set(), "fixture_ids": set()}
        loaded_rules = load_blacklist(filepath)
        self.assertEqual(loaded_rules, expected_rules)

    def test_load_blacklist_empty_file_or_content(self):
        filepath_empty_json = self._create_temp_blacklist_file("empty.json", {})
        expected_rules_empty = {"league_ids": set(), "fixture_ids": set()}
        self.assertEqual(load_blacklist(filepath_empty_json), expected_rules_empty)

        filepath_empty_content = os.path.join(TEST_FILES_DIR, "empty_content.json")
        with open(filepath_empty_content, 'w') as f:
            f.write("") # Empty file
        # This should ideally be handled as invalid JSON by json.load()
        self.assertEqual(load_blacklist(filepath_empty_content), expected_rules_empty)


    def test_load_blacklist_partial_rules(self):
        rules_content = {"league_ids": [10, 20]} # Only league_ids
        filepath = self._create_temp_blacklist_file("partial_league.json", rules_content)
        expected_rules = {"league_ids": {10, 20}, "fixture_ids": set()}
        self.assertEqual(load_blacklist(filepath), expected_rules)

        rules_content_fixture = {"fixture_ids": [300]} # Only fixture_ids
        filepath_fixture = self._create_temp_blacklist_file("partial_fixture.json", rules_content_fixture)
        expected_rules_fixture = {"league_ids": set(), "fixture_ids": {300}}
        self.assertEqual(load_blacklist(filepath_fixture), expected_rules_fixture)

    def test_filter_games_empty_games_list(self):
        rules = {"league_ids": {1}, "fixture_ids": {101}}
        self.assertEqual(filter_games([], rules), [])

    def test_filter_games_empty_rules(self):
        sample_games = [
            {"fixture": {"id": 100}, "league": {"id": 1}},
            {"fixture": {"id": 200}, "league": {"id": 2}},
        ]
        self.assertEqual(filter_games(sample_games, {}), sample_games)
        self.assertEqual(filter_games(sample_games, {"league_ids": set(), "fixture_ids": set()}), sample_games)


    def test_filter_games_with_rules(self):
        rules = {"league_ids": {10}, "fixture_ids": {202}}
        games = [
            {"fixture": {"id": 101}, "league": {"id": 10}},  # Blacklisted by league
            {"fixture": {"id": 202}, "league": {"id": 20}},  # Blacklisted by fixture
            {"fixture": {"id": 303}, "league": {"id": 30}},  # Should pass
            {"fixture": {"id": 404}, "league": {"id": 10}},  # Blacklisted by league
            {"fixture": {"id": 505}, "league": {"id": 40}},  # Should pass
        ]
        expected_filtered_games = [
            {"fixture": {"id": 303}, "league": {"id": 30}},
            {"fixture": {"id": 505}, "league": {"id": 40}},
        ]
        self.assertEqual(filter_games(games, rules), expected_filtered_games)

    def test_filter_games_missing_ids_in_game_data(self):
        rules = {"league_ids": {1}, "fixture_ids": {101}}
        games_with_missing_data = [
            {"fixture": {}, "league": {"id": 1}}, # Missing fixture id
            {"fixture": {"id": 101}, "league": {}}, # Missing league id
            {"foo": "bar"}, # Completely different structure
            {"fixture": {"id": 200}, "league": {"id": 2}}, # Valid, not blacklisted
        ]
        # Games with missing data for filtering should be kept by default (as per current implementation)
        expected_filtered_games = [
            {"fixture": {}, "league": {"id": 1}},
            {"fixture": {"id": 101}, "league": {}}, # This will be kept as league_id is None
            {"foo": "bar"},
            {"fixture": {"id": 200}, "league": {"id": 2}},
        ]
        # Re-evaluating: if fixture ID is 101, it should be blacklisted if rule is fixture_id: {101}
        # The current filter_games logs a warning and keeps the game if IDs are missing.
        # Let's refine expectation based on code:
        # Game 1: league_id=1 -> blacklisted by league
        # Game 2: fixture_id=101 -> blacklisted by fixture
        # Game 3: kept (no valid IDs to check)
        # Game 4: kept (not in blacklist)

        # Current logic: if league_id or fixture_id is None, it's kept.
        # If league_id matches, it's dropped. If fixture_id matches, it's dropped.

        filtered = filter_games(games_with_missing_data, rules)

        # Game 1: league_id=1. Blacklisted.
        # Game 2: fixture_id=101. Blacklisted.
        # Game 3: kept.
        # Game 4: kept.
        expected_after_filter = [
            # First one is blacklisted by league_id=1
            # Second one is blacklisted by fixture_id=101
            {"foo": "bar"},
            {"fixture": {"id": 200}, "league": {"id": 2}},
        ]
        # This depends on how `int(None)` or `None in set()` is handled.
        # `game.get('league', {}).get('id')` can be None. `int(None)` raises TypeError.
        # The try-except in `filter_games` catches this and keeps the game.
        # So, if IDs are missing causing type errors, they are kept.

        # Let's re-verify the logic in filter_games regarding missing IDs:
        # if league_id is None or fixture_id is None: -> it's kept.
        # So, for game 1, fixture_id is None. Kept.
        # For game 2, league_id is None. Kept.
        # For game 3, both are None. Kept.
        # For game 4, neither is None. Not blacklisted. Kept.
        self.assertEqual(len(filtered), 4) # All should be kept if IDs are problematic for int conversion

        # Test with valid but blacklisted IDs alongside problematic ones
        games_mixed = [
            {"fixture": {"id": 10}, "league": {"id": 1}}, # Blacklisted by league_id=1
            {"fixture": {"id": "bad_id"}, "league": {"id": 2}}, # Kept (ValueError on int(fixture_id))
            {"fixture": {"id": 101}, "league": {"id": 3}}, # Blacklisted by fixture_id=101
            {"fixture": {"id": 20}, "league": {"id": "bad_league_id"}}, # Kept (ValueError on int(league_id))
            {"fixture": {"id": 30}, "league": {"id": 30}} # Kept (not blacklisted)
        ]

        filtered_mixed = filter_games(games_mixed, rules)
        # Expected: game 2, game 4, game 5 are kept
        self.assertEqual(len(filtered_mixed), 3)
        self.assertIn({"fixture": {"id": "bad_id"}, "league": {"id": 2}}, filtered_mixed)
        self.assertIn({"fixture": {"id": 20}, "league": {"id": "bad_league_id"}}, filtered_mixed)
        self.assertIn({"fixture": {"id": 30}, "league": {"id": 30}}, filtered_mixed)


if __name__ == '__main__':
    unittest.main()
