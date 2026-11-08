import core

SITE = "Discord"


def check(username, callback):
    url = "https://discord.com/api/v9/unique-username/username-attempt-unauthed"
    headers = {"Content-Type": "application/json"}
    payload = {"username": username}

    try:
        r = core.safe_request("POST", url, headers=headers, json=payload, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("taken") is True:
                callback({
                    "site": SITE,
                    "status": "Found",
                    "details": "username is taken",
                    "tool": "Native Check",
                    "url": "https://discord.com",
                })
            else:
                callback({
                    "site": SITE,
                    "status": "Not Registered",
                    "details": "username is available",
                    "tool": "Native Check",
                    "url": "",
                })
    except Exception:
        pass
