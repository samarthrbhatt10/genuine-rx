import urllib.request, json, time

time.sleep(2)

API = "http://localhost:8000/api/v1"

# 1. Resolve Crocin
req = urllib.request.Request(
    f"{API}/resolve-medicine",
    data=json.dumps({"raw_text": "Crocin", "source": "typed"}).encode(),
    headers={"Content-Type": "application/json"},
)
data = json.loads(urllib.request.urlopen(req).read())
print("Resolve Crocin:", data)

# 2. Substitutes
mid = data["medicine_id"]
subs = json.loads(urllib.request.urlopen(f"{API}/medicines/{mid}/substitutes").read())
print(f"Substitutes count: {len(subs['substitutes'])}")
print("Top substitute:", subs["substitutes"][0])

# 3. Tracked medicines for user 1
tracked = json.loads(urllib.request.urlopen(f"{API}/users/1/tracked-medicines").read())
print(f"User 1 tracked: {len(tracked)} medicines")
for t in tracked:
    hist = t.get("history", [])
    print(f"  {t['brand_name']} ({t['profile_label']}): Rs.{t['latest_price']} | {len(hist)} history pts")

# 4. Track Atorva for user 1
req4 = urllib.request.Request(
    f"{API}/tracked-medicines",
    data=json.dumps({"user_id": 1, "medicine_id": 32, "profile_label": "self"}).encode(),
    headers={"Content-Type": "application/json"},
)
print("Track Atorva:", json.loads(urllib.request.urlopen(req4).read()))

# 5. Confirm it persisted
tracked2 = json.loads(urllib.request.urlopen(f"{API}/users/1/tracked-medicines").read())
print(f"User 1 now tracking: {len(tracked2)} medicines")
