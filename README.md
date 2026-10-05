# Oggy — Telegram AI Assistant

Oggy is a Telegram-based AI assistant built with Python. It uses the Groq API for LLM responses and maintains both short-term conversation history and user-defined long-term memories using a local JSON file.

The project was built as a practical experiment in combining Telegram bots, LLM APIs, persistent memory, conversation handling, and message formatting.

## Features

- AI-powered conversations using the Groq API
- Private chat and group chat support
- Persistent long-term memory
- Short-term conversation history
- JSON-based persistent storage
- Save memories using `/save_memory`
- Display stored memories using `/display_memory`
- Delete memories using `/delete_memory`
- Automatically re-indexes memories after deletion
- Telegram-compatible Markdown formatting
- Automatically splits long Telegram messages while preserving formatting
- Configurable LLM model and conversation attention window

## How It Works

Oggy maintains two types of memory for each Telegram chat.

### 1. Conversation Memory

Recent messages between the user and Oggy are stored in the JSON database.

The number of stored conversation messages is controlled by the attention window:

```python
ATTENTION_WINDOW = 10
```

Only the most recent messages are retained:

```python
knowledge["conversation"] = knowledge["conversation"][-ATTENTION_WINDOW:]
```

This allows Oggy to maintain conversational context without continually sending the entire conversation history to the LLM.

### 2. Long-Term Memory

Users can explicitly tell Oggy to remember something.

For example:

```text
/save_memory
```

Oggy asks:

```text
What should I remember?
```

The next message is then stored as a long-term memory.

Long-term memories are included in the system context whenever Oggy generates a response.

Example:

```json
"long_term_memory": [
    {
        "id": 1,
        "content": "User is learning C++."
    },
    {
        "id": 2,
        "content": "User is building an AI assistant."
    }
]
```

Unlike conversation memory, long-term memories are not removed by the attention window.

## Available Commands

| Command | Description |
|---|---|
| `/start` | Starts the bot |
| `/help` | Displays help information |
| `/save_memory` | Saves a new long-term memory |
| `/display_memory` | Displays stored long-term memories |
| `/delete_memory` | Deletes a selected long-term memory |

Note: You will need to configure these commands in your telegram bot using the Telegram App or Website.

### Saving a Memory

```text
/save_memory
```

Oggy will ask what it should remember. Enter the information you want to store.

### Displaying Memories

```text
/display_memory
```

Oggy displays the stored memories along with their indexes.

### Deleting a Memory

```text
/delete_memory
```

Oggy displays the current memories and asks for the index of the memory to delete.

After deletion, the remaining memories are automatically re-indexed.

## Architecture

The basic flow of a normal message is:

```text
Telegram
   |
   v
Telegram Bot
   |
   v
Load JSON Memory
   |
   +-- Long-Term Memory
   |
   +-- Recent Conversation
   |
   v
Groq API
   |
   v
LLM Response
   |
   v
Markdown Conversion
   |
   v
Telegram Message
   |
   v
Save Conversation
```

Long-term memories are added to the system context before the conversation history and current user message.

## Technologies Used

- Python
- python-telegram-bot
- Groq API
- Groq LLM
- telegramify-markdown
- JSON

### Python Libraries

The main dependencies are:

```text
python-telegram-bot
telegramify-markdown
groq
```

## Setup

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd <repository-directory>
```

### 2. Install Dependencies

```bash
pip install python-telegram-bot groq telegramify-markdown
```

### 3. Create a Telegram Bot

Create a bot using Telegram's BotFather and obtain the bot token.

Set the token in the configuration section of the project.

**Do not commit your bot token to GitHub.**

### 4. Configure the Groq API

Create a Groq API key and store it as an environment variable:

```bash
GROQ_API_KEY=your_api_key
```

The application reads the API key using:

```python
os.environ.get("GROQ_API_KEY")
```

### 5. Configure the Bot

The main configuration values are:

```python
BOT_TOKEN = "<BotToken>"
BOT_USERNAME = "@<YourBotName>"
BOT_PROMPT = "You are a helpful assistant."
LLM_MODEL = "openai/gpt-oss-120b"
MEMORY_LOCATION = "llm_memory.json"
ATTENTION_WINDOW = 10
```

You can change the model to another model available through your Groq account.

### 6. Run the Bot

```bash
python telegram_bot.py
```

The bot uses Telegram polling to receive messages.

## Group Chat Support

Oggy can also operate in Telegram group chats.

In a group, Oggy only responds when its username is mentioned.

For example:

```text
@YourBotName explain recursion
```

The bot removes its username from the message before sending the remaining text to the LLM.

Messages that do not mention the bot are ignored.

## Message Formatting

LLM responses are generated as Markdown.

Since Telegram has its own message-formatting rules, Oggy uses `telegramify-markdown` to convert the generated Markdown into Telegram-compatible message entities.

```python
formatted_text, entities = convert(markdown)
```

Long messages are split using `split_entities()` so that Telegram's message length limit can be respected without breaking formatting.

```python
for chunk_text, chunk_entities in split_entities(
    messages,
    entities,
    max_utf16_len=4096
):
    await update.message.reply_text(
        chunk_text,
        entities=[e.to_dict() for e in chunk_entities]
    )
```

## Data Storage

The bot currently uses a JSON file for persistent storage:

```text
llm_memory.json
```

Each Telegram chat has its own memory entry.

A simplified structure looks like:

```json
{
    "chat_id": {
        "memory_len": 2,
        "long_term_memory": [
            {
                "id": 1,
                "content": "Example memory"
            },
            {
                "id": 2,
                "content": "Another memory"
            }
        ],
        "conversation": [
            {
                "role": "user",
                "content": "Hello"
            },
            {
                "role": "assistant",
                "content": "Hello! How can I help?"
            }
        ]
    }
}
```

The Telegram chat ID is used to keep each chat's data separate.

## Project Structure

A simple version of the project looks like:

```text
.
├── telegram_bot.py
├── llm_memory.json
└── README.md
```

The JSON file acts as the persistent database for the current implementation.

## Security

### Never commit secrets

Do not upload the following to GitHub:

- Telegram bot tokens
- Groq API keys
- Other API credentials
- Private user data
- Personal Telegram chat IDs if they contain sensitive information

Use environment variables for API keys whenever possible.

For example:

```bash
GROQ_API_KEY=your_api_key
```

The included source code should contain placeholders rather than real credentials.

## Limitations

This project intentionally uses a simple architecture.

The current implementation stores persistent data in a JSON file, which is convenient for a small personal project but is not ideal for a large number of users.

Potential limitations include:

- JSON file writes can become problematic with many simultaneous users.
- Conversation history is limited by the attention window.
- Long-term memory is manually managed by the user.
- There is currently no authentication layer beyond Telegram's chat identity.
- The bot depends on the availability of the Groq API.
- The bot currently uses polling rather than a webhook.

For a larger deployment, a database such as SQLite or PostgreSQL would be a more robust choice.

## Future Improvements

- [ ] `/list_memory` command
- [ ] `/clear_memory` command
- [ ] Editable bot personality/prompt
- [ ] Per-user attention window
- [ ] `/settings` command
- [ ] Better memory search and retrieval
- [ ] SQLite/PostgreSQL storage
- [ ] Automatic summarization of older conversations
- [ ] Memory categories/tags
- [ ] Memory editing
- [ ] Webhook-based deployment
- [ ] Improved error handling
- [ ] Async Groq API calls

## Learning Goals

This project was also built as a learning project to explore:

- Telegram Bot API
- Python asynchronous programming
- Conversation handlers
- LLM APIs
- Prompt construction
- Short-term and long-term memory
- JSON persistence
- Message formatting
- Context-window management
- API key management
- Building practical AI assistants

## License

This project is available for educational and personal use.

Add your preferred license here, for example:

```text
MIT License
```
