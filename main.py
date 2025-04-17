# main.py
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import os
from typing import Dict, Optional
from datetime import datetime
import heapq
from collections import Counter
import hashlib
import pickle
import time
from bst import RedBlackTree

app = FastAPI(title="URL Shortener")

# Create templates directory if it doesn't exist
os.makedirs("templates", exist_ok=True)

# Create data directory if it doesn't exist
os.makedirs("data", exist_ok=True)

templates = Jinja2Templates(directory="templates")

# Constants
HASH_SIZE = 7  # Length of short URL hash
DATA_FILE = "data/url_data.pkl"
COUNTER_FILE = "data/url_counter.pkl"
TREE_FILE = "data/url_tree.pkl"

# Data structures
url_map: Dict[str, str] = {}  # Hash table: short_url -> original_url
access_counter = Counter()  # Track URL access frequency
most_frequent = []  # Heap for most frequently accessed URLs
url_tree = RedBlackTree()  # Red-Black Tree for ordered URL storage

# Cuckoo hash table
CUCKOO_SIZE = 1024
cuckoo_table1 = [None] * CUCKOO_SIZE
cuckoo_table2 = [None] * CUCKOO_SIZE


def save_data():
    """Save data structures to disk"""
    with open(DATA_FILE, "wb") as f:
        pickle.dump(url_map, f)

    with open(COUNTER_FILE, "wb") as f:
        pickle.dump(access_counter, f)

    with open(TREE_FILE, "wb") as f:
        pickle.dump(url_tree, f)


def load_data():
    """Load data structures from disk"""
    global url_map, access_counter, url_tree, most_frequent

    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "rb") as f:
                url_map = pickle.load(f)

        if os.path.exists(COUNTER_FILE):
            with open(COUNTER_FILE, "rb") as f:
                access_counter = pickle.load(f)
                # Rebuild heap from counter
                most_frequent = [(-count, url) for url, count in access_counter.items()]
                heapq.heapify(most_frequent)

        if os.path.exists(TREE_FILE):
            with open(TREE_FILE, "rb") as f:
                url_tree = pickle.load(f)
    except Exception as e:
        print(f"Error loading data: {e}")


def hash_url(url: str) -> str:
    """Generate a short hash for a URL"""
    timestamp = str(time.time())
    hash_input = url + timestamp
    return hashlib.sha256(hash_input.encode()).hexdigest()[:HASH_SIZE]


def cuckoo_hash1(key: str) -> int:
    """First hash function for cuckoo hashing"""
    return int(hashlib.md5(key.encode()).hexdigest(), 16) % CUCKOO_SIZE


def cuckoo_hash2(key: str) -> int:
    """Second hash function for cuckoo hashing"""
    return int(hashlib.sha1(key.encode()).hexdigest(), 16) % CUCKOO_SIZE


def cuckoo_insert(key: str, value: str, max_iterations: int = 100) -> bool:
    """Insert a key-value pair using cuckoo hashing"""
    for _ in range(max_iterations):
        pos1 = cuckoo_hash1(key)

        # Try first table
        if cuckoo_table1[pos1] is None or cuckoo_table1[pos1][0] == key:
            cuckoo_table1[pos1] = (key, value)
            return True

        # Kick out existing entry
        key, value, cuckoo_table1[pos1] = (
            cuckoo_table1[pos1][0],
            cuckoo_table1[pos1][1],
            (key, value),
        )

        # Try second table
        pos2 = cuckoo_hash2(key)
        if cuckoo_table2[pos2] is None or cuckoo_table2[pos2][0] == key:
            cuckoo_table2[pos2] = (key, value)
            return True

        # Kick out existing entry
        key, value, cuckoo_table2[pos2] = (
            cuckoo_table2[pos2][0],
            cuckoo_table2[pos2][1],
            (key, value),
        )

    # Rehash if we can't insert
    # In a real implementation, we would resize the tables here
    return False


def cuckoo_lookup(key: str) -> Optional[str]:
    """Look up a key in the cuckoo hash table"""
    pos1 = cuckoo_hash1(key)
    if cuckoo_table1[pos1] is not None and cuckoo_table1[pos1][0] == key:
        return cuckoo_table1[pos1][1]

    pos2 = cuckoo_hash2(key)
    if cuckoo_table2[pos2] is not None and cuckoo_table2[pos2][0] == key:
        return cuckoo_table2[pos2][1]

    return None


def update_frequency(short_url: str):
    """Update access frequency for a URL and maintain heap"""
    access_counter[short_url] += 1
    count = access_counter[short_url]

    # Update heap
    for i, (neg_count, url) in enumerate(most_frequent):
        if url == short_url:
            most_frequent[i] = (-count, short_url)
            heapq.heapify(most_frequent)
            break
    else:
        heapq.heappush(most_frequent, (-count, short_url))


@app.on_event("startup")
def startup_event():
    """Load data when app starts"""
    load_data()

    # Create HTML template if it doesn't exist
    template_path = "templates/index.html"
    if not os.path.exists(template_path):
        with open(template_path, "w") as f:
            f.write(
                """
<!DOCTYPE html>
<html>
<head>
    <title>URL Shortener</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        .container {
            background-color: #f9f9f9;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        input[type="url"] {
            width: 70%;
            padding: 10px;
            margin-right: 10px;
        }
        button {
            padding: 10px 15px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .result {
            margin-top: 20px;
            padding: 10px;
            background-color: #e9f7ef;
            border-radius: 4px;
            display: none;
        }
        .stats {
            margin-top: 30px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>URL Shortener</h1>
        
        <form action="/shorten" method="post">
            <input type="url" name="url" placeholder="Enter URL to shorten" required>
            <button type="submit">Shorten</button>
        </form>
        
        {% if short_url %}
        <div class="result" style="display: block;">
            <p>Shortened URL: <a href="{{ short_url }}" target="_blank">{{ request.base_url }}{{ short_url }}</a></p>
        </div>
        {% endif %}
        
        <div class="stats">
            <h2>Most Frequently Accessed URLs</h2>
            <table>
                <tr>
                    <th>Short URL</th>
                    <th>Original URL</th>
                    <th>Access Count</th>
                </tr>
                {% for url, data in popular_urls %}
                <tr>
                    <td><a href="{{ url }}">{{ url }}</a></td>
                    <td>{{ data.original_url }}</td>
                    <td>{{ data.count }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>
</body>
</html>
            """
            )


@app.on_event("shutdown")
def shutdown_event():
    """Save data when app shuts down"""
    save_data()


@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    """Render the index page"""
    # Get top 5 most frequently accessed URLs
    popular_urls = []
    heap_copy = most_frequent.copy()

    for _ in range(min(5, len(heap_copy))):
        if heap_copy:
            neg_count, short_url = heapq.heappop(heap_copy)
            if short_url in url_map:
                popular_urls.append(
                    (
                        short_url,
                        {"original_url": url_map[short_url], "count": -neg_count},
                    )
                )

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "popular_urls": popular_urls, "short_url": None},
    )


@app.post("/shorten", response_class=HTMLResponse)
async def shorten_url(request: Request, url: str = Form(...)):
    """Shorten a URL and return the index page with the result"""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Generate short URL
    short_hash = hash_url(url)

    # Store in hash table
    url_map[short_hash] = url

    # Store in cuckoo hash table
    cuckoo_insert(short_hash, url)

    # Add to Red-Black Tree
    url_tree.insert(short_hash, url)

    # Get top 5 most frequently accessed URLs for display
    popular_urls = []
    heap_copy = most_frequent.copy()

    for _ in range(min(5, len(heap_copy))):
        if heap_copy:
            neg_count, short_url = heapq.heappop(heap_copy)
            if short_url in url_map:
                popular_urls.append(
                    (
                        short_url,
                        {"original_url": url_map[short_url], "count": -neg_count},
                    )
                )

    # Save data
    save_data()

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "short_url": short_hash, "popular_urls": popular_urls},
    )


@app.get("/{short_url}")
async def redirect_to_url(short_url: str):
    """Redirect to the original URL"""
    # Try to get from main hash table
    original_url = url_map.get(short_url)

    if not original_url:
        # Try cuckoo hash table as backup
        original_url = cuckoo_lookup(short_url)

    if not original_url:
        # Try Red-Black Tree as tertiary lookup
        original_url = url_tree.search(short_url)

    if not original_url:
        raise HTTPException(status_code=404, detail="URL not found")

    # Update frequency and heap
    update_frequency(short_url)

    # Save data periodically (in production, would use background task)
    if access_counter[short_url] % 10 == 0:
        save_data()

    return RedirectResponse(url=original_url)


@app.get("/stats/popular")
async def get_popular_urls():
    """Get most popular URLs"""
    top_urls = []
    heap_copy = most_frequent.copy()

    for _ in range(min(10, len(heap_copy))):
        if heap_copy:
            neg_count, short_url = heapq.heappop(heap_copy)
            if short_url in url_map:
                top_urls.append(
                    {
                        "short_url": short_url,
                        "original_url": url_map[short_url],
                        "access_count": -neg_count,
                    }
                )

    return {"popular_urls": top_urls}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
