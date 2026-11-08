import core

SITE = "GitLab"

def check(username, callback):
    r = core.safe_request("GET", f"https://gitlab.com/api/v4/users?username={username}")

    if r.status_code == 200:
        data = r.json()
        if isinstance(data, list) and len(data) > 0:
            user = data[0]
            details = []

            if user.get("id"): details.append(f"ID: {user['id']}")
            if user.get("name"): details.append(f"Name: {user['name']}")
            if user.get("state"): details.append(f"State: {user['state']}")
            if user.get("public_email"): details.append(f"Email: {user['public_email']}")
            if user.get("avatar_url"): details.append(f"Avatar: {user['avatar_url']}")

            callback({
                "site": SITE,
                "status": "Found",
                "details": " | ".join(details),
                "tool": "Native Check",
                "url": user.get("web_url", "")
            })
