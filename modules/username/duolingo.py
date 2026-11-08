from datetime import datetime
import core

SITE = "Duolingo"

def check(username, callback):
    url = f"https://www.duolingo.com/2017-06-30/users?username={username}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    try:
        r = core.safe_request("GET", url, headers=headers, timeout=10)

        if r.status_code == 200:
            try:
                data = r.json()
                users = data.get("users", [])

                if users and users[0].get("id") != 0:
                    u = users[0]
                    details = []

                    if u.get("name"): details.append(f"Name: {u['name']}")
                    if u.get("id"): details.append(f"ID: {u['id']}")
                    if u.get("learningLanguage"): details.append(f"Learning: {u['learningLanguage']}")
                    if u.get("fromLanguage"): details.append(f"From: {u['fromLanguage']}")
                    if u.get("location"): details.append(f"Location: {u['location']}")
                    if u.get("creationDate"):
                        try:
                            details.append(f"Joined: {datetime.fromtimestamp(u['creationDate']).strftime('%d. %m. %Y')}")
                        except Exception:
                            pass
                    if u.get("totalXp") is not None: details.append(f"XP: {u['totalXp']}")

                    pic = u.get("picture", "")
                    if pic.startswith("//"): pic = "https:" + pic
                    if pic: details.append(f"Avatar: {pic}")

                    callback({
                        "site": SITE,
                        "status": "Found",
                        "details": " | ".join(details),
                        "tool": "Native Check",
                        "url": f"https://www.duolingo.com/profile/{u.get('username')}"
                    })
            except Exception:
                pass
    except Exception:
        pass
