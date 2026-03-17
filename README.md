# DeepSeek & Gemini API Proxy

A local API server that provides OpenAI-compatible endpoints for DeepSeek Chat and Gemini Web using browser automation. This allows you to interact with AI models without requiring an API key.

## Features

- **OpenAI-compatible API** - Use OpenAI client libraries to connect
- **Browser Automation** - Uses Playwright to interact with web chat UI
- **Multi-Provider Support** - Currently supports DeepSeek and Gemini 3 Flash
- **RESTful Endpoints** - Full REST API with standard HTTP methods
- **Streaming Support** - Real-time streaming responses
- **Conversation Management** - Continue existing conversations (DeepSeek only)
- **Thinking Mode** - Enable DeepSeek's reasoning/think process in responses

## Requirements

- Python 3.9+
- Google Chrome browser (for Playwright automation)
- Playwright browsers installed

## Installation

1. **Clone the repository or navigate to the project directory:**

```bash
cd ai-web-proxy
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
        "port": 8000
    },
    "deepseek": {
        "enabled": true,
        "base_url": "https://chat.deepseek.com",
        "chrome_path": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
    },
    "gemini": {
        "enabled": true,
        "base_url": "https://gemini.google.com"
    },
    "browser": {
        "use_browser": true,
        "headless": false,
        "page_load_timeout": 60,
        "navigation_timeout": 30,
        "action_timeout": 10,
        "max_retries": 3,
        "retry_delay": 0.5,
        "disable_dev_shm": true,
        "no_sandbox": true,
        "disable_gpu": true
    }
}
```

| Setting | Description | Default |
|---------|-------------|---------|
| `server.host` | Server bind address | `0.0.0.0` |
| `server.port` | Server port | `8000` |
| `deepseek.enabled` | Enable/start the DeepSeek provider | `true` |
| `deepseek.base_url` | DeepSeek web chat URL | `https://chat.deepseek.com` |
| `deepseek.chrome_path` | Path to Chrome browser | (system default) |
| `gemini.enabled` | Enable/start the Gemini provider | `true` |
| `gemini.base_url` | Gemini web chat URL | `https://gemini.google.com` |
| `browser.use_browser` | Enable browser automation | `true` |
| `browser.headless` | Run browser in headless mode | `false` |
| `browser.page_load_timeout` | Page load timeout (seconds) | `60` |
| `browser.navigation_timeout` | Navigation timeout (seconds) | `30` |
| `browser.action_timeout` | Action timeout (seconds) | `10` |
| `browser.max_retries` | Maximum retry attempts | `3` |

## Usage

### Starting the Server

```bash
python main.py
```

The server will start at `http://localhost:8000`. On first run (if headless is false), a browser window will open for you to log in to your account.

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

List all available and enabled models dynamically:

```bash
curl http://localhost:8000/v1/models
```

#### Continue Conversation (DeepSeek Only)

To continue an existing conversation on DeepSeek, provide the `conversation_id` from the DeepSeek chat URL:

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

**Note:** The `conversation_id` navigates to the existing conversation in the browser. The messages array is only used for the current prompt (last user message). *Gemini unauthenticated mode does not support `conversation_id`.*

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
      {"role": "user", "content": "Explain quantum computing in simple terms."}
    ]
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

# With thinking mode enabled (DeepSeek Only)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {"role": "user", "content": "Solve this math problem: 2 + 2 = ?"}
    ],
    "thinking": true
  }'
```

## Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `model` | string | Yes | Model ID (`deepseek-chat`, `gemini-3-flash`, etc.) |
| `messages` | array | Yes | List of message objects (only the **last user message** is used) |
| `stream` | boolean | No | Enable streaming. Default: `false` |
| `conversation_id` | string | No | Continue existing conversation by navigating to its URL. *DeepSeek ONLY.* |
| `create_new` | boolean | No | Create new conversation. Default: `true` |
| `thinking` | boolean | No | Enable thinking mode. Use `true` to enable. Default: `false` (*DeepSeek ONLY.*) |

### Message Format

**Note:** Currently, only the **last user message** is sent to the provider. System messages and previous conversation history are not included in the request.

```json
{
  "messages": [
    {"role": "user", "content": "Your question here"}
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
        "content": "AI response here",
        "reasoning_content": "Thinking process (if thinking mode enabled)",
        "thinking_time": 6,
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 50,
    "total_tokens": 60
  },
  "conversation_id": "abc123xyz"
}
```

**Note:** When thinking mode is enabled, the response will include:
- `reasoning_content` - The AI's thinking/reasoning process
- `thinking_time` - Time spent on thinking in seconds
- `conversation_id` - The DeepSeek conversation ID (returned in response body and headers)

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

5. **Thinking Mode**: Use `"thinking": {"type": "enabled"}` in your request to enable DeepSeek's reasoning process. This provides more detailed reasoning but may take longer.

6. **Use Cases**: This is useful for development, testing, and scenarios where you don't have an API key but need programmatic access to DeepSeek.

7. **Messages Behavior**: Currently, only the **last user message** in the `messages` array is sent to DeepSeek. System prompts and conversation history are not preserved between requests (unless using `conversation_id` to navigate to an existing conversation in the browser).

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
ai-web-proxy/
├── main.py                 # FastAPI server entry point
├── config.json             # Application configuration
├── requirements.txt        # Python dependencies
├── session.json            # Browser session storage
├── src/
│   ├── __init__.py
│   ├── config.py           # Configuration loader
│   ├── models.py           # Pydantic request/response models
│   ├── proxy.py            # API & Models Provider Proxy
│   ├── browser_deepseek.py # Playwright browser automation for DeepSeek
│   ├── browser_gemini.py   # Playwright browser automation for Gemini
│   ├── session.py          # Session management
│   ├── mapper.py           # Data mapping utilities
│   ├── tokenizer.py        # Token counting utilities
│   ├── constants.py        # Application constants
│   └── providers/          # Provider implementations
│       ├── __init__.py
│       ├── base.py         # Base Provider interface
│       ├── deepseek.py     # DeepSeek Provider
│       └── gemini.py       # Gemini Provider
└── README.md               # This file
```

## License

MIT License

## Disclaimer

This project is for educational and personal use. It automates the web interface of DeepSeek and should be used responsibly. Make sure to comply with DeepSeek's Terms of Service when using this proxy.