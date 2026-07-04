import os
import json
import time
import feedparser
import requests

FEEDS_FILE = "feeds.txt"
SEEN_FILE = "seen_ids.json"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"


def load_feeds():
    with open(FEEDS_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_seen(seen_ids):
    # Keep the file from growing forever: cap at last 5000 IDs
    ids_list = list(seen_ids)[-5000:]
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(ids_list, f, ensure_ascii=False)


def send_telegram_message(text):
    try:
        resp = requests.post(
            TELEGRAM_API,
            data={
                "chat_id": CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"Telegram error: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")


def main():
    feeds = load_feeds()
    seen_ids = load_seen()
    new_seen_ids = set(seen_ids)

    # First run ever: don't spam with all historical items, just mark them seen.
    first_run = not os.path.exists(SEEN_FILE)

    total_new = 0

    for feed_url in feeds:
        try:
            parsed = feedparser.parse(feed_url)
        except Exception as e:
            print(f"Failed to parse feed {feed_url}: {e}")
            continue

        feed_title = parsed.feed.get("title", "Google Alert")

        for entry in parsed.entries:
            entry_id = entry.get("id") or entry.get("link")
            if not entry_id:
                continue
            if entry_id in seen_ids:
                continue

            new_seen_ids.add(entry_id)

            if first_run:
                continue  # just mark as seen, don't send on the very first run

            total_new += 1

            title = entry.get("title", "بدون عنوان")
            link = entry.get("link", "")

            message = f"<b>{feed_title}</b>\n{title}\n{link}"
            send_telegram_message(message)
            time.sleep(0.5)  # avoid hitting Telegram rate limits

    save_seen(new_seen_ids)
    print(f"Done. {total_new} new item(s) sent.")


if __name__ == "__main__":
    main()
