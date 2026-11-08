# haxdog

haxdog is a command-line OSINT tool. It searches for a username or email address across social media platforms and services.

## Features

- Username and email searches (Spotify, Discord, Giphy, etc.)
- Clean terminal output with Rich, including inline avatar rendering
- `--json` flag for easy scripting and automation
- Drop-in modules: just add a file to `modules/`, no core edits needed

## Installation

1. Clone the repository.
```bash
git clone https://github.com/yourusername/haxdog.git
cd haxdog
```

2. Create a virtual environment.
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install the requirements.
```bash
pip install -r requirements.txt
```

## Usage

Run the tool without arguments to see the help screen.
```bash
python main.py
```

Search by username:
```bash
python main.py --username johndoe
```

Search by email:
```bash
python main.py --email test@example.com
```

Output as JSON:
```bash
python main.py --username johndoe --json
```

List all available modules:
```bash
python main.py --list
```

## Adding Modules

You never need to edit `main.py` or `core.py`. Create a new file in `modules/username/` or `modules/email/`. The tool detects and loads it on the next run.

**Example module (`modules/username/example.py`):**
```python
import core

SITE = "ExampleSite"

def check(username, callback):
    url = f"https://api.example.com/users/{username}"
    r = core.safe_request("GET", url)
    
    if r.status_code == 200:
        callback({
            "site": SITE,
            "status": "Found",
            "details": "Profile exists",
            "tool": "Native Check",
            "url": f"https://example.com/{username}",
        })
```

To extract avatars or extra details, add an `enrich(url)` function and define `DOMAINS = ["example.com"]`.

## Disclaimer

This tool is for educational purposes and authorized security testing. Do not use it to harass or stalk anyone, and respect the terms of service of the platforms it queries.
