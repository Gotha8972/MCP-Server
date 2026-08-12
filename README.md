# Splitwise MCP Server

A custom MCP (Model Context Protocol) server that connects to your Splitwise account. Query your expenses, see who owes whom, and get category-wise spending breakdowns — all from your MCP client (Claude Desktop, Gemini CLI, etc).

**Read-only · INR only**

## Features

| Tool | Description |
|---|---|
| `get_my_profile` | Your Splitwise user info |
| `get_friends_balances` | Friends with INR balances (who owes whom) |
| `get_groups` | All groups with members and balances |
| `get_expenses` | Fetch expenses with date/group/friend filters |
| `get_spending_by_category` | ⭐ Category-wise spending breakdown |
| `get_category_list` | All Splitwise categories & subcategories |

## Setup

### 1. Get Splitwise API Credentials

1. Go to [https://secure.splitwise.com/oauth_clients](https://secure.splitwise.com/oauth_clients)
2. Click **Register your application**
3. Fill in any name/description/URL (they can be placeholders)
4. After registering, you'll see your **Consumer Key** and **Consumer Secret**
5. On the same page, you'll find your **API Key** — this is tied to your personal account

### 2. Configure Credentials

Copy the example env file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```
SPLITWISE_CONSUMER_KEY=your_consumer_key
SPLITWISE_CONSUMER_SECRET=your_consumer_secret
SPLITWISE_API_KEY=your_api_key
```

### 3. Install Dependencies

```bash
# Create a virtual environment (recommended)
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install
pip install -e .
```

### 4. Test with MCP Inspector

```bash
fastmcp dev inspector server.py
```

This opens a web UI where you can test each tool interactively.

### 5. Configure Your MCP Client

#### Claude Desktop

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "splitwise": {
      "command": "python",
      "args": ["c:\\Project\\Spark MCP\\server.py"],
      "env": {
        "SPLITWISE_CONSUMER_KEY": "your_key",
        "SPLITWISE_CONSUMER_SECRET": "your_secret",
        "SPLITWISE_API_KEY": "your_api_key"
      }
    }
  }
}
```

#### Gemini CLI

Add to your `~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "splitwise": {
      "command": "python",
      "args": ["c:\\Project\\Spark MCP\\server.py"],
      "env": {
        "SPLITWISE_CONSUMER_KEY": "your_key",
        "SPLITWISE_CONSUMER_SECRET": "your_secret",
        "SPLITWISE_API_KEY": "your_api_key"
      }
    }
  }
}
```

## Example Prompts

Once configured, try asking your AI assistant:

- *"How much have I spent this month?"*
- *"Show me my spending by category for the last 3 months"*
- *"Who owes me money?"*
- *"What are my recent expenses in the Flat group?"*
- *"What's my total spending on food this year?"*

## License

MIT
