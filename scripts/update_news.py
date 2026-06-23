"""Daily news brief updater — called by daily.yml"""
import json
import os
from datetime import datetime, timezone, timedelta
import anthropic

JST = timezone(timedelta(hours=9))

CATEGORIES = {
    "ai_video": {"label": "AI Video", "icon": "🎬", "query": "AI video generation tools Kling Sora Runway Luma 2026"},
    "ai_agents": {"label": "AI Agents", "icon": "🤖", "query": "AI agents automation Claude GPT autonomous 2026"},
    "cold_email": {"label": "Cold Email", "icon": "📧", "query": "cold email outreach deliverability Gmail 2026"},
    "shopify_ec": {"label": "Shopify / EC", "icon": "🛒", "query": "Shopify ecommerce DTC trends 2026"},
    "competitors": {"label": "Competitors", "icon": "⚔️", "query": "AI video production agency funding news 2026"},
    "social_algo": {"label": "Instagram / TikTok", "icon": "📱", "query": "TikTok Instagram algorithm video reach 2026"}
}

def generate_news_for_category(client, category_key, category):
    prompt = f"""You are a market intelligence researcher for Vidcel, an AI video production agency serving Shopify/DTC brands.

Generate 3 realistic, concise news headlines for the category: {category['label']}
Search context: {category['query']}
Today's date: {datetime.now(JST).strftime('%Y-%m-%d')}

Return ONLY a JSON array of 3 objects with these exact fields:
- title: headline (max 80 chars)
- source: publication name
- url: "#"
- time: relative time like "2h ago", "5h ago", "1d ago"
- hot: boolean (true if especially important/viral)

Example:
[
  {{"title": "Kling 2.1 adds 4K60fps output", "source": "TechCrunch", "url": "#", "time": "3h ago", "hot": true}},
  {{"title": "Shopify merchants see 34% video ROAS lift", "source": "AdWeek", "url": "#", "time": "6h ago", "hot": false}},
  {{"title": "Instagram reduces reach for text-only posts", "source": "Social Media Today", "url": "#", "time": "12h ago", "hot": false}}
]"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}]
    )
    text = message.content[0].text.strip()
    # Extract JSON array
    start = text.find('[')
    end = text.rfind(']') + 1
    if start >= 0 and end > start:
        return json.loads(text[start:end])
    return []

def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("No ANTHROPIC_API_KEY — skipping news update")
        return

    client = anthropic.Anthropic(api_key=api_key)
    now = datetime.now(JST).isoformat()

    news_data = {
        "last_updated": now,
        "categories": {}
    }

    for key, cat in CATEGORIES.items():
        print(f"Generating news for {cat['label']}...")
        try:
            items = generate_news_for_category(client, key, cat)
            news_data["categories"][key] = {
                "label": cat["label"],
                "icon": cat["icon"],
                "items": items[:3]
            }
        except Exception as e:
            print(f"Error for {key}: {e}")
            # Keep existing data for this category
            try:
                with open("data/news.json") as f:
                    existing = json.load(f)
                if key in existing.get("categories", {}):
                    news_data["categories"][key] = existing["categories"][key]
            except Exception:
                pass

    with open("data/news.json", "w") as f:
        json.dump(news_data, f, indent=2, ensure_ascii=False)
    print(f"News updated at {now}")

if __name__ == "__main__":
    main()
