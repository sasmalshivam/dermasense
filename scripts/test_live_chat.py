import json
import sys
import urllib.request
import urllib.error

# Ensure UTF-8 output in Windows terminal
sys.stdout.reconfigure(encoding="utf-8")

URL = "http://127.0.0.1:8000/api/chat"

test_cases = [
    {
        "id": 1,
        "lang": "en",
        "question": "What are the common symptoms of melanoma?",
        "condition": None,
        "desc": "English - Melanoma symptoms (general query)"
    },
    {
        "id": 2,
        "lang": "en",
        "question": "Is it contagious?",
        "condition": "melanoma",
        "desc": "English - Contextual follow-up: contagion"
    },
    {
        "id": 3,
        "lang": "en",
        "question": "What should I avoid doing?",
        "condition": "melanoma",
        "desc": "English - Contextual follow-up: do not / precautions"
    },
    {
        "id": 4,
        "lang": "en",
        "question": "What is the first aid for ringworm or tinea?",
        "condition": "tinea_ringworm",
        "desc": "English - Tinea first aid & home care"
    },
    {
        "id": 5,
        "lang": "en",
        "question": "What is the capital of Australia?",
        "condition": None,
        "desc": "English - Out-of-scope question (must return 'I don\\'t know')"
    },
    {
        "id": 6,
        "lang": "hi",
        "question": "क्या मेलानोमा एक व्यक्ति से दूसरे में फैलता है?",
        "condition": "melanoma",
        "desc": "Hindi - Melanoma contagion follow-up"
    },
    {
        "id": 7,
        "lang": "or",
        "question": "ମେଲାନୋମା ହେଲେ ମୁଁ କ'ଣ କରିବା ଉଚିତ ନୁହେଁ?",
        "condition": "melanoma",
        "desc": "Odia - Melanoma harmful practices (do_not) follow-up"
    },
    {
        "id": 8,
        "lang": "hi",
        "question": "कल का क्रिकेट मैच कौन जीता?",
        "condition": None,
        "desc": "Hindi - Out-of-scope question (must return 'I don\\'t know')"
    }
]

print("=" * 80)
print("DERMASENSE LIVE CHATBOT VERIFICATION (/api/chat)")
print("=" * 80)

for tc in test_cases:
    payload = {
        "message": tc["question"],
        "detected_condition": tc["condition"],
        "language": tc["lang"]
    }
    
    req = urllib.request.Request(
        URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"\n[Test {tc['id']}/8] {tc['desc']}")
            print(f"Language: {tc['lang'].upper()} | Context: {tc['condition']}")
            print(f"Query: {tc['question']}")
            print(f"Answer: {data.get('answer')}")
            print(f"Matched: {data.get('matched_condition')} > {data.get('section')}")
            print(f"Confidence: {data.get('confidence'):.3f} | Grounded: {data.get('grounded')}")
            sources = data.get("sources", [])
            if sources:
                print(f"Sources ({len(sources)}):")
                for s in sources[:2]:
                    print(f"  - [{s.get('title')}]: {s.get('url')}")
            else:
                print("Sources: None (Out-of-scope query rejected)")
    except urllib.error.URLError as e:
        print(f"\n[Test {tc['id']}/8] ERROR connecting to backend: {e}")
        sys.exit(1)

print("\n" + "=" * 80)
print("All 8 live chatbot endpoint tests executed successfully.")
print("=" * 80)

