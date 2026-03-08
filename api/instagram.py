from flask import Flask, request, jsonify
import requests
import re
from bs4 import BeautifulSoup

app = Flask(__name__)

HEADERS = {
    "User-Agent": "Instagram 155.0.0.37.107 Android",
    "Accept-Language": "en-US,en;q=0.9"
}

def get_instagram_info(username):

    url = f"https://www.instagram.com/{username}/"
    r = requests.get(url, headers=HEADERS)

    if r.status_code != 200:
        return None

    html = r.text
    soup = BeautifulSoup(html, "html.parser")

    data = {
        "username": username,
        "full_name": None,
        "biography": None,
        "followers": None,
        "following": None,
        "posts": None,
        "profile_pic_url": None,
        "is_verified": None
    }

    # description meta
    meta = soup.find("meta", attrs={"name": "description"})
    if meta:
        content = meta.get("content")

        followers = re.search(r"([\d,.]+)\sFollowers", content)
        following = re.search(r"([\d,.]+)\sFollowing", content)
        posts = re.search(r"([\d,.]+)\sPosts", content)

        if followers:
            data["followers"] = followers.group(1)

        if following:
            data["following"] = following.group(1)

        if posts:
            data["posts"] = posts.group(1)

    # profile pic
    img = soup.find("meta", property="og:image")
    if img:
        data["profile_pic_url"] = img.get("content")

    # title
    title = soup.find("title")
    if title:
        data["full_name"] = title.text.replace(" • Instagram photos and videos", "")

    # verified
    if "Verified" in html:
        data["is_verified"] = True

    return data


@app.route("/")
def home():

    return jsonify({
        "success": True,
        "name": "Instagram Info API",
        "developer": "@TEAMRAX0",
        "owner": "@raxforpvt",
        "routes": "/api/instagram?username=username"
    })


@app.route("/api/instagram")
def instagram():

    username = request.args.get("username")

    if not username:
        return jsonify({
            "success": False,
            "error": "username required"
        })

    info = get_instagram_info(username)

    if not info:
        return jsonify({
            "success": False,
            "error": "user not found"
        })

    return jsonify({
        "success": True,
        "source": "instagram_public",
        "developer": "@TEAMRAX0",
        "owner": "@raxforpvt",
        "data": info
    })


if __name__ == "__main__":
    app.run(debug=True)
