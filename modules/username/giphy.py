import core

SITE = "Giphy"
DOMAINS = ["giphy.com"]


def check(username, callback):
    r = core.safe_request(
        "GET",
        f"https://api.giphy.com/v1/channels/{username}"
        f"?api_key=Gc7131jiJuvI7IdN0HZ1D7nh0ow5BU6g",
    )
    if r.status_code == 200:
        callback({
            "site": SITE,
            "status": "Found",
            "details": "",
            "tool": "Native Check",
            "url": f"https://giphy.com/channel/{username}",
        })


def enrich(url):
    user = url.strip("/").split("/")[-1]
    custom_data = {}
    image_url = None
    try:
        r = core.safe_request(
            "GET",
            f"https://api.giphy.com/v1/channels/{user}"
            f"?api_key=Gc7131jiJuvI7IdN0HZ1D7nh0ow5BU6g",
        )
        if r.status_code == 200:
            data = r.json()
            if "data" in data:
                cid = data["data"].get("id")
                if cid:
                    custom_data["ID"] = str(cid)
                if "user" in data["data"]:
                    ui = data["data"]["user"]
                    if ui.get("avatar_url"):
                        image_url = ui["avatar_url"]
                    if ui.get("username"):
                        custom_data["Username"] = ui["username"]
                if cid:
                    rf = core.safe_request(
                        "GET", f"https://giphy.com/api/v4/channels/{cid}/feed"
                    )
                    if rf.status_code == 200 and "results" in rf.json():
                        custom_data["Total GIFs"] = str(len(rf.json()["results"]))
    except Exception:
        pass

    ab = None
    if image_url:
        try:
            ab = core.safe_request("GET", image_url).content
        except Exception:
            pass

        return {"api_data": custom_data, "avatar_bytes": ab, "avatar_url": image_url}
