import core

SITE = "Spotify"


def check(email, callback):
    url = (
        "https://spclient.wg.spotify.com/signup/public/v1/account"
        f"?validate=1&email={email}"
    )
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        r = core.safe_request("GET", url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            errors = data.get("errors", {}) or {}
            if data.get("status") == 20 and "already registered" in errors.get("email", ""):
                callback({
                    "site": SITE,
                    "status": "Found",
                    "details": "email is registered",
                    "tool": "Native Email",
                    "url": "https://www.spotify.com/",
                })
    except Exception:
        pass
