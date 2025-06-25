import json
import os
from football_suggester.config import get_logger, LLM_PROVIDER, LLM_API_KEY, LLM_MODEL, SYSTEM_PROMPT_FILE_PATH

logger = get_logger(__name__)

def load_system_prompt(filepath: str = None) -> str:
    """
    Loads the system prompt from a text file.

    Args:
        filepath (str, optional): The path to the system prompt file.
            If None, uses SYSTEM_PROMPT_FILE_PATH from config.

    Returns:
        str: The content of the system prompt file, or a default prompt if not found/empty.
    """
    if filepath is None:
        filepath = SYSTEM_PROMPT_FILE_PATH

    default_prompt = """You are a helpful football match suggestion assistant.
Please review the list of upcoming football matches and identify the ones that are most likely to be interesting.
Consider factors like team rivalries, importance of the match (e.g., title decider, relegation battle),
form of the teams, and historical significance.
Return your answer as a comma-separated list of fixture IDs. For example: 123,456,789
Do not include any other text or explanation.
"""
    try:
        with open(filepath, 'r') as f:
            prompt = f.read().strip()
        if not prompt:
            logger.warning(f"System prompt file at {filepath} is empty. Using default prompt.")
            return default_prompt
        logger.info(f"Successfully loaded system prompt from {filepath}")
        return prompt
    except FileNotFoundError:
        logger.warning(f"System prompt file not found at {filepath}. Using default prompt.")
        return default_prompt
    except Exception as e:
        logger.error(f"An error occurred while loading system prompt from {filepath}: {e}. Using default prompt.")
        return default_prompt

def _prepare_games_for_llm(games: list) -> str:
    """
    Prepares a simplified string representation of games for the LLM.
    Includes essential information like fixture ID, teams, league, and date.
    """
    game_details_list = []
    for game in games:
        fixture = game.get('fixture', {})
        league = game.get('league', {})
        teams = game.get('teams', {})
        home_team = teams.get('home', {}).get('name', 'N/A')
        away_team = teams.get('away', {}).get('name', 'N/A')

        detail = (
            f"Fixture ID: {fixture.get('id')}, "
            f"Date: {fixture.get('date', 'N/A')[:10]}, " # Just the date part
            f"League: {league.get('name', 'N/A')} (ID: {league.get('id')}), "
            f"Match: {home_team} vs {away_team}"
        )
        game_details_list.append(detail)

    if not game_details_list:
        return "No games available to analyze."

    return "\n".join(game_details_list)

def get_interesting_games(games: list, system_prompt: str = None) -> list[int]:
    """
    Sends a list of games to an LLM and gets a list of fixture IDs deemed interesting.

    Args:
        games (list): A list of game objects (dictionaries) from the API client,
                      filtered by the blacklist.
        system_prompt (str, optional): The system prompt to guide the LLM.
                                       If None, loads from the configured file.

    Returns:
        list[int]: A list of integer fixture IDs suggested by the LLM.
                   Returns an empty list if an error occurs, no games provided,
                   or LLM configuration is missing.
    """
    if not games:
        logger.info("No games provided to LLM handler.")
        return []

    if not LLM_API_KEY:
        logger.error(f"LLM_API_KEY for provider '{LLM_PROVIDER}' is not configured. Cannot get suggestions.")
        return []

    if not LLM_MODEL:
        logger.error(f"LLM_MODEL for provider '{LLM_PROVIDER}' is not configured. Cannot get suggestions.")
        return []

    if system_prompt is None:
        system_prompt = load_system_prompt()

    games_representation = _prepare_games_for_llm(games)
    user_prompt = f"Here is a list of upcoming football matches:\n{games_representation}\n\nPlease identify the interesting ones based on the criteria you've been given."

    if LLM_PROVIDER.lower() == 'openai':
        try:
            # Ensure openai library is available
            import openai
            client = openai.OpenAI(api_key=LLM_API_KEY)

            logger.info(f"Sending {len(games)} games to OpenAI model {LLM_MODEL} for suggestions.")
            # logger.debug(f"System Prompt: {system_prompt}")
            # logger.debug(f"User Prompt: {user_prompt}")

            chat_completion = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5, # Adjust for creativity vs. determinism
            )

            response_content = chat_completion.choices[0].message.content
            logger.info(f"LLM response received: {response_content}")

            if not response_content:
                logger.warning("LLM returned an empty response.")
                return []

            # Parse the response: expecting comma-separated fixture IDs
            suggested_ids_str = response_content.strip().split(',')
            suggested_ids = []
            for id_str in suggested_ids_str:
                try:
                    suggested_ids.append(int(id_str.strip()))
                except ValueError:
                    logger.warning(f"LLM returned a non-integer ID: '{id_str.strip()}'. Skipping.")

            logger.info(f"LLM suggested {len(suggested_ids)} games as interesting.")
            return suggested_ids

        except ImportError:
            logger.error("OpenAI library is not installed. Please install it: pip install openai")
            return []
        except Exception as e:
            logger.error(f"Error interacting with OpenAI API: {e}")
            if hasattr(e, 'response') and e.response:
                 logger.error(f"OpenAI API Response: {e.response.text}")
            return []

    # Placeholder for other LLM providers
    # elif LLM_PROVIDER.lower() == 'anthropic':
    #     logger.error("Anthropic LLM provider not yet implemented.")
    #     return []
    else:
        logger.error(f"Unsupported LLM provider: {LLM_PROVIDER}. Supported providers: 'openai'.")
        return []

if __name__ == '__main__':
    # This is for basic testing of the module.
    # Ensure your .env file is populated with LLM_API_KEY and LLM_MODEL.
    from football_suggester.config import load_dotenv, PROJECT_ROOT, logger as cfg_logger

    dotenv_path_for_test = os.path.join(PROJECT_ROOT, '.env')
    if os.path.exists(dotenv_path_for_test):
        load_dotenv(dotenv_path_for_test)
        # Re-evaluate necessary config vars if they were None
        LLM_API_KEY = os.getenv('LLM_API_KEY')
        LLM_MODEL = os.getenv('LLM_MODEL')
        SYSTEM_PROMPT_FILE_PATH = os.path.join(PROJECT_ROOT, os.getenv('SYSTEM_PROMPT_FILE_PATH', 'system_prompt.txt'))
        cfg_logger.info(f"Reloaded .env for llm_handler test. System prompt path: {SYSTEM_PROMPT_FILE_PATH}")


    # Create a dummy system_prompt.txt if it doesn't exist for testing
    if not os.path.exists(SYSTEM_PROMPT_FILE_PATH):
        cfg_logger.info(f"Creating dummy system prompt at {SYSTEM_PROMPT_FILE_PATH} for testing.")
        with open(SYSTEM_PROMPT_FILE_PATH, 'w') as f:
            f.write(load_system_prompt()) # Writes default prompt

    # Sample games data (as if from api_client and filtered by blacklist)
    sample_games_for_llm = [
        {"fixture": {"id": 78901, "date": "2023-12-01T20:00:00+00:00"}, "league": {"id": 39, "name": "Premier League"}, "teams": {"home": {"name": "Manchester United"}, "away": {"name": "Chelsea"}}},
        {"fixture": {"id": 78902, "date": "2023-12-01T15:00:00+00:00"}, "league": {"id": 135, "name": "Serie A"}, "teams": {"home": {"name": "Juventus"}, "away": {"name": "Inter Milan"}}},
        {"fixture": {"id": 78903, "date": "2023-12-02T17:30:00+00:00"}, "league": {"id": 78, "name": "Bundesliga"}, "teams": {"home": {"name": "Bayern Munich"}, "away": {"name": "Borussia Dortmund"}}},
        {"fixture": {"id": 11111, "date": "2023-12-03T12:00:00+00:00"}, "league": {"id": 61, "name": "Ligue 1"}, "teams": {"home": {"name": "Paris Saint-Germain"}, "away": {"name": "Olympique Marseille"}}},
        {"fixture": {"id": 22222, "date": "2023-12-03T19:45:00+00:00"}, "league": {"id": 140, "name": "La Liga"}, "teams": {"home": {"name": "FC Barcelona"}, "away": {"name": "Real Madrid"}}},
        {"fixture": {"id": 33333, "date": "2023-12-04T14:00:00+00:00"}, "league": {"id": 88, "name": "Eredivisie"}, "teams": {"home": {"name": "Ajax"}, "away": {"name": "Feyenoord"}}},
        {"fixture": {"id": 44444, "date": "2023-12-05T18:00:00+00:00"}, "league": {"id": 203, "name": " Brasileiro Série A"}, "teams": {"home": {"name": "Flamengo"}, "away": {"name": "Palmeiras"}}},
        {"fixture": {"id": 55555, "date": "2023-12-06T16:00:00+00:00"}, "league": {"id": 253, "name": "MLS"}, "teams": {"home": {"name": "LA Galaxy"}, "away": {"name": "LAFC"}}},
        {"fixture": {"id": 66666, "date": "2023-12-07T20:00:00+00:00"}, "league": {"id": 10, "name": "CAF Champions League"}, "teams": {"home": {"name": "Al Ahly"}, "away": {"name": "Esperance Tunis"}}},
        {"fixture": {"id": 99999, "date": "2023-12-10T15:00:00+00:00"}, "league": {"id": 529, "name": "Super League"}, "teams": {"home": {"name": "Lowly United"}, "away": {"name": "Bottom FC"}}}, # Less interesting game
    ]

    if not LLM_API_KEY or not LLM_MODEL:
        cfg_logger.warning("LLM_API_KEY or LLM_MODEL not set in .env. Skipping live LLM test.")
    else:
        cfg_logger.info(f"\nTesting LLM integration with {LLM_PROVIDER} model {LLM_MODEL}...")
        # Load specific system prompt for testing if needed, or use default
        # test_system_prompt = "You are a test LLM. From the list, pick fixtures with IDs 78901 and 22222. Return as 78901,22222."
        # suggested_fixture_ids = get_interesting_games(sample_games_for_llm, system_prompt=test_system_prompt)

        suggested_fixture_ids = get_interesting_games(sample_games_for_llm)

        if suggested_fixture_ids:
            cfg_logger.info(f"LLM suggested the following fixture IDs: {suggested_fixture_ids}")
            # Verify these IDs are present in the original sample_games_for_llm
            original_ids = {g['fixture']['id'] for g in sample_games_for_llm}
            for sid in suggested_fixture_ids:
                if sid not in original_ids:
                    cfg_logger.warning(f"LLM suggested an ID not in the original list: {sid}")
        else:
            cfg_logger.info("LLM did not suggest any games or an error occurred.")

    cfg_logger.info("\nTesting with no games:")
    no_games_result = get_interesting_games([])
    cfg_logger.info(f"Result for no games: {no_games_result}")

    # Clean up dummy system_prompt.txt if it was created by this test script
    # This is tricky because config.py might also warn about it.
    # For now, leave it, or rely on user creating their own.
    # if os.path.exists(SYSTEM_PROMPT_FILE_PATH) and "dummy system prompt" in open(SYSTEM_PROMPT_FILE_PATH).read():
    #     os.remove(SYSTEM_PROMPT_FILE_PATH)
    #     cfg_logger.info(f"Removed dummy system prompt file: {SYSTEM_PROMPT_FILE_PATH}")

    cfg_logger.info("LLM handler test finished.")
