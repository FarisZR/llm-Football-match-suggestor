import requests
import datetime
from football_suggester.config import get_logger, API_FOOTBALL_KEY, API_FOOTBALL_URL

logger = get_logger(__name__)

def fetch_upcoming_games(days_ahead: int = 7, league_id: str = None, season: str = None) -> list:
    """
    Fetches upcoming football games from the api-football.com service.

    Args:
        days_ahead (int): Number of days from today to fetch fixtures for. Defaults to 7.
        league_id (str, optional): Specific league ID to fetch games for.
        season (str, optional): The season year (e.g., "2023"). Required if league_id is provided.

    Returns:
        list: A list of fixture objects (dictionaries) from the API response,
              or an empty list if an error occurs or no games are found.
    """
    if not API_FOOTBALL_KEY:
        logger.error("API_FOOTBALL_KEY is not configured. Cannot fetch games.")
        return []

    if not API_FOOTBALL_URL:
        logger.error("API_FOOTBALL_URL is not configured. Cannot fetch games.")
        return []

    today = datetime.date.today()
    end_date = today + datetime.timedelta(days=days_ahead)

    params = {
        "date_from": today.strftime("%Y-%m-%d"),
        "date_to": end_date.strftime("%Y-%m-%d"),
        # "status": "NS" # Not Started games
    }

    # The API seems to prefer 'date' for a single day, or 'from'/'to' for a range.
    # Let's adjust to use 'from' and 'to' as per their docs for date ranges,
    # or just 'date' if we wanted a single day.
    # For upcoming, we'll use 'live' with 'all' to get NS, and filter later, or specify date range.
    # The API endpoint for fixtures with date range:
    # https://v3.football.api-sports.io/fixtures?date=YYYY-MM-DD (single day)
    # https://v3.football.api-sports.io/fixtures?from=YYYY-MM-DD&to=YYYY-MM-DD (date range)
    # Let's stick to date range.

    # The API uses 'from' and 'to' for date ranges with /fixtures endpoint.
    # It seems my initial thought on params was slightly off.
    # Correcting based on typical API patterns and api-football docs.
    # The API uses 'date' for a single day, or 'from' and 'to' for a range for some things,
    # but for general fixtures, it's often by 'date', 'league'/'season', or 'live'.
    # Let's use the 'date' parameter for each day in the range to ensure we get all games.
    # Or, more efficiently, use from/to if the API supports it well for fixtures.
    # The documentation suggests /fixtures can take 'date', 'season', 'league', 'live', 'next', 'last'.
    # 'next=<number_of_fixtures>' or 'last=<number_of_fixtures>' might be simpler.
    # However, to control the date range precisely, iterating or using from/to is better.
    # The example at https://www.api-football.com/documentation-v3#tag/Fixtures/operation/get-fixtures
    # shows `date`, `league`, `season`.
    # If we want a range, we might need to make multiple calls or find a better parameter.
    # The API docs state: "The Paging is not available for this endpoint. (fixtures with date)"
    # "To retrieve all fixtures for a date range, you will need to make a request for each date."
    # This is inefficient. Let's check if 'live' or 'status' can help.
    # "status : fixture status ( Check Fixture Status )" -> NS (Not Started)

    # Let's try with "season" and "league" if provided, otherwise fetch broadly by date range.
    # If fetching broadly, we might hit limits or get too much data.
    # A common pattern for "upcoming" is to specify a `status=NS` (Not Started).

    current_params = {
        "from": today.strftime("%Y-%m-%d"),
        "to": end_date.strftime("%Y-%m-%d"),
        "status": "NS" # Not Started
    }

    if league_id:
        if not season:
            logger.warning("Season must be provided if league_id is specified. Fetching without league filter.")
        else:
            current_params["league"] = str(league_id)
            current_params["season"] = str(season)
            # If league and season are specified, 'from' and 'to' might not be needed or work the same way.
            # The API usually expects either date-based or league/season based queries for fixtures.
            # Let's assume for league/season, we want all 'NS' games in that league/season.
            # We might remove 'from' and 'to' if 'league' and 'season' are primary.
            # Documentation: "You can combine with status parameter."
            # "If you use the league and season parameters you will have all the fixtures of the season."
            # So, if league and season are given, we get all NS for that season.
            # If we also want to limit by date, the 'from'/'to' should still apply.
            logger.info(f"Fetching upcoming games for league {league_id}, season {season} from {current_params['from']} to {current_params['to']}.")


    headers = {
        'x-rapidapi-host': API_FOOTBALL_URL.replace('https://', ''), # Host without schema
        'x-rapidapi-key': API_FOOTBALL_KEY
    }

    endpoint = f"{API_FOOTBALL_URL}/fixtures"
    all_fixtures = []

    try:
        logger.info(f"Fetching upcoming games from {endpoint} with params: {current_params}")
        response = requests.get(endpoint, headers=headers, params=current_params, timeout=20)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)

        data = response.json()

        if data.get("response"):
            all_fixtures = data["response"]
            logger.info(f"Successfully fetched {len(all_fixtures)} fixtures.")

            # Handle paging if it exists and is needed - though docs say not for date range.
            # For league/season queries, paging might apply.
            # The 'paging' object in the response: { "current": 1, "total": 1 }
            # If data['paging']['total'] > data['paging']['current'], we'd need more requests.
            # For now, assuming one page is enough or paging is handled by date range.
            # If league/season is used, paging is important.
            current_page = data.get("paging", {}).get("current", 1)
            total_pages = data.get("paging", {}).get("total", 1)

            while current_page < total_pages:
                current_page += 1
                logger.info(f"Fetching page {current_page}/{total_pages} for the same query.")
                current_params["page"] = current_page
                response = requests.get(endpoint, headers=headers, params=current_params, timeout=20)
                response.raise_for_status()
                data = response.json()
                if data.get("response"):
                    all_fixtures.extend(data["response"])
                    logger.info(f"Added {len(data['response'])} fixtures from page {current_page}. Total: {len(all_fixtures)}")
                else:
                    logger.warning(f"No 'response' field in page {current_page} data: {data.get('errors') or data}")
                    break # Stop if a page is empty or error occurs

        else:
            errors = data.get('errors')
            if isinstance(errors, dict) and any(errors.values()): # errors can be a dict like {"token": "missing"} or list
                 logger.error(f"API error when fetching games: {errors}")
            elif isinstance(errors, list) and errors:
                 logger.error(f"API error when fetching games: {', '.join(errors)}")
            else:
                logger.warning(f"No games found or unexpected API response structure: {data}")
            return []

    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err} - Response: {http_err.response.text}")
        return []
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Request error occurred: {req_err}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return []

    return all_fixtures

if __name__ == '__main__':
    # This is for basic testing of the module.
    # Ensure your .env file is populated or environment variables are set.
    from football_suggester.config import load_dotenv, PROJECT_ROOT, logger as cfg_logger
    import os

    # Load .env from project root for direct script execution
    dotenv_path_for_test = os.path.join(PROJECT_ROOT, '.env')
    if os.path.exists(dotenv_path_for_test):
        load_dotenv(dotenv_path_for_test)
        # Re-evaluate API_FOOTBALL_KEY and URL after loading .env if they were initially None
        API_FOOTBALL_KEY = os.getenv('API_FOOTBALL_KEY')
        API_FOOTBALL_URL = os.getenv('API_FOOTBALL_URL', 'https://v3.football.api-sports.io')
        cfg_logger.info("Reloaded .env for direct script test.")

    if not API_FOOTBALL_KEY:
        cfg_logger.error("API_FOOTBALL_KEY is not set. Please set it in your .env file or environment.")
    else:
        cfg_logger.info("Fetching all upcoming games for the next 3 days...")
        games = fetch_upcoming_games(days_ahead=3)
        if games:
            cfg_logger.info(f"Found {len(games)} games.")
            # for game in games[:5]: # Print details of first 5 games
            #     fixture = game.get('fixture', {})
            #     league = game.get('league', {})
            #     teams = game.get('teams', {})
            #     cfg_logger.info(
            #         f"ID: {fixture.get('id')}, Date: {fixture.get('date')}, "
            #         f"League: {league.get('name')} (ID: {league.get('id')}), "
            #         f"Match: {teams.get('home', {}).get('name')} vs {teams.get('away', {}).get('name')}"
            #     )
        else:
            cfg_logger.info("No games found or an error occurred.")

        # Example: Fetching for a specific league (e.g., Premier League ID 39, Season 2023)
        # cfg_logger.info("\nFetching Premier League (ID 39) games for season 2023 in the next 30 days...")
        # premier_league_games = fetch_upcoming_games(days_ahead=30, league_id="39", season="2023")
        # if premier_league_games:
        #     cfg_logger.info(f"Found {len(premier_league_games)} Premier League games.")
        #     # for game in premier_league_games[:5]:
        #     #     fixture = game.get('fixture', {})
        #     #     league = game.get('league', {})
        #     #     teams = game.get('teams', {})
        #     #     cfg_logger.info(
        #     #         f"ID: {fixture.get('id')}, Date: {fixture.get('date')}, "
        #     #         f"League: {league.get('name')}, "
        #     #         f"Match: {teams.get('home', {}).get('name')} vs {teams.get('away', {}).get('name')}"
        #     #     )
        # else:
        #     cfg_logger.info("No Premier League games found or an error occurred.")
