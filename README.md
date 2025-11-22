# Giacomino

API for my custom [chatbot](https://www.giacomociro.com).

## Setup

Create a `.env` file in the root directory with the following entries:

```env
TOGETHER_API_KEY=""                # Your Together API key
FLASK_ENV="production"              # Flask environment (production/development)
PORT=5000                           # Port to run the API
RETRIEVE_TOP_K=10                   # Number of documents to put in context
MAX_CHARS=2048                      # Max characters per conversation
HISTORY_KEY=""                      # Password to access the history endpoint
LOG_FILE="logs.txt"                 # Log file path
TEXT_MODEL_PATH="meta-llama/Llama-3.2-3B-Instruct-Turbo"    # Model to generate answers
EMB_MODEL_PATH="BAAI/bge-large-en-v1.5"                    # Embedding model
CHAT_REQUESTS_PER_HOUR_LIMIT=10     # Rate limit for chat requests per hour
```