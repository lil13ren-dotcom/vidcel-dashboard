"""Weekly Shopify trends updater — called by weekly.yml"""
import json
import os
from datetime import datetime, timezone, timedelta
import anthropic

JST = timezone(timedelta(hours=9))

def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("No ANTHROPIC_API_KEY — skipping trends update")
        return

    client = anthropic.Anthropic(api_key=api_key)
    today = datetime.now(JST).strftime('%Y-%m-%d')

    prompt = f"""You are a Shopify/DTC market analyst. Today is {today}.

Analyze current Shopify trending product categories for DTC brands using AI video marketing.
Return a JSON object with this exact structure:

{{
  "last_updated": "{datetime.now(JST).isoformat()}",
  "shopify_trending": [
    {{
      "category": "Category Name",
      "trend": "up"|"stable"|"down",
      "growth": <integer percent, can be negative>,
      "competition": "low"|"medium"|"high",
      "video_potential": "high"|"medium"|"low",
      "notes": "one short sentence insight"
    }}
  ],
  "monthly_growth": [
    {{"month": "Jan", "ai_gadgets": 22, "functional_bev": 35, "pet": 18, "beauty": 28}},
    ...6 months...
  ]
}}

Include 8 categories. Be realistic about current market conditions."""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}]
    )
    text = message.content[0].text.strip()
    start = text.find('{')
    end = text.rfind('}') + 1
    if start >= 0 and end > start:
        data = json.loads(text[start:end])
        with open("data/trends.json", "w") as f:
            json.dump(data, f, indent=2)
        print("Trends updated")
    else:
        print("Failed to parse trends JSON")

if __name__ == "__main__":
    main()
