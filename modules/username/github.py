from datetime import datetime
import re
import core

SITE = "GitHub"
DOMAINS = ["github.com"]

_TRAILER_RE = re.compile(
    r"^(?P<key>Signed-off-by|Co-authored-by|Reviewed-by|Tested-by|"
    r"Reported-by|Acked-by|Suggested-by|Cc):\s+"
    r"(?P<name>[^<]+?)\s+<(?P<email>[^>]+)>\s*$",
    re.MULTILINE | re.IGNORECASE,
)

_SYSTEM_EMAIL_RE = re.compile(
    r'(^(?:noreply|no-reply|donotreply|do-not-reply)@|@users\.noreply\.github\.com$)',
    re.IGNORECASE,
)

def _is_system_email(email):
    return bool(email and _SYSTEM_EMAIL_RE.search(email))


def check(username, callback):
    r = core.safe_request("GET", f"https://api.github.com/users/{username}")
    if r.status_code == 200:
        callback({
            "site": SITE,
            "status": "Found",
            "details": "",
            "tool": "Native Check",
            "url": f"https://github.com/{username}"
        })


def _extract_emails_from_user(username):
    headers = {"Accept": "application/vnd.github+json"}
    emails = set()
    try:
        r_gpg = core.safe_request("GET", f"https://api.github.com/users/{username}/gpg_keys", headers=headers, timeout=10)
        if r_gpg.status_code == 200:
            for key in r_gpg.json():
                for em in key.get("emails", []):
                    if em.get("email"):
                        emails.add(em["email"].lower())

        r_commits = core.safe_request("GET", f"https://api.github.com/search/commits?q=author:{username}&per_page=10", headers=headers, timeout=10)
        if r_commits.status_code == 200:
            for item in r_commits.json().get("items", []):
                commit = item.get("commit", {})
                if commit.get("author", {}).get("email"):
                    emails.add(commit["author"]["email"].lower())
    except Exception:
        pass
    return emails


def _extract_emails_cross_repo(username):
    headers = {"Accept": "application/vnd.github+json"}
    emails = set()

    for page in range(1, 11):
        url = f"https://api.github.com/search/commits?q=author:{username}&per_page=100&page={page}"
        try:
            r = core.safe_request("GET", url, headers=headers, timeout=15)
            if r.status_code != 200:
                break
            data = r.json()
            items = data.get("items", [])
            if not items:
                break

            for item in items:
                commit = item.get("commit", {})

                for role in ("author", "committer"):
                    who = commit.get(role, {})
                    email = who.get("email")
                    if email:
                        emails.add(email.lower())

                message = commit.get("message", "")
                for tm in _TRAILER_RE.finditer(message):
                    email = tm.group("email").strip()
                    name = tm.group("name").strip()
                    if email and ":" not in name and "@" not in name:
                        emails.add(email.lower())
        except Exception:
            break

    return emails


def enrich(url):
    user = url.strip("/").split("/")[-1]
    headers = {"Accept": "application/vnd.github+json"}

    custom_data = {}
    image_url = None

    try:
        r = core.safe_request("GET", f"https://api.github.com/users/{user}", headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("name"): custom_data["Name"] = data["name"]
            if data.get("id"): custom_data["ID"] = str(data["id"])
            if data.get("location"): custom_data["Location"] = data["location"]
            if data.get("company"): custom_data["Company"] = data["company"]
            if data.get("blog"): custom_data["Blog"] = data["blog"]
            if data.get("twitter_username"): custom_data["Twitter"] = f"@{data['twitter_username']}"
            if data.get("bio"): custom_data["Bio"] = data["bio"]
            if data.get("public_repos") is not None: custom_data["Public Repos"] = str(data["public_repos"])
            if data.get("followers") is not None: custom_data["Followers"] = str(data["followers"])
            if data.get("created_at"):
                try:
                    custom_data["Joined"] = datetime.strptime(data["created_at"], "%Y-%m-%dT%H:%M:%SZ").strftime("%d. %m. %Y")
                except Exception:
                    pass
            if data.get("avatar_url"):
                image_url = data["avatar_url"]

        r_orgs = core.safe_request("GET", f"https://api.github.com/users/{user}/orgs", headers=headers, timeout=10)
        if r_orgs.status_code == 200:
            orgs = [org.get("login") for org in r_orgs.json()]
            if orgs:
                custom_data["Organizations"] = ", ".join(orgs)

        all_emails = _extract_emails_from_user(user)
        all_emails |= _extract_emails_cross_repo(user)

        real_emails = sorted(e for e in all_emails if e and not _is_system_email(e))
        if real_emails:
            custom_data["Extracted Emails"] = " | ".join(real_emails)

    except Exception:
        pass

    avatar_bytes = None
    if image_url:
        try:
            avatar_bytes = core.safe_request("GET", image_url).content
        except Exception:
            pass

    return {"api_data": custom_data, "avatar_bytes": avatar_bytes, "avatar_url": image_url}