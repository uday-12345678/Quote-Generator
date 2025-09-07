from flask import Flask, render_template, request, jsonify
import requests
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

# Configure a session with retries
session = requests.Session()
retries = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"]
)
adapter = HTTPAdapter(max_retries=retries)
session.mount("https://", adapter)
session.mount("http://", adapter)

# Optionally suppress warnings only when we intentionally disable verification in fallback
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/get_quote")
def get_quote():
    # Normalize genre/tag
    genre = request.args.get("genre", "inspirational") or "inspirational"
    genre = genre.strip().lower()

    # If user requested fun/humor, fetch from a jokes API
    if genre in ("humor", "fun"):
        joke_url = "https://official-joke-api.appspot.com/jokes/random"
        try:
            res = session.get(joke_url, timeout=6)
            if res.status_code != 200:
                try:
                    err_msg = res.json().get("message", res.text)
                except Exception:
                    err_msg = res.text
                logging.warning("Joke API error: %s (status %s)", err_msg, res.status_code)
                return jsonify({
                    "success": False,
                    "quote": None,
                    "author": None,
                    "tags": ["humor"],
                    "message": f"Joke API error: {err_msg}"
                })

            data = res.json()
            # official-joke-api returns 'setup' and 'punchline'
            setup = data.get("setup", "").strip()
            punchline = data.get("punchline", "").strip()
            joke_text = (setup + (" " if setup and punchline else "") + punchline).strip()

            if not joke_text:
                logging.warning("Joke API returned empty data: %s", data)
                return jsonify({
                    "success": False,
                    "quote": None,
                    "author": None,
                    "tags": ["humor"],
                    "message": "Joke API returned no joke."
                })

            return jsonify({
                "success": True,
                "quote": joke_text,
                "author": data.get("type", "Joke"),
                "tags": ["humor"],
                "message": "OK"
            })

        except requests.exceptions.RequestException as e:
            logging.exception("Network error while fetching joke")
            return jsonify({
                "success": False,
                "quote": None,
                "author": None,
                "tags": ["humor"],
                "message": f"Network error: {str(e)}"
            })

    url = "https://api.quotable.io/random"
    params = {"tags": genre}
    try:
        # Primary attempt — normal SSL verification
        res = session.get(url, params=params, timeout=6)
        if res.status_code != 200:
            try:
                err_msg = res.json().get("message", res.text)
            except ValueError:
                err_msg = res.text
            logging.warning("Quotable API error: %s (status %s)", err_msg, res.status_code)
            return jsonify({
                "success": False,
                "quote": None,
                "author": None,
                "tags": [],
                "message": f"Quotable API error: {err_msg}"
            })

        data = res.json()
        quote = data.get("content")
        author = data.get("author")
        tags = data.get("tags", [])

        if not quote or not author:
            logging.warning("Quotable API returned incomplete data: %s", data)
            return jsonify({
                "success": False,
                "quote": None,
                "author": None,
                "tags": tags,
                "message": "Quotable returned incomplete data."
            })

        return jsonify({
            "success": True,
            "quote": quote,
            "author": author,
            "tags": tags,
            "message": "OK"
        })

    except requests.exceptions.SSLError as ssl_err:
        # SSL verification failed — attempt a fallback request without verification and inform user
        logging.warning("SSL verification failed (%s). Attempting fallback without verification.", ssl_err)
        try:
            res = session.get(url, params=params, timeout=6, verify=False)
            if res.status_code == 200:
                data = res.json()
                quote = data.get("content")
                author = data.get("author")
                tags = data.get("tags", [])
                if quote and author:
                    return jsonify({
                        "success": True,
                        "quote": quote,
                        "author": author,
                        "tags": tags,
                        "message": "OK (ssl verification bypassed; update certs to fix)"
                    })
            # If fallback didn't work or returned bad status
            try:
                err_msg = res.json().get("message", res.text)
            except Exception:
                err_msg = getattr(res, "text", "Unknown error")
            return jsonify({
                "success": False,
                "quote": None,
                "author": None,
                "tags": [],
                "message": f"SSL verification failed and fallback failed: {err_msg}"
            })
        except requests.exceptions.RequestException as e:
            logging.exception("Fallback request failed after SSL error")
            return jsonify({
                "success": False,
                "quote": None,
                "author": None,
                "tags": [],
                "message": f"SSL verification failed and fallback request failed: {str(e)}"
            })
    except requests.exceptions.RequestException as e:
        logging.exception("Network error while fetching quote")
        return jsonify({
            "success": False,
            "quote": None,
            "author": None,
            "tags": [],
            "message": f"Network error: {str(e)}"
        })

if __name__ == "__main__":
    app.run(debug=True)
