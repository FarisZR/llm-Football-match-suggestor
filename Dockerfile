# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the content of the local src directory to the working directory
COPY . .

# Specify the command to run on container startup
# This will be updated once main.py is created
# CMD ["python", "main.py"]

# Expose any necessary ports (if the service were to run a web server, for example)
# Not strictly necessary for a script-based service that runs and exits,
# but good practice if it evolves.
# EXPOSE 8000

# Environment variables for configuration (can be set at runtime)
# ENV API_FOOTBALL_KEY=""
# ENV CALDAV_URL=""
# ENV CALDAV_USERNAME=""
# ENV CALDAV_PASSWORD=""
# ENV OPENAI_API_KEY="" # Or other LLM provider key
# ENV BLACKLIST_FILE="blacklist.json"
# ENV SYSTEM_PROMPT_FILE="system_prompt.txt"

ENTRYPOINT ["python", "main.py"]
