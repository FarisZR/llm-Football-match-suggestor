# Football Match Suggester

This service uses AI to suggest interesting football (soccer) matches based on user-defined criteria. It fetches upcoming games from api-football.com, filters them based on a blacklist and user preferences (via an LLM), and then adds the suggested matches to a CalDAV calendar.

## Features

- Fetches upcoming football matches from api-football.com.
- Allows blacklisting of specific leagues or games.
- Uses a Large Language Model (LLM) to identify "interesting" matches based on a customizable system prompt.
- Adds suggested matches as events to a CalDAV-compatible calendar.
- Runnable as a Docker container.

## Prerequisites

- Docker
- Access to api-football.com (API key required)
- Access to an LLM provider (e.g., OpenAI API key required)
- A CalDAV server and credentials

## Configuration

The service is configured via environment variables. You can set these directly or use a `.env` file in the project root (this file is gitignored by default). Create a `.env` file by copying `.env.example` and filling in your values.

**Required environment variables** (see `.env.example` for more details and defaults):

- `API_FOOTBALL_KEY`: Your API key for api-football.com.
- `CALDAV_URL`: The URL of your CalDAV server.
- `CALDAV_USERNAME`: Your CalDAV username (required if not in URL and server needs auth).
- `CALDAV_PASSWORD`: Your CalDAV password (required if not in URL and server needs auth).
- `LLM_PROVIDER`: The LLM provider to use (default: `openai`).
- `LLM_API_KEY`: Your API key for the chosen LLM provider.
- `LLM_MODEL`: The specific model to use (e.g., `gpt-3.5-turbo`, `gpt-4`).

**Optional environment variables:**

- `API_FOOTBALL_URL`: Override the default api-football base URL.
- `CALDAV_CALENDAR_NAME`: Specific name of the calendar to use on the CalDAV server if it cannot be auto-detected or you want a specific one.
- `SYSTEM_PROMPT_FILE_PATH`: Path to the system prompt file (default: `system_prompt.txt` in the project root).
- `BLACKLIST_FILE_PATH`: Path to the blacklist file (default: `blacklist.json` in the project root).
- `LOG_LEVEL`: Logging level (e.g., `INFO`, `DEBUG`, `WARNING`, `ERROR`. Default: `INFO`).
- `FETCH_DAYS_AHEAD`: How many days ahead to fetch games for (default: `7`).
- `TARGET_LEAGUE_ID`: Specific league ID to fetch games from (e.g., Premier League `39`). If set, `TARGET_SEASON` is also required.
- `TARGET_SEASON`: Season year (e.g., `2023` for the 2023-2024 season) - required if `TARGET_LEAGUE_ID` is set.

### Blacklist File Format (`blacklist.json` or path from `BLACKLIST_FILE_PATH`)

The blacklist file should be a JSON file. See `blacklist.example.json` for the format and examples.
Content example:
```json
{
  "league_ids": [123, 456],
  "fixture_ids": [789012, 345678]
}
```

### System Prompt File (`system_prompt.txt` or path from `SYSTEM_PROMPT_FILE_PATH`)

A plain text file containing instructions for the LLM. See `system_prompt.example.txt` for a detailed example of how to guide the LLM.

## Running with Docker

1.  **Build the Docker image:**
    ```bash
    docker build -t football-suggester .
    ```

2.  **Prepare your configuration:**
    *   Create a `.env` file in your project root with your API keys and settings (you can copy `.env.example` and modify it).
    *   Create/customize `system_prompt.txt` and `blacklist.json` in your project root if you're using the default paths.

3.  **Run the Docker container:**
    ```bash
    docker run --rm \
      --env-file .env \
      -v "$(pwd)/system_prompt.txt:/app/system_prompt.txt:ro" \
      -v "$(pwd)/blacklist.json:/app/blacklist.json:ro" \
      football-suggester
    ```
    *   `--rm`: Automatically removes the container when it exits.
    *   `--env-file .env`: Loads your environment variables from the `.env` file in your current directory.
    *   The `-v` flags mount your local configuration files into the container (read-only). The example paths assume `system_prompt.txt` and `blacklist.json` are in your current directory (project root).
    *   The paths `/app/system_prompt.txt` and `/app/blacklist.json` inside the container match the default paths expected by the application if `SYSTEM_PROMPT_FILE_PATH` and `BLACKLIST_FILE_PATH` are not overridden in your `.env` file. If you set these variables to different paths (e.g., `/config/my_prompt.txt`), ensure your volume mount paths (`-v source:target`) reflect those target paths.

## Development

1.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up environment variables:**
    Create a `.env` file in the project root (copy from `.env.example`) and fill in your configuration. The application will load this file during development.

4.  **Run the service:**
    ```bash
    python main.py
    ```

5.  **Run tests:**
    ```bash
    # Ensure you are in the project root directory
    python -m unittest discover -s tests
    ```
    Or, if you prefer using pytest (also listed in `requirements.txt`):
    ```bash
    pytest
    ```

## Project Structure
```
football_suggester/
├── football_suggester/         # Main application Python package
│   ├── __init__.py
│   ├── api_client.py       # Fetches games from api-football.com
│   ├── blacklist.py        # Handles game/league blacklisting
│   ├── calendar_manager.py # Manages CalDAV calendar events
│   ├── config.py           # Loads configuration from environment/.env
│   └── llm_handler.py      # Interacts with the LLM for suggestions
├── tests/                    # Unit tests
│   ├── __init__.py           # Makes 'tests' a package (optional for simple discover)
│   ├── test_blacklist.py
│   ├── test_calendar_manager.py
│   ├── test_llm_handler.py
│   └── temp_test_files/      # Directory created/used by some tests, then removed
├── .env.example              # Example environment variables file
├── .gitignore                # Specifies intentionally untracked files for Git
├── .dockerignore             # Specifies files to ignore when building Docker image
├── AGENTS.md                 # Instructions for AI agents working on this codebase
├── Dockerfile                # Defines the Docker image
├── main.py                   # Main script to run the service
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── system_prompt.example.txt # Example system prompt for the LLM
└── blacklist.example.json    # Example blacklist file
```
