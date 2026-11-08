import hashlib
import hmac
import re
import time

import core

SITE = "Spotify"

_TOTP_VERSION = "61"
_TOTP_SECRET = ',7/*F("rLJ2oxaKL^f+E1xvP@N'
_APP_VERSION = "1.3.8.509.g26b6eac7300d"
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_token_cache = {}


def _totp_key(secret: str) -> bytes:
    return "".join(
        str(ord(c) ^ (i % 33 + 9)) for i, c in enumerate(secret)
    ).encode()


def _totp(secret: str, timestamp_s: int) -> str:
    counter = int(timestamp_s) // 30
    digest = hmac.new(
        _totp_key(secret), counter.to_bytes(8, "big"), hashlib.sha1
    ).digest()
    offset = digest[-1] & 0x0F
    code = int.from_bytes(digest[offset:offset + 4], "big") & 0x7FFFFFFF
    return str(code % 1_000_000).zfill(6)


def _get_server_time() -> int:
    r = core.safe_request(
        "GET",
        "https://open.spotify.com/api/server-time",
        headers={"User-Agent": _UA, "Accept": "application/json"},
        timeout=10,
    )
    if r.status_code == 200:
        data = r.json()
        if data.get("serverTime"):
            return int(data["serverTime"])
    return int(time.time())


def _mint_access_token():
    server_time = _get_server_time()
    local_time = int(time.time())

    totp = _totp(_TOTP_SECRET, local_time)
    totp_server = _totp(_TOTP_SECRET, server_time)

    url = (
        "https://open.spotify.com/api/token"
        f"?reason=init&productType=web-player"
        f"&totp={totp}&totpServer={totp_server}&totpVer={_TOTP_VERSION}"
    )
    r = core.safe_request(
        "GET", url, headers={"User-Agent": _UA, "Accept": "application/json"}, timeout=15
    )
    if r.status_code == 200:
        data = r.json()
        if data.get("accessToken"):
            return {
                "access_token": data["accessToken"],
                "expires_at": data["accessTokenExpirationTimestampMs"] / 1000.0,
            }
    return None


def _mint_client_token(access_token: str) -> str:
    payload = {
        "client_data": {
            "client_version": _APP_VERSION,
            "client_id": "d8a5ed958d274c2e8ee717e6a4b0971d",
            "js_sdk_data": {
                "device_brand": "unknown",
                "device_model": "unknown",
                "os": "windows",
                "os_version": "10.0.0",
                "device_id": "unknown",
                "device_type": "computer",
            },
        }
    }
    r = core.safe_request(
        "POST",
        "https://clienttoken.spotify.com/v1/clienttoken",
        headers={
            "User-Agent": _UA,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
        json=payload,
        timeout=15,
    )
    if r.status_code == 200:
        return r.json().get("granted_token", {}).get("token", "")
    return ""


def _get_tokens():
    now = time.time()
    if _token_cache.get("access_token") and _token_cache.get("expires_at", 0) > now + 60:
        return _token_cache["access_token"], _token_cache.get("client_token", "")

    minted = _mint_access_token()
    if not minted:
        print("[Spotify] failed to mint a fresh access token — TOTP secret may have rotated")
        return "", ""

    access = minted["access_token"]
    client = _mint_client_token(access)
    _token_cache.update(
        access_token=access,
        expires_at=minted["expires_at"],
        client_token=client,
    )
    return access, client


def check(username: str, callback):
    access, client_token = _get_tokens()
    if not access:
        return

    url = (
        f"https://spclient.wg.spotify.com/user-profile-view/v3/profile/{username}"
        "?playlist_limit=10&artist_limit=10&episode_limit=10&market=DE"
    )
    headers = {
        "User-Agent": _UA,
        "Accept": "application/x-protobuf",
        "Accept-Language": "en",
        "Referer": "https://open.spotify.com/",
        "app-platform": "WebPlayer",
        "spotify-app-version": _APP_VERSION,
        "Authorization": f"Bearer {access}",
        "Origin": "https://open.spotify.com",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
    }
    if client_token:
        headers["client-token"] = client_token

    r = core.safe_request("GET", url, headers=headers, timeout=15)
    
    if r.status_code == 200:
        strings = re.findall(rb"[ -~]{4,}", r.content)
        decoded = [s.decode("utf-8", errors="ignore") for s in strings]

        details_list = []
        playlists = set()

        for i, s in enumerate(decoded):
            if f"spotify:user:{username.lower()}" in s.lower():
                if i + 1 < len(decoded):
                    nxt = decoded[i + 1].strip()
                    if nxt and not nxt.startswith("spotify") and not nxt.startswith("http"):
                        details_list.append(f"Name: {nxt}")
                break

        for s in decoded:
            if "https://i.scdn.co/" in s and not any(
                d.startswith("Avatar") for d in details_list
            ):
                m = re.search(r"(https://i\.scdn\.co/[^\s]+)", s)
                if m:
                    details_list.append(f"Avatar: {m.group(1)}")
            for m in re.findall(r"spotify:playlist:([a-zA-Z0-9]+)", s):
                playlists.add(m)

        if playlists:
            details_list.append(f"Playlists: {len(playlists)}")

        callback({
            "site": SITE,
            "status": "Found",
            "details": " | ".join(details_list) if details_list else "Profile found",
            "tool": "Native Check",
            "url": f"https://open.spotify.com/user/{username}",
        })
        
    elif r.status_code == 404:
        # Uživatel neexistuje
        callback({
            "site": SITE,
            "status": "Not Found",
            "details": "Profile does not exist",
            "tool": "Native Check",
            "url": "",
        })
    elif r.status_code in (401, 403):
        print(f"[Spotify] still blocked (status {r.status_code}) — TOTP secret/version may have rotated")
    else:
        print(f"[Spotify] unexpected status {r.status_code}")
