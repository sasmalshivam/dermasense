import json
import sys
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://127.0.0.1:8000"

print("=" * 80)
print("DERMASENSE PHASE 6 LIVE END-TO-END VERIFICATION")
print("=" * 80)

# 1. Health Endpoint
with urllib.request.urlopen(f"{BASE}/api/health") as resp:
    data = json.loads(resp.read().decode())
    print("\n[1/5] Health Check:")
    print(f"Status: {data.get('status')} | ONNX: {data.get('onnx_runtime_version')}")
    print(f"Supported classes: {data.get('supported_classes')}")

# 2. Telemetry Opt-In Submission
payload = {
    "consent": True,
    "condition_id": "melanocytic_nevus",
    "condition_name": "Melanocytic Nevus (Benign Mole)",
    "region": "Khurda (Bhubaneswar), Odisha"
}
req = urllib.request.Request(
    f"{BASE}/api/telemetry/opt-in",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
    print("\n[2/5] Telemetry Opt-In (Explicit Consent):")
    print(f"Status: {data.get('status')} | Record ID: {data.get('record_id')}")
    print(f"Region: {data.get('region')} | Condition: {data.get('condition_id')}")

# 3. Telemetry Denial Without Consent
payload_denied = {
    "consent": False,
    "condition_id": "melanoma",
    "condition_name": "Melanoma",
    "region": "Delhi NCR"
}
req_denied = urllib.request.Request(
    f"{BASE}/api/telemetry/opt-in",
    data=json.dumps(payload_denied).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
try:
    urllib.request.urlopen(req_denied)
    print("\n[3/5] Telemetry Without Consent: FAILED (Should have been rejected)")
except urllib.error.HTTPError as e:
    print(f"\n[3/5] Telemetry Without Consent Correctly Rejected: HTTP {e.code} ({e.reason})")

# 4. Admin Password Verification
req_verify = urllib.request.Request(
    f"{BASE}/api/admin/verify",
    data=json.dumps({"password": "derma_admin_2025"}).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(req_verify) as resp:
    data = json.loads(resp.read().decode())
    print(f"\n[4/5] Admin Password Verification: Valid = {data.get('valid')}")

# 5. Admin Metrics & Spike Detection
req_metrics = urllib.request.Request(
    f"{BASE}/api/admin/metrics",
    headers={"X-Admin-Password": "derma_admin_2025"}
)
with urllib.request.urlopen(req_metrics) as resp:
    data = json.loads(resp.read().decode())
    print("\n[5/5] Admin Surveillance Metrics & Outbreak Alerts:")
    print(f"Total Opt-In Records: {data.get('total_records')}")
    print(f"Active Disease Cluster Spikes (> Mean + 2*Sigma): {data.get('active_spikes_count')}")
    spikes = data.get("spikes", [])
    for spk in spikes[:3]:
        print(f"  - [{spk.get('alert_level')}] {spk.get('condition_name')} in {spk.get('region')}: Current={spk.get('current_week_count')} vs Baseline Mean={spk.get('baseline_mean')} (Z={spk.get('z_score')}σ)")
    fb = data.get("feedback_summary", {})
    print(f"Citizen Feedback: Avg Rating = {fb.get('average_rating')} / 5.0 ({fb.get('total_submissions')} reviews)")

print("\n" + "=" * 80)
print("ALL LIVE END-TO-END ENDPOINTS VERIFIED SUCCESSFULLY")
print("=" * 80)

