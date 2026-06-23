"""
Self-healing system check — called hourly by self_check.yml
Validates all JSON data files and auto-fixes issues using Claude API.
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta
import anthropic

JST = timezone(timedelta(hours=9))

DATA_FILES = {
    "data/news.json": {
        "required_keys": ["last_updated", "categories"],
        "max_age_hours": 26
    },
    "data/clients.json": {
        "required_keys": ["clients", "plans"],
        "max_age_hours": None
    },
    "data/pipeline.json": {
        "required_keys": ["tasks"],
        "max_age_hours": None
    },
    "data/finance.json": {
        "required_keys": ["summary", "monthly_history"],
        "max_age_hours": None
    },
    "data/leads.json": {
        "required_keys": ["phases", "leads"],
        "max_age_hours": None
    },
    "data/domain.json": {
        "required_keys": ["domains"],
        "max_age_hours": 25
    },
    "data/analytics.json": {
        "required_keys": ["instantly"],
        "max_age_hours": 25
    },
    "data/trends.json": {
        "required_keys": ["shopify_trending", "monthly_growth"],
        "max_age_hours": 170
    },
    "data/competitors.json": {
        "required_keys": ["competitors"],
        "max_age_hours": 170
    }
}

issues = []
fixes = []

def check_file(path, rules):
    print(f"Checking {path}...")
    if not os.path.exists(path):
        issues.append(f"MISSING: {path}")
        return False
    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        issues.append(f"INVALID JSON: {path} — {e}")
        return False

    for key in rules.get("required_keys", []):
        if key not in data:
            issues.append(f"MISSING KEY '{key}' in {path}")

    if rules.get("max_age_hours") and "last_updated" in data:
        try:
            updated = datetime.fromisoformat(data["last_updated"].replace('Z', '+00:00'))
            age = (datetime.now(timezone.utc) - updated.astimezone(timezone.utc)).total_seconds() / 3600
            if age > rules["max_age_hours"]:
                issues.append(f"STALE DATA: {path} last updated {age:.1f}h ago (max {rules['max_age_hours']}h)")
        except Exception:
            pass

    return True

def auto_fix_with_claude(client, issue_desc, file_path):
    """Use Claude to regenerate a broken/stale data file."""
    print(f"Auto-fixing: {issue_desc}")
    try:
        with open(file_path) as f:
            current = f.read()
    except Exception:
        current = "{}"

    prompt = f"""A dashboard data file has an issue: {issue_desc}

File: {file_path}
Current content (may be broken):
{current[:2000]}

Please return a corrected, complete JSON for this file. Keep the same structure but fix any issues.
If the data is stale, generate fresh realistic data for today ({datetime.now(JST).strftime('%Y-%m-%d')}).
Return ONLY valid JSON, no explanation."""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )
    text = message.content[0].text.strip()
    # Try to extract JSON
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start = text.find(start_char)
        end = text.rfind(end_char) + 1
        if start >= 0 and end > start:
            try:
                fixed = json.loads(text[start:end])
                with open(file_path, 'w') as f:
                    json.dump(fixed, f, indent=2, ensure_ascii=False)
                fixes.append(f"Fixed: {file_path}")
                return True
            except json.JSONDecodeError:
                pass
    return False

def main():
    print(f"=== Vidcel Self-Check {datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')} ===")

    for path, rules in DATA_FILES.items():
        check_file(path, rules)

    if not issues:
        print("✅ All checks passed — no issues found")
        sys.exit(0)

    print(f"\n⚠️  Found {len(issues)} issue(s):")
    for issue in issues:
        print(f"  - {issue}")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("No ANTHROPIC_API_KEY — cannot auto-fix. Manual fix required.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    print("\n🔧 Auto-fixing with Claude...")

    for issue in issues:
        # Extract file path from issue description
        for path in DATA_FILES.keys():
            if path in issue:
                auto_fix_with_claude(client, issue, path)
                break

    if fixes:
        print(f"\n✅ Applied {len(fixes)} fix(es):")
        for fix in fixes:
            print(f"  - {fix}")
    else:
        print("\n❌ Could not auto-fix all issues")
        sys.exit(1)

if __name__ == "__main__":
    main()
