import core

SITE = "Seznam.cz"


def check(email, callback):
    ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    try:
        r = core.safe_request(
            "GET",
            f"https://registrace.seznam.cz/api/v1/username-check/{email}",
            headers={"User-Agent": ua},
            timeout=10,
        )
        if r.status_code == 200 and r.json().get("available") is False:
            recover_url = f"https://login.szn.cz/api/v1/recover/request?username={email}"
            rr = core.safe_request(
                "GET",
                recover_url,
                headers={"User-Agent": ua, "Accept": "application/json",
                         "Referer": "https://login.szn.cz/"},
                timeout=10,
            )
            details_list = []
            if rr.status_code == 474:
                details_list.append("no recovery options set")
            elif rr.status_code == 200:
                try:
                    j = rr.json()
                    if j.get("avatar_url"):
                        details_list.append(f"Avatar: {j['avatar_url']}")
                    if j.get("email"):
                        details_list.append(f"Recovery Email: {j['email']}")
                    phone = j.get("phone")
                    if isinstance(phone, list) and len(phone) >= 2:
                        details_list.append(f"Phone: {phone[0]} *** *** {phone[1]}")
                    prov = j.get("identity_providers")
                    if isinstance(prov, list) and prov:
                        details_list.append(f"SSO: {', '.join(prov)}")
                except Exception:
                    pass

            callback({
                "site": SITE,
                "status": "Found",
                "details": " | ".join(details_list) or "account exists (no extra info)",
                "tool": "Czech Email",
                "url": recover_url,
            })
            return

        callback({
            "site": SITE,
            "status": "Not Registered",
            "details": "",
            "tool": "Czech Email",
            "url": "",
        })
    except Exception:
        pass
