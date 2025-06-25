import unittest
import os
from football_suggester.llm_handler import load_system_prompt, _prepare_games_for_llm
from football_suggester.config import PROJECT_ROOT

TEST_FILES_DIR = os.path.join(PROJECT_ROOT, "tests", "temp_test_files")

class TestLLMHandler(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(TEST_FILES_DIR):
            os.makedirs(TEST_FILES_DIR)

    @classmethod
    def tearDownClass(cls):
        for item in os.listdir(TEST_FILES_DIR):
            os.remove(os.path.join(TEST_FILES_DIR, item))
        if os.path.exists(TEST_FILES_DIR):
            os.rmdir(TEST_FILES_DIR)

    def _create_temp_prompt_file(self, filename, content):
        filepath = os.path.join(TEST_FILES_DIR, filename)
        with open(filepath, 'w') as f:
            f.write(content)
        return filepath

    def test_load_system_prompt_success(self):
        prompt_content = "This is a test system prompt."
        filepath = self._create_temp_prompt_file("prompt1.txt", prompt_content)

        loaded_prompt = load_system_prompt(filepath)
        self.assertEqual(loaded_prompt, prompt_content)

    def test_load_system_prompt_file_not_found(self):
        # Expect default prompt
        default_prompt_start = "You are a helpful football match suggestion assistant."
        loaded_prompt = load_system_prompt(os.path.join(TEST_FILES_DIR,"non_existent_prompt.txt"))
        self.assertTrue(loaded_prompt.startswith(default_prompt_start))

    def test_load_system_prompt_empty_file(self):
        filepath = self._create_temp_prompt_file("empty_prompt.txt", "")
        default_prompt_start = "You are a helpful football match suggestion assistant."
        loaded_prompt = load_system_prompt(filepath)
        self.assertTrue(loaded_prompt.startswith(default_prompt_start))

    def test_prepare_games_for_llm_empty_list(self):
        self.assertEqual(_prepare_games_for_llm([]), "No games available to analyze.")

    def test_prepare_games_for_llm_structure(self):
        sample_games = [
            {"fixture": {"id": 78901, "date": "2023-12-01T20:00:00+00:00"}, "league": {"id": 39, "name": "Premier League"}, "teams": {"home": {"name": "Man Utd"}, "away": {"name": "Chelsea"}}},
            {"fixture": {"id": 78902, "date": "2023-12-02T15:00:00+00:00"}, "league": {"id": 135, "name": "Serie A"}, "teams": {"home": {"name": "Juventus"}, "away": {"name": "Inter"}}},
        ]

        expected_output_game1 = "Fixture ID: 78901, Date: 2023-12-01, League: Premier League (ID: 39), Match: Man Utd vs Chelsea"
        expected_output_game2 = "Fixture ID: 78902, Date: 2023-12-02, League: Serie A (ID: 135), Match: Juventus vs Inter"

        prepared_string = _prepare_games_for_llm(sample_games)

        self.assertIn(expected_output_game1, prepared_string)
        self.assertIn(expected_output_game2, prepared_string)
        self.assertEqual(prepared_string.count('\n'), len(sample_games) - 1) # N-1 newlines for N games

    def test_prepare_games_for_llm_missing_data(self):
        sample_games_missing_data = [
            {"fixture": {"id": 123}, "league": {}, "teams": {}}, # Missing names, date
        ]
        # Expected: uses 'N/A' for missing fields
        expected_output = "Fixture ID: 123, Date: N/A, League: N/A (ID: None), Match: N/A vs N/A"
        prepared_string = _prepare_games_for_llm(sample_games_missing_data)
        self.assertEqual(prepared_string, expected_output)


if __name__ == '__main__':
    unittest.main()
