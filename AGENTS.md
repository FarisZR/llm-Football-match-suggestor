## Agent Instructions for `football_suggester`

This document provides guidance for AI agents working on the `football_suggester` project.

### Project Goal

The primary goal is to create a Python service that fetches upcoming football (soccer) matches, uses an LLM to determine which matches might be "interesting" based on user-defined criteria, and then adds these matches to a CalDAV calendar. The service must be runnable as a Docker container.

### Key Technologies

- Python 3.10+
- `requests` for HTTP calls (api-football.com)
- `python-dotenv` for environment variable management
- `caldav` for CalDAV integration
- An LLM provider API (e.g., OpenAI)
- Docker for containerization

### Development Guidelines

1.  **Configuration:**
    *   All sensitive information (API keys, URLs, credentials) and configurable parameters (file paths, LLM model names) MUST be managed via environment variables. Use the `python-dotenv` library and a `config.py` module to load these.
    *   Provide clear examples in `.env.example`.
    *   Refer to configuration values via the `config.py` module, not directly using `os.getenv` everywhere.

2.  **Modularity:**
    *   Break down functionality into logical modules (e.g., `api_client.py`, `llm_handler.py`, `calendar_manager.py`, `blacklist.py`).
    *   Each module should have a clear responsibility.

3.  **Error Handling:**
    *   Implement robust error handling, especially for external API calls, file operations, and network requests.
    *   Use try-except blocks appropriately.
    *   Log errors effectively using the `logging` module.

4.  **Logging:**
    *   Use the standard Python `logging` module for all informational and error messages.
    *   Make the log level configurable via an environment variable (e.g., `LOG_LEVEL`).
    *   Logs should be informative enough to debug issues.

5.  **API Interaction (api-football.com):**
    *   Encapsulate all logic for interacting with api-football.com within `api_client.py`.
    *   Handle potential API errors gracefully (e.g., rate limits, authentication failures, invalid responses).
    *   Ensure the client can handle parameters for filtering (e.g., date ranges for fixtures).

6.  **LLM Interaction:**
    *   Encapsulate LLM interaction logic in `llm_handler.py`.
    *   The system prompt should be loaded from an external file, configurable via an environment variable.
    *   The LLM should be prompted to return a structured response (e.g., a list of fixture IDs) that can be easily parsed.
    *   Make the choice of LLM provider and model configurable if feasible, but start with one (e.g., OpenAI).

7.  **Calendar Integration (caldav):**
    *   Encapsulate CalDAV logic in `calendar_manager.py`.
    *   Ensure that event creation is idempotent where possible (i.e., don't create duplicate events if the script runs multiple times for the same game). This might involve checking if an event for a specific game already exists.
    *   Event details (summary, description, start/end times) should be clear and informative.

8.  **Blacklisting:**
    *   The blacklist should be loaded from a file (e.g., JSON). The file path should be configurable.
    *   The filtering logic should be efficient.

9.  **Dockerfile:**
    *   The `Dockerfile` should create a minimal, secure image.
    *   Use a slim base image (e.g., `python:3.10-slim`).
    *   Ensure `requirements.txt` is copied and dependencies are installed efficiently.
    *   The `CMD` or `ENTRYPOINT` should run the main service script.
    *   Clearly document how to build and run the container, including passing necessary environment variables and mounting configuration files.

10. **Main Script (`main.py`):**
    *   This script should orchestrate the overall workflow:
        1.  Load configuration.
        2.  Initialize logging.
        3.  Fetch upcoming games.
        4.  Apply blacklist.
        5.  Process games with LLM to get suggestions.
        6.  Add suggested games to the calendar.
    *   It should be the entry point for the application.

11. **Testing:**
    *   Aim for good test coverage.
    *   Write unit tests for individual functions and modules, especially for business logic and helper functions. Mock external services (APIs, CalDAV server, LLM) during unit testing.
    *   Consider integration tests if time permits, but prioritize unit tests.

12. **Readability and Maintainability:**
    *   Write clean, well-commented Python code.
    *   Follow PEP 8 guidelines. Consider using tools like `black` and `flake8`.
    *   Keep functions small and focused on a single task.

### Specific Instructions for Current Task

*   Focus on establishing the basic project structure and placeholder files first.
*   Implement the configuration loading early as it will be used by many modules.
*   When implementing modules, start with the core functionality and add error handling and logging progressively.
*   If you encounter ambiguity or need clarification on a specific API endpoint or data format, make a reasonable assumption and note it, or ask the user.

By following these guidelines, the resulting service should be robust, maintainable, and meet the user's requirements.
