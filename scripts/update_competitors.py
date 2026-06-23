"""Weekly competitor intel updater — called by weekly.yml"""
import json
import os
from datetime import datetime, timezone, timedelta
import anthropic

JST = timezone(timedelta(hours=9))

COMPETITORS = ["VidAI Agency", "Pictory Pro Agency", "HeyGen Studios"]

def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("No ANTHROPIC_API_KEY — skipping competitor update")
        return

    client = anthropic.Anthropic(api_key=api_key)
    today = datetime.now(JST).strftime('%Y-%m-%d')

    with open("data/competitors.json") as f:
        existing = json.load(f)

    prompt = f"""You are a competitive intelligence analyst for Vidcel, an AI video production agency for Shopify/DTC brands.
Today is {today}.

Based on the current AI video production agency market, provide updated competitive intelligence.
Include Vidcel (our company) as one entry. Competitors: {', '.join(COMPETITORS)}.

Return JSON array of competitor objects with these fields:
- id: string slug
- name: string
- founded: year string
- funding: funding description
- pricing: price range string
- strengths: array of 3 strings
- weaknesses: array of 3 strings
- radar: object with keys quality/speed/price/support/innovation/retention, values 0-100

Be honest and realistic. Vidcel should have strengths in quality and support but weaknesses in scale."""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}]
    )
    text = message.content[0].text.strip()
    start = text.find('[')
    end = text.rfind(']') + 1
    if start >= 0 and end > start:
        competitors = json.loads(text[start:end])
        existing["competitors"] = competitors
        existing["last_updated"] = datetime.now(JST).isoformat()
        with open("data/competitors.json", "w") as f:
            json.dump(existing, f, indent=2)
        print("Competitor data updated")
    else:
        print("Failed to parse competitors JSON")

if __name__ == "__main__":
    main()
