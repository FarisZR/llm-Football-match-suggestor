import json
from football_suggester.config import get_logger, BLACKLIST_FILE_PATH

logger = get_logger(__name__)

def load_blacklist(filepath: str = None) -> dict:
    """
    Loads blacklist rules from a JSON file.

    The JSON file is expected to have keys like "league_ids" and "fixture_ids",
    each associated with a list of IDs to be blacklisted.

    Args:
        filepath (str, optional): The path to the blacklist JSON file.
            If None, uses BLACKLIST_FILE_PATH from config.

    Returns:
        dict: A dictionary containing blacklist rules (e.g., {"league_ids": [1, 2], "fixture_ids": [101, 102]}).
              Returns an empty dictionary if the file is not found or is invalid.
    """
    if filepath is None:
        filepath = BLACKLIST_FILE_PATH

    try:
        with open(filepath, 'r') as f:
            blacklist_rules = json.load(f)
            logger.info(f"Successfully loaded blacklist from {filepath}")
            # Basic validation of structure
            if not isinstance(blacklist_rules, dict):
                logger.warning(f"Blacklist file {filepath} does not contain a valid JSON object. Using empty blacklist.")
                return {}

            # Ensure expected keys are lists, convert to set for efficient lookup
            if "league_ids" in blacklist_rules and not isinstance(blacklist_rules["league_ids"], list):
                logger.warning("Invalid format for 'league_ids' in blacklist. Expected a list.")
                blacklist_rules["league_ids"] = []
            if "fixture_ids" in blacklist_rules and not isinstance(blacklist_rules["fixture_ids"], list):
                logger.warning("Invalid format for 'fixture_ids' in blacklist. Expected a list.")
                blacklist_rules["fixture_ids"] = []

            # Convert IDs to appropriate types if necessary, e.g., integers, and use sets for lookup
            processed_rules = {
                "league_ids": set(map(int, blacklist_rules.get("league_ids", []))),
                "fixture_ids": set(map(int, blacklist_rules.get("fixture_ids", [])))
            }
            return processed_rules

    except FileNotFoundError:
        logger.warning(f"Blacklist file not found at {filepath}. No blacklist will be applied.")
        return {"league_ids": set(), "fixture_ids": set()}
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from blacklist file {filepath}. No blacklist will be applied.")
        return {"league_ids": set(), "fixture_ids": set()}
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading blacklist from {filepath}: {e}")
        return {"league_ids": set(), "fixture_ids": set()}

def filter_games(games: list, blacklist_rules: dict) -> list:
    """
    Filters a list of games based on the provided blacklist rules.

    Args:
        games (list): A list of game objects (dictionaries) from the API.
                      Each game object is expected to have 'league.id' and 'fixture.id'.
        blacklist_rules (dict): A dictionary of blacklist rules, typically loaded by `load_blacklist`.
                                Example: {"league_ids": {1, 2}, "fixture_ids": {101, 102}}

    Returns:
        list: A new list containing only the games that are not blacklisted.
    """
    if not games:
        return []
    if not blacklist_rules or (not blacklist_rules.get("league_ids") and not blacklist_rules.get("fixture_ids")):
        logger.info("No blacklist rules provided or rules are empty. Returning all games.")
        return games

    blacklisted_league_ids = blacklist_rules.get("league_ids", set())
    blacklisted_fixture_ids = blacklist_rules.get("fixture_ids", set())

    filtered_games = []
    for game in games:
        try:
            league_id = game.get('league', {}).get('id')
            fixture_id = game.get('fixture', {}).get('id')

            if league_id is None or fixture_id is None:
                logger.warning(f"Game missing league_id or fixture_id, cannot apply blacklist: {game}")
                filtered_games.append(game) # Keep game if IDs are missing, or decide to drop
                continue

            # Ensure IDs from game are integers for comparison with set elements
            league_id = int(league_id)
            fixture_id = int(fixture_id)

            if league_id in blacklisted_league_ids:
                logger.debug(f"Game {fixture_id} in league {league_id} blacklisted by league ID.")
                continue

            if fixture_id in blacklisted_fixture_ids:
                logger.debug(f"Game {fixture_id} blacklisted by fixture ID.")
                continue

            filtered_games.append(game)

        except (TypeError, ValueError) as e:
            logger.warning(f"Could not process game for blacklist filtering due to invalid ID format: {game}. Error: {e}")
            # Decide whether to include or exclude such games. For now, include.
            filtered_games.append(game)
        except Exception as e:
            logger.error(f"Unexpected error while filtering game: {game}. Error: {e}")
            # Optionally, re-raise or handle more gracefully
            filtered_games.append(game) # Default to keeping the game if an unexpected error occurs

    logger.info(f"Filtered games: {len(games)} original -> {len(filtered_games)} after blacklist.")
    return filtered_games

if __name__ == '__main__':
    # Example usage for testing
    # Create dummy blacklist.json for testing
    example_blacklist_content = {
        "league_ids": [1, 78], # Example: Bundesliga (Germany), Premier League (England)
        "fixture_ids": [12345, 67890]
    }
    example_blacklist_file = "test_blacklist.json"
    with open(example_blacklist_file, 'w') as f:
        json.dump(example_blacklist_content, f)

    logger.info(f"Current BLACKLIST_FILE_PATH from config: {BLACKLIST_FILE_PATH}")

    # Test load_blacklist
    rules = load_blacklist(example_blacklist_file)
    logger.info(f"Loaded blacklist rules: {rules}")

    # Example games data (simplified structure based on api-football response)
    sample_games = [
        {"fixture": {"id": 100}, "league": {"id": 1}, "teams": {"home": {"name": "Team A"}, "away": {"name": "Team B"}}}, # Blacklisted by league
        {"fixture": {"id": 12345}, "league": {"id": 2}, "teams": {"home": {"name": "Team C"}, "away": {"name": "Team D"}}}, # Blacklisted by fixture
        {"fixture": {"id": 200}, "league": {"id": 2}, "teams": {"home": {"name": "Team E"}, "away": {"name": "Team F"}}}, # Should pass
        {"fixture": {"id": 300}, "league": {"id": 78}, "teams": {"home": {"name": "Team G"}, "away": {"name": "Team H"}}}, # Blacklisted by league
        {"fixture": {"id": 400}, "league": {"id": 90}, "teams": {"home": {"name": "Team I"}, "away": {"name": "Team J"}}}, # Should pass
        {"fixture": {"id": "abc"}, "league": {"id": "xyz"}} # Invalid game data
    ]

    # Test filter_games
    logger.info(f"\nOriginal games: {len(sample_games)}")
    for game in sample_games: logger.info(f"  Fixture ID: {game.get('fixture',{}).get('id')}, League ID: {game.get('league',{}).get('id')}")

    filtered = filter_games(sample_games, rules)
    logger.info(f"\nFiltered games: {len(filtered)}")
    for game in filtered: logger.info(f"  Fixture ID: {game.get('fixture',{}).get('id')}, League ID: {game.get('league',{}).get('id')}")

    # Test with non-existent file
    logger.info("\nTesting with non-existent blacklist file:")
    non_existent_rules = load_blacklist("non_existent_blacklist.json")
    filtered_non_existent = filter_games(sample_games, non_existent_rules)
    logger.info(f"Filtered games with non-existent blacklist: {len(filtered_non_existent)}") # Should be all games

    # Test with empty blacklist file
    with open("empty_blacklist.json", 'w') as f:
        json.dump({}, f)
    empty_rules = load_blacklist("empty_blacklist.json")
    filtered_empty = filter_games(sample_games, empty_rules)
    logger.info(f"\nFiltered games with empty blacklist: {len(filtered_empty)}")

    # Clean up dummy files
    import os
    os.remove(example_blacklist_file)
    os.remove("empty_blacklist.json")
