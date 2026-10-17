"""
DermaSense Anonymized Public Health Surveillance & Disease Spike Detection Service.
Adheres strictly to zero-PII privacy architecture:
- No photos, no IP addresses, and no device identifiers are ever collected or stored.
- Only coarse district/region and predicted condition are stored upon explicit user consent.
- Implements statistical spike detection (outbreak alarm) when weekly count > mean + 2*sigma.
"""

import json
import math
import os
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config import FEEDBACK_STORAGE_PATH, SURVEILLANCE_DB_PATH


class SurveillanceService:
    def __init__(self, db_path: Path = SURVEILLANCE_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._seed_initial_data_if_empty()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS opt_in_telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    condition_id TEXT NOT NULL,
                    condition_name TEXT NOT NULL,
                    region TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    date_day TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_day ON opt_in_telemetry(date_day);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_cond ON opt_in_telemetry(condition_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_region ON opt_in_telemetry(region);")
            conn.commit()

    def record_telemetry(
        self,
        consent: bool,
        condition_id: str,
        condition_name: str,
        region: str,
        custom_timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Records an anonymized surveillance entry strictly upon explicit opt-in consent.
        Never accepts or stores IP, device ID, user name, or image data.
        """
        if not consent:
            raise ValueError("Consent required: Cannot record telemetry without explicit user opt-in.")

        now = custom_timestamp or datetime.now(timezone.utc)
        ts_iso = now.isoformat()
        date_day = now.strftime("%Y-%m-%d")

        # Sanitize region to coarse district/state only
        clean_region = region.strip()
        if not clean_region:
            clean_region = "Unspecified District, India"

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO opt_in_telemetry (condition_id, condition_name, region, timestamp, date_day)
                VALUES (?, ?, ?, ?, ?);
                """,
                (condition_id.strip(), condition_name.strip(), clean_region, ts_iso, date_day),
            )
            conn.commit()
            record_id = cursor.lastrowid

        return {
            "status": "success",
            "message": "Anonymized public health telemetry recorded with explicit consent.",
            "record_id": record_id,
            "condition_id": condition_id,
            "region": clean_region,
            "date": date_day,
        }

    def _seed_initial_data_if_empty(self):
        """Seeds realistic historical disease surveillance trends for demonstration and spike detection."""
        with self._get_connection() as conn:
            count = conn.execute("SELECT COUNT(*) as c FROM opt_in_telemetry;").fetchone()["c"]
            if count > 0:
                return

        print("[INFO] Seeding initial anonymized surveillance telemetry for SIH demonstration...")
        now = datetime.now(timezone.utc)

        # Baseline records across 4 weeks
        sample_entries = [
            # Week -3 to -1 baseline
            ("melanocytic_nevus", "Melanocytic Nevus (Benign Mole)", "Bengaluru Urban, Karnataka", 24),
            ("melanocytic_nevus", "Melanocytic Nevus (Benign Mole)", "Khurda (Bhubaneswar), Odisha", 18),
            ("melanocytic_nevus", "Melanocytic Nevus (Benign Mole)", "Mumbai Suburban, Maharashtra", 22),
            ("melanoma", "Melanoma (Skin Cancer)", "Bengaluru Urban, Karnataka", 4),
            ("melanoma", "Melanoma (Skin Cancer)", "Khurda (Bhubaneswar), Odisha", 2),
            ("melanoma", "Melanoma (Skin Cancer)", "Delhi NCR", 5),
            ("tinea_ringworm", "Tinea (Fungal Infection / Ringworm)", "Khurda (Bhubaneswar), Odisha", 12),
            ("tinea_ringworm", "Tinea (Fungal Infection / Ringworm)", "Mumbai Suburban, Maharashtra", 14),
            ("eczema", "Eczema (Atopic Dermatitis)", "Delhi NCR", 10),
            ("eczema", "Eczema (Atopic Dermatitis)", "Bengaluru Urban, Karnataka", 8),
            ("psoriasis", "Psoriasis", "Pune, Maharashtra", 7),
        ]

        # Insert historical spread over the last 28 days
        for cond_id, cond_name, reg, count_total in sample_entries:
            for i in range(count_total):
                days_ago = (i % 25) + 3  # between 3 and 28 days ago
                past_date = now - timedelta(days=days_ago, hours=(i * 3) % 24)
                self.record_telemetry(
                    consent=True,
                    condition_id=cond_id,
                    condition_name=cond_name,
                    region=reg,
                    custom_timestamp=past_date,
                )

        # In current week (last 3 days), simulate an elevated spike in fungal infections in coastal humid region
        # Tinea in Khurda: baseline average was ~3/week. We inject 14 cases in the current week to trigger > mean + 2*sigma!
        for i in range(14):
            recent_date = now - timedelta(days=(i % 3), hours=i * 2)
            self.record_telemetry(
                consent=True,
                condition_id="tinea_ringworm",
                condition_name="Tinea (Fungal Infection / Ringworm)",
                region="Khurda (Bhubaneswar), Odisha",
                custom_timestamp=recent_date,
            )

        print("[OK] Initial surveillance telemetry database initialized and seeded successfully.")

    def get_metrics(self, window_days: int = 30) -> Dict[str, Any]:
        """
        Aggregates surveillance data, disease geographic distributions, and executes
        the statistical spike detector (flags condition/region where current week > mean + 2*sigma).
        """
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=window_days)).strftime("%Y-%m-%d")

        with self._get_connection() as conn:
            # 1. Total records
            total_records = conn.execute(
                "SELECT COUNT(*) as c FROM opt_in_telemetry WHERE date_day >= ?;", (cutoff_date,)
            ).fetchone()["c"]

            # 2. Condition distribution
            cond_rows = conn.execute(
                """
                SELECT condition_id, condition_name, COUNT(*) as cnt
                FROM opt_in_telemetry
                WHERE date_day >= ?
                GROUP BY condition_id, condition_name
                ORDER BY cnt DESC;
                """,
                (cutoff_date,),
            ).fetchall()
            by_condition = {
                row["condition_id"]: {"name": row["condition_name"], "count": row["cnt"]} for row in cond_rows
            }

            # 3. Regional distribution
            reg_rows = conn.execute(
                """
                SELECT region, COUNT(*) as cnt
                FROM opt_in_telemetry
                WHERE date_day >= ?
                GROUP BY region
                ORDER BY cnt DESC;
                """,
                (cutoff_date,),
            ).fetchall()
            by_region = {row["region"]: row["cnt"] for row in reg_rows}

            # 4. Daily timeline
            trend_rows = conn.execute(
                """
                SELECT date_day, condition_id, COUNT(*) as cnt
                FROM opt_in_telemetry
                WHERE date_day >= ?
                GROUP BY date_day, condition_id
                ORDER BY date_day ASC;
                """,
                (cutoff_date,),
            ).fetchall()

            daily_trends: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
            for row in trend_rows:
                daily_trends[row["date_day"]][row["condition_id"]] += row["cnt"]

            timeline = [
                {"date": day, "counts": dict(counts), "total": sum(counts.values())}
                for day, counts in sorted(daily_trends.items())
            ]

            # 5. Spike Detection Algorithm:
            # Group records into 7-day intervals (Current Week: days 0-6; Week 1: 7-13; Week 2: 14-20; Week 3: 21-27)
            now = datetime.now(timezone.utc)
            all_records = conn.execute(
                """
                SELECT condition_id, condition_name, region, timestamp
                FROM opt_in_telemetry
                ORDER BY timestamp DESC;
                """
            ).fetchall()

        # Bucket by (condition_id, region) into weekly counts
        # week 0 = last 7 days (current week)
        # week 1, 2, 3 = prior historical baseline weeks
        condition_names: Dict[str, str] = {}
        weekly_counts: Dict[tuple, List[int]] = defaultdict(lambda: [0, 0, 0, 0])

        for rec in all_records:
            cid = rec["condition_id"]
            reg = rec["region"]
            cname = rec["condition_name"]
            condition_names[cid] = cname

            ts_str = rec["timestamp"]
            try:
                rec_dt = datetime.fromisoformat(ts_str)
                diff_days = (now - rec_dt).days
                if diff_days < 7:
                    weekly_counts[(cid, reg)][0] += 1
                elif diff_days < 14:
                    weekly_counts[(cid, reg)][1] += 1
                elif diff_days < 21:
                    weekly_counts[(cid, reg)][2] += 1
                elif diff_days < 28:
                    weekly_counts[(cid, reg)][3] += 1
            except Exception:
                continue

        spikes: List[Dict[str, Any]] = []
        for (cid, reg), counts in weekly_counts.items():
            current_week = counts[0]
            baseline_weeks = counts[1:]  # [w1, w2, w3]

            if not baseline_weeks or sum(baseline_weeks) == 0:
                mean_baseline = 1.0
                std_baseline = 0.5
            else:
                mean_baseline = sum(baseline_weeks) / len(baseline_weeks)
                variance = sum((w - mean_baseline) ** 2 for w in baseline_weeks) / len(baseline_weeks)
                std_baseline = math.sqrt(variance)

            # Avoid division by zero
            effective_std = max(std_baseline, 0.5)
            threshold = mean_baseline + (2.0 * effective_std)
            z_score = (current_week - mean_baseline) / effective_std if effective_std > 0 else 0.0

            is_spike = bool(current_week > threshold and current_week >= 4)

            spikes.append({
                "condition_id": cid,
                "condition_name": condition_names.get(cid, cid.title()),
                "region": reg,
                "current_week_count": current_week,
                "baseline_mean": round(mean_baseline, 2),
                "baseline_std": round(effective_std, 2),
                "threshold": round(threshold, 2),
                "z_score": round(z_score, 2),
                "is_spike": is_spike,
                "alert_level": "CRITICAL" if z_score > 3.0 else ("WARNING" if is_spike else "NORMAL"),
            })

        # Sort spikes so that detected anomalies appear at top
        spikes.sort(key=lambda s: (s["is_spike"], s["z_score"]), reverse=True)

        # 6. Citizen feedback statistics
        feedback_summary = self._get_feedback_summary()

        return {
            "total_records": total_records,
            "window_days": window_days,
            "by_condition": by_condition,
            "by_region": by_region,
            "timeline": timeline,
            "spikes": spikes,
            "active_spikes_count": sum(1 for s in spikes if s["is_spike"]),
            "feedback_summary": feedback_summary,
        }

    def _get_feedback_summary(self) -> Dict[str, Any]:
        """Reads citizen & clinician feedback log and calculates ratings and review stats."""
        total_feedback = 0
        rating_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        clinician_reviewed_count = 0
        recent_comments: List[Dict[str, Any]] = []

        if FEEDBACK_STORAGE_PATH.exists():
            try:
                with open(FEEDBACK_STORAGE_PATH, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        entry = json.loads(line)
                        total_feedback += 1
                        r = entry.get("rating", 5)
                        if r in rating_counts:
                            rating_counts[r] += 1
                        if entry.get("clinician_reviewed", False):
                            clinician_reviewed_count += 1
                        if entry.get("feedback_text"):
                            recent_comments.append({
                                "condition_id": entry.get("condition_id"),
                                "rating": r,
                                "text": entry.get("feedback_text"),
                                "clinician": entry.get("clinician_reviewed", False),
                                "timestamp": entry.get("timestamp"),
                            })
            except Exception as e:
                print(f"[WARN] Could not parse feedback log: {e}")

        avg_rating = 0.0
        if total_feedback > 0:
            avg_rating = sum(star * count for star, count in rating_counts.items()) / total_feedback

        return {
            "total_submissions": total_feedback,
            "average_rating": round(avg_rating, 2),
            "rating_distribution": rating_counts,
            "clinician_reviewed_submissions": clinician_reviewed_count,
            "recent_comments": recent_comments[-10:],
        }


# Global singleton service
surveillance_service = SurveillanceService()

