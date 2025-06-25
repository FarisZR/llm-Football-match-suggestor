import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
# This is useful for local development.
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# Initialize basic logging
LOG_LEVEL_STR = os.getenv('LOG_LEVEL', 'INFO').upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_STR, logging.INFO)

logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

# API Football Configuration
API_FOOTBALL_KEY = os.getenv('API_FOOTBALL_KEY')
API_FOOTBALL_URL = os.getenv('API_FOOTBALL_URL', 'https://v3.football.api-sports.io')

# CalDAV Configuration
CALDAV_URL = os.getenv('CALDAV_URL')
CALDAV_USERNAME = os.getenv('CALDAV_USERNAME')
CALDAV_PASSWORD = os.getenv('CALDAV_PASSWORD')
# Optional: Specify a calendar name if the URL doesn't include it or multiple calendars exist
CALDAV_CALENDAR_NAME = os.getenv('CALDAV_CALENDAR_NAME')


# LLM Configuration
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'openai') # Default to openai
LLM_API_KEY = os.getenv('LLM_API_KEY')
LLM_MODEL = os.getenv('LLM_MODEL') # e.g., "gpt-3.5-turbo" or "gpt-4" for OpenAI

# File Paths
# Ensure paths are absolute or relative to the project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

SYSTEM_PROMPT_FILE_PATH_STR = os.getenv('SYSTEM_PROMPT_FILE_PATH', 'system_prompt.txt')
SYSTEM_PROMPT_FILE_PATH = SYSTEM_PROMPT_FILE_PATH_STR \
    if os.path.isabs(SYSTEM_PROMPT_FILE_PATH_STR) \
    else os.path.join(PROJECT_ROOT, SYSTEM_PROMPT_FILE_PATH_STR)

BLACKLIST_FILE_PATH_STR = os.getenv('BLACKLIST_FILE_PATH', 'blacklist.json')
BLACKLIST_FILE_PATH = BLACKLIST_FILE_PATH_STR \
    if os.path.isabs(BLACKLIST_FILE_PATH_STR) \
    else os.path.join(PROJECT_ROOT, BLACKLIST_FILE_PATH_STR)


# Validation for critical configurations
CRITICAL_ENV_VARS = {
    "API_FOOTBALL_KEY": API_FOOTBALL_KEY,
    "CALDAV_URL": CALDAV_URL,
    # CALDAV_USERNAME and CALDAV_PASSWORD might not be needed if URL contains credentials
    # "LLM_API_KEY": LLM_API_KEY, # LLM might be optional or have a free tier/local model
}

missing_vars = [key for key, value in CRITICAL_ENV_VARS.items() if value is None]

if missing_vars:
    logger.warning(f"Missing critical environment variables: {', '.join(missing_vars)}. Service functionality may be limited.")

# Log loaded configuration for debugging (be careful with sensitive data in production logs)
# logger.debug(f"API_FOOTBALL_URL: {API_FOOTBALL_URL}")
# logger.debug(f"LLM_PROVIDER: {LLM_PROVIDER}")
# logger.debug(f"SYSTEM_PROMPT_FILE_PATH: {SYSTEM_PROMPT_FILE_PATH}")
# logger.debug(f"BLACKLIST_FILE_PATH: {BLACKLIST_FILE_PATH}")

# Whitelist mode configuration
WHITELIST_MODE_LEAGUE_IDS_STR = os.getenv('WHITELIST_MODE_LEAGUE_IDS', None)
WHITELIST_MODE_LEAGUE_IDS = []
if WHITELIST_MODE_LEAGUE_IDS_STR:
    try:
        WHITELIST_MODE_LEAGUE_IDS = [int(id_str.strip()) for id_str in WHITELIST_MODE_LEAGUE_IDS_STR.split(',') if id_str.strip()]
        if WHITELIST_MODE_LEAGUE_IDS:
            logger.info(f"Whitelist mode enabled. Monitoring specific league IDs: {WHITELIST_MODE_LEAGUE_IDS}")
    except ValueError:
        logger.error(f"Invalid format for WHITELIST_MODE_LEAGUE_IDS. Expected comma-separated integers. Disabling whitelist mode. Value was: '{WHITELIST_MODE_LEAGUE_IDS_STR}'")
        WHITELIST_MODE_LEAGUE_IDS = []


if not os.path.exists(SYSTEM_PROMPT_FILE_PATH):
    logger.warning(f"System prompt file not found at: {SYSTEM_PROMPT_FILE_PATH}")

if not os.path.exists(BLACKLIST_FILE_PATH):
    logger.warning(f"Blacklist file not found at: {BLACKLIST_FILE_PATH}")

# You can add more specific validation or transformation for config values here
# For example, converting a string 'True' to a boolean True, or a port number to an int.

def get_logger(name):
    """
    Returns a logger instance with the configured settings.
    """
    return logging.getLogger(name)

# Example of how other modules can get a logger
# from football_suggester.config import get_logger
# logger = get_logger(__name__)
