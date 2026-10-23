#!/usr/bin/env python3
"""Small Supabase-backed memory CLI for a personal AI brain."""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


def load_env():
    path = Path(__file__).parent.parent / ".env"
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")


def require_credentials():
    if not SUPABASE_URL or not SUPABASE_KEY:
        sys.exit("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")


def headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def request(method, url, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=body, headers=headers(), method=method)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read() or b"null")


def embedding(text):
    if not GEMINI_KEY:
        return None
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-embedding-001:embedContent?key={GEMINI_KEY}"
    )
    payload = {
        "content": {"parts": [{"text": text}]},
        "outputDimensionality": 1536,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())["embedding"]["values"]


def capture(text, thought_type=None, topic=None):
    require_credentials()
    metadata = {k: v for k, v in {"type": thought_type, "topic": topic}.items() if v}
    result = request(
        "POST",
        f"{SUPABASE_URL}/rest/v1/rpc/upsert_thought",
        {"p_content": text, "p_payload": metadata},
    )
    vector = embedding(text)
    if vector and result.get("id"):
        request(
            "PATCH",
            f"{SUPABASE_URL}/rest/v1/thoughts?id=eq.{result['id']}",
            {"embedding": vector},
        )
    print(f"Captured: {result.get('id', 'unknown')}")


def search(query, limit=10):
    require_credentials()
    vector = embedding(query)
    if not vector:
        sys.exit("Search requires GEMINI_API_KEY. Capture and list work without it.")
    rows = request(
        "POST",
        f"{SUPABASE_URL}/rest/v1/rpc/match_thoughts",
        {"query_embedding": vector, "match_threshold": 0.5, "match_count": limit},
    )
    for row in rows:
        print(f"[{row['similarity']:.2f}] {row['created_at'][:10]}  {row['content']}")


def recent(days=30, limit=20):
    require_credentials()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    params = urllib.parse.urlencode(
        {"created_at": f"gte.{since}", "order": "created_at.desc", "limit": limit}
    )
    rows = request("GET", f"{SUPABASE_URL}/rest/v1/thoughts?{params}")
    for row in rows:
        print(f"{row['created_at'][:10]}  {row['content']}")


def main():
    parser = argparse.ArgumentParser(description="Shared AI memory via Supabase")
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("capture")
    add.add_argument("text")
    add.add_argument("--type")
    add.add_argument("--topic")
    find = commands.add_parser("search")
    find.add_argument("query")
    find.add_argument("--limit", type=int, default=10)
    show = commands.add_parser("list")
    show.add_argument("--days", type=int, default=30)
    show.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    if args.command == "capture":
        capture(args.text, args.type, args.topic)
    elif args.command == "search":
        search(args.query, args.limit)
    else:
        recent(args.days, args.limit)


if __name__ == "__main__":
    main()
