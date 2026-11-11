import core

SITE = "Roblox"

def check(username, callback):
    validate_url = (
        f"https://auth.roblox.com/v1/usernames/validate"
        f"?username={username}&birthday=2019-1&context=Signup"
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        r = core.safe_request("GET", validate_url, headers=headers, timeout=10)
        if r.status_code != 200:
            return

        data = r.json()
        if data.get("code") == 0:
            return
        url = "https://users.roblox.com/v1/usernames/users"
        payload = {
            "usernames": [username],
            "excludeBannedUsers": False
        }
        headers_post = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        r2 = core.safe_request("POST", url, headers=headers_post, json=payload, timeout=10)
        if r2.status_code == 200:
            data2 = r2.json()
            users = data2.get("data", [])
            if users:
                user = users[0]
                details = []
                if user.get("id"):
                    details.append(f"ID: {user['id']}")
                if user.get("name"):
                    details.append(f"Name: {user['name']}")
                if user.get("displayName"):
                    details.append(f"Display Name: {user['displayName']}")

                callback({
                    "site": SITE,
                    "status": "Found",
                    "details": " | ".join(details),
                    "tool": "Native Check",
                    "url": f"https://www.roblox.com/users/{user.get('id')}/profile"
                })
    except Exception:
        pass
