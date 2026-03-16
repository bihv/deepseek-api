# DeepSeek API Proxy

A local API server that provides OpenAI-compatible endpoints for DeepSeek Chat using browser automation. This allows you to interact with DeepSeek's AI models without requiring an API key by automating the web-based chat interface.

## Features

- **OpenAI-compatible API** - Use OpenAI client libraries to connect to DeepSeek
- **Browser Automation** - Uses Playwright to interact with DeepSeek's web chat
- **RESTful Endpoints** - Full REST API with standard HTTP methods
- **Streaming Support** - Real-time streaming responses
- **Conversation Management** - Continue existing conversations or create new ones

## Requirements

- Python 3.9+
- Google Chrome browser (for Playwright automation)
- Playwright browsers installed

## Installation

1. **Clone the repository or navigate to the project directory:**

```bash
cd deepseek-api
```

2. **Create a virtual environment (recommended):**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
```

4. **Install Playwright browsers:**

```bash
playwright install chromium
```

## Configuration

Edit `config.json` to configure the application:

```json
{
    "server": {
        "host": "0.0.0.0",
        "port": 8000,
        "reload": true
    },
    "browser": {
        "headless": false,
        "timeout": 120
    },
    "deepseek": {
        "base_url": "https://chat.deepseek.com"
    }
}
```

| Setting | Description | Default |
|---------|-------------|---------|
| `server.host` | Server bind address | `0.0.0.0` |
| `server.port` | Server port | `8000` |
| `server.reload` | Auto-reload on code changes | `true` |
| `browser.headless` | Run browser in headless mode | `false` |
| `browser.timeout` | Browser operation timeout (seconds) | `120` |
| `deepseek.base_url` | DeepSeek web chat URL | `https://chat.deepseek.com` |

## Usage

### Starting the Server

```bash
python main.py
```

The server will start at `http://localhost:8000`. On first run, a browser window will open for you to log in to your DeepSeek account.

### API Endpoints

#### Chat Completion

**POST** `/v1/chat/completions`

Send a chat completion request (non-streaming):

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {"role": "user", "content": "Hello! How are you?"}
    ]
  }'
```

**POST** `/v1/chat/completions` (streaming)

Send a streaming chat completion request:

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {"role": "user", "content": "Hello! How are you?"}
    ],
    "stream": true
  }'
```

#### List Models

**GET** `/v1/models`

List available models:

```bash
curl http://localhost:8000/v1/models
```

#### Continue Conversation

To continue an existing conversation, provide the `conversation_id` from the DeepSeek chat URL:

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {"role": "user", "content": "Follow-up question"}
    ],
    "conversation_id": "abc123xyz",
    "create_new": false
  }'
```

### Using with OpenAI Python Library

```python
from openai import OpenAI

client = OpenAI(
    api_key="dummy",  # Not required for this proxy
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "user", "content": "What is Python?"}
    ]
)

print(response.choices[0].message.content)
```

### Using with cURL

```bash
# Non-streaming request
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Explain quantum computing in simple terms."}
    ],
    "temperature": 0.7
  }'

# Streaming request
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {"role": "user", "content": "Count from 1 to 5"}
    ],
    "stream": true
  }'
```

## Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `model` | string | Yes | Model ID (use `deepseek-chat`) |
| `messages` | array | Yes | List of message objects |
| `temperature` | float | No | Sampling temperature (0.0-2.0). Default: 0.7 |
| `max_tokens` | integer | No | Maximum tokens to generate |
| `stream` | boolean | No | Enable streaming. Default: false |
| `conversation_id` | string | No | Continue existing conversation |
| `create_new` | boolean | No | Create new conversation. Default: true |

### Message Format

```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Your question here"},
    {"role": "assistant", "content": "Previous response (optional)"},
    {"role": "user", "content": "Follow-up question"}
  ]
}
```

## Response Format

### Non-Streaming Response

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "deepseek-chat",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "AI response here"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 50,
    "total_tokens": 60
  }
}
```

### Streaming Response

```
data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"deepseek-chat","choices":[{"index":0,"delta":{"role":"assistant","content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"deepseek-chat","choices":[{"index":0,"delta":{"content":"!"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"deepseek-chat","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}
```

## Important Notes

1. **First Run**: On the first run, a browser window will open. You must log in to your DeepSeek account manually. The session will be saved for subsequent requests.

2. **Session Persistence**: The browser session is maintained as long as the server is running. Closing the browser window may require re-authentication on next run.

3. **Headless Mode**: Set `headless: true` in `config.json` for server environments without display. Note: Login may require manual intervention first.

4. **Rate Limiting**: This proxy uses the web interface, so it inherits the same rate limits as the web chat. Use responsibly.

5. **Use Cases**: This is useful for development, testing, and scenarios where you don't have an API key but need programmatic access to DeepSeek.

## Troubleshooting

### Browser not found

If you see an error about Chrome not being found, ensure Chrome is installed and the path in `src/browser.py` is correct.

### Login issues

- Ensure you're logged into DeepSeek in the browser that opens
- If using headless mode, run once with `headless: false` to log in, then switch to headless

### Connection timeout

Increase the `browser.timeout` value in `config.json` if responses take longer than expected.

### Response extraction issues

The browser automation relies on DeepSeek's UI structure. If responses are not being captured correctly, the UI may have changed. Check `src/browser.py` for selector updates.

## Project Structure

```
deepseek-api/
├── main.py                 # FastAPI server entry point
├── config.json             # Application configuration
├── requirements.txt        # Python dependencies
├── src/
│   ├── __init__.py
│   ├── config.py          # Configuration loader
│   ├── models.py          # Pydantic request/response models
│   ├── proxy.py           # DeepSeek proxy implementation
│   ├── browser.py         # Playwright browser automation
│   ├── session.py         # Session management
│   └── mapper.py          # Data mapping utilities
└── README.md              # This file
```

## License

MIT License

## Disclaimer

This project is for educational and personal use. It automates the web interface of DeepSeek and should be used responsibly. Make sure to comply with DeepSeek's Terms of Service when using this proxy.