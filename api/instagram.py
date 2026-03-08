from flask import Flask, request, jsonify
import requests
import json
import re

app = Flask(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

def extract_shared_data(html: str):
    # Old pattern fallback
    m = re.search(r'window\._sharedData\s*=\s*(\{.*?\});</script>', html)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass

    # Newer JSON blobs sometimes contain "profilePage_"
    m2 = re.search(r'"profilePage_([0-9]+)"', html)
    if m2:
        # no guaranteed structured object available
        return None

    return None

def parse_meta_description(content: str):
    result = {
        "followers": None,
        "following": None,
        "posts": None,
    }
    if not content:
        return result

    followers = re.search(r'([\d.,MKmk]+)\sFollowers', content)
    following = re.search(r'([\d.,MKmk]+)\sFollowing', content)
    posts = re.search(r'([\d.,MKmk]+)\sPosts', content)

    if followers:
        result["followers"] = followers.group(1)
    if following:
        result["following"] = following.group(1)
    if posts:
        result["posts"] = posts.group(1)

    return result

def get_public_instagram_info(username: str):
    url = f"https://www.instagram.com/{username}/"
    resp = requests.get(url, headers=HEADERS, timeout=20)

    if resp.status_code != 200:
        return {"error": f"http_{resp.status_code}"}

    html = resp.text

    if "Login • Instagram" in html or 'login' in html.lower():
        return {"error": "login_required_or_blocked"}

    data = {
        "username": username,
        "full_name": None,
        "biography": None,
        "followers": None,
        "following": None,
        "posts": None,
        "profile_pic_url": None,
        "is_verified": None,
        "is_private": None,
        "external_url": None,
        "category": None,
        "recent_posts_count": 0,
        "recent_posts": []
    }

    # Meta tags fallback
    meta_desc_match = re.search(r'<meta name="description" content="([^"]+)"', html)
    if meta_desc_match:
        parsed = parse_meta_description(meta_desc_match.group(1))
        data.update(parsed)

    og_title = re.search(r'<meta property="og:title" content="([^"]+)"', html)
    if og_title:
        data["full_name"] = og_title.group(1)

    og_desc = re.search(r'<meta property="og:description" content="([^"]+)"', html)
    if og_desc:
        desc = og_desc.group(1)
        if desc:
            data["biography"] = desc

    og_image = re.search(r'<meta property="og:image" content="([^"]+)"', html)
    if og_image:
        data["profile_pic_url"] = og_image.group(1)

    # Try structured JSON if present
    shared = extract_shared_data(html)
    if shared:
        try:
            user = shared["entry_data"]["ProfilePage"][0]["graphql"]["user"]

            data["username"] = user.get("username")
            data["full_name"] = user.get("full_name")
            data["biography"] = user.get("biography")
            data["followers"] = user.get("edge_followed_by", {}).get("count")
            data["following"] = user.get("edge_follow", {}).get("count")
            data["posts"] = user.get("edge_owner_to_timeline_media", {}).get("count")
            data["profile_pic_url"] = user.get("profile_pic_url_hd") or user.get("profile_pic_url")
            data["is_verified"] = user.get("is_verified")
            data["is_private"] = user.get("is_private")
            data["external_url"] = user.get("external_url")
            data["category"] = user.get("category_name")

            edges = user.get("edge_owner_to_timeline_media", {}).get("edges", [])
            for edge in edges[:12]:
                node = edge.get("node", {})
                caption_edges = node.get("edge_media_to_caption", {}).get("edges", [])
                caption = caption_edges[0]["node"]["text"] if caption_edges else ""

                data["recent_posts"].append({
                    "shortcode": node.get("shortcode"),
                    "caption": caption,
                    "thumbnail": node.get("thumbnail_src"),
                    "display_url": node.get("display_url"),
                    "taken_at": node.get("taken_at_timestamp"),
                    "is_video": node.get("is_video")
                })

            data["recent_posts_count"] = len(data["recent_posts"])
        except Exception:
            pass

    return data

@app.route("/")
def home():
    return jsonify({
        "success": True,
        "name": "Instagram Public Info API",
        "developer": "@TEAMRAX0",
        "route": "/api/instagram?username=instagram"
    })

@app.route("/api/instagram")
def instagram():
    username = request.args.get("username", "").strip()

    if not username:
        return jsonify({
            "success": False,
            "error": "username required"
        }), 400

    if not re.fullmatch(r"[A-Za-z0-9._]+", username):
        return jsonify({
            "success": False,
            "error": "invalid username"
        }), 400

    result = get_public_instagram_info(username)

    if "error" in result:
        return jsonify({
            "success": False,
            "error": result["error"]
        }), 403

    return jsonify({
        "success": True,
        "source": "instagram_public_limited",
        "developer": "@TEAMRAX0",
        "data": result
    })

# Vercel serverless entrypoint
app = app
