"""
ARIA — Autonomous Risk Intelligence Agent

Runs as a background asyncio loop inside the admin API.
Nobody calls it. It decides when to act.

Loop:
  every CYCLE_SECS seconds:
    1. scan recent SecurityEvents (last WINDOW_MINS)
    2. cluster by user_id
    3. for clusters that meet thresholds: build explainability charts,
       synthesize hypothesis, call Qwen3.5-0.8B VLM with multi-chart image
    4. persist AriaInvestigation — admin board polls /admin/aria/investigations
"""
import asyncio, datetime, collections, os
from typing import Dict, List

CYCLE_SECS   = 60
WINDOW_MINS  = 10
MIN_CLUSTER  = 3   # minimum events in a cluster before ARIA investigates
MIN_RISK     = 0.3  # ignore noise events below this


# ── VLM helpers ───────────────────────────────────────────────────────────────

_vlm_pipe = None   # lazy-loaded transformers pipeline

def _vlm_call(grid_b64: str, hypothesis: str, event_summaries: str) -> str:
    """Call Qwen3.5-0.8B VLM. Tries remote OpenAI-compatible endpoint first, falls back to local."""
    vlm_url   = os.environ.get("VLM_API_URL")
    vlm_model = os.environ.get("VLM_MODEL", "Qwen/Qwen3.5-0.8B")
    prompt = (
        f"You are a fraud analyst reviewing a security cluster. "
        f"ARIA's hypothesis: {hypothesis}. "
        f"Event risk scores and categories: {event_summaries}. "
        "The image shows feature importance bar charts from multiple ML providers. "
        "Red bars push risk up, green push risk down. "
        "In 3-4 sentences: Does the visual evidence support or contradict the hypothesis? "
        "Which provider shows the most suspicious pattern? Any signs of false positives?"
    )
    if vlm_url:
        try:
            from openai import OpenAI
            client = OpenAI(base_url=vlm_url, api_key="EMPTY")
            resp = client.chat.completions.create(
                model=vlm_model,
                messages=[{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{grid_b64}"}},
                    {"type": "text", "text": prompt}
                ]}],
                max_tokens=512, temperature=0.7, top_p=0.8,
                extra_body={"top_k": 20, "presence_penalty": 1.5}
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f"[VLM unavailable: {e}]"
    else:
        return _vlm_local(grid_b64, prompt, vlm_model)


def _vlm_local(grid_b64: str, prompt: str, model_id: str) -> str:
    global _vlm_pipe
    try:
        import io, base64 as b64
        from PIL import Image
        if _vlm_pipe is None:
            from transformers import pipeline
            _vlm_pipe = pipeline("image-text-to-text", model=model_id, device_map="auto")
        img = Image.open(io.BytesIO(b64.b64decode(grid_b64)))
        msgs = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt}]}]
        out = _vlm_pipe(text=msgs, images=[img], max_new_tokens=512)
        return out[0]["generated_text"][-1]["content"]
    except Exception as e:
        return f"[Local VLM error: {e}]"


# ── Clustering & investigation logic ──────────────────────────────────────────

def _classify(categories: List[str], scores: List[float]) -> tuple:
    high = sum(1 for s in scores if s > 0.6)
    if "LURE" in categories and "MONETIZE" in categories:
        return "social_engineering_chain", "LURE→MONETIZE attack chain detected across cluster"
    if "EXPLOIT" in categories and "MONETIZE" in categories:
        return "ato_fraud", "Account takeover followed by fraudulent transaction"
    if high >= 3:
        return "coordinated_attack", f"{high} high-risk events in {WINDOW_MINS}min window — coordinated attack suspected"
    return "elevated_cluster", "Cluster of elevated-risk events — manual review recommended"


def _confidence(scores: List[float], categories: List[str]) -> float:
    base = min(1.0, sum(scores) / len(scores) * 1.5)
    if "LURE" in categories and "MONETIZE" in categories: base = min(1.0, base + 0.2)
    return round(base, 3)


def _scan_and_investigate():
    from src.db.models import SessionLocal, SecurityEvent, AriaInvestigation
    from src.explainability.explain import contributions_for_provider, make_chart, make_grid_chart, auto_summary
    from src.api.internal.evaluation_runner import _registry

    db = SessionLocal()
    try:
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(minutes=WINDOW_MINS)
        recent = db.query(SecurityEvent).filter(
            SecurityEvent.timestamp >= cutoff,
            SecurityEvent.overall_risk >= MIN_RISK
        ).all()

        clusters: Dict[str, list] = collections.defaultdict(list)
        for e in recent:
            clusters[e.user_id or "ANON"].append(e)

        for key, events in clusters.items():
            if len(events) < MIN_CLUSTER:
                continue

            ids = [e.id for e in events]
            scores = [e.overall_risk for e in events]
            cats = [e.event_category for e in events]

            # update existing open investigation if cluster already known
            existing = db.query(AriaInvestigation).filter(
                AriaInvestigation.cluster_key == key,
                AriaInvestigation.status == "open"
            ).first()
            if existing:
                old_ids = set(existing.cluster_event_ids or [])
                new_ids = set(ids) - old_ids
                if new_ids:
                    existing.cluster_event_ids = list(old_ids | new_ids)
                    existing.cycle += 1
                    existing.updated_at = datetime.datetime.utcnow()
                    db.commit()
                    print(f"[ARIA] investigation {existing.id} updated — {len(new_ids)} new events")
                continue

            classification, hypothesis = _classify(cats, scores)

            # build charts from highest-risk event's payload
            best = max(events, key=lambda e: e.overall_risk)
            payload = best.input_payload or {}
            charts, summaries = {}, []
            for p in _registry.get_providers():
                name = p.__class__.__name__
                contribs = contributions_for_provider(p, payload)
                if contribs:
                    charts[name] = make_chart(contribs, name, best.overall_risk, best.decision)
                    summaries.append(auto_summary(contribs, best.overall_risk))

            grid = make_grid_chart(charts, f"ARIA cluster: {key}  events={ids}")
            event_summary = "; ".join(
                f"event#{e.id} risk={e.overall_risk:.2f} cat={e.event_category}" for e in events
            )
            vlm_text = _vlm_call(grid, hypothesis, event_summary) if grid else "[no chart data]"
            conf = _confidence(scores, cats)

            inv = AriaInvestigation(
                cluster_key=key,
                cluster_event_ids=ids,
                hypothesis=hypothesis,
                classification=classification,
                evidence_summary=" | ".join(summaries[:3]),
                vlm_assessment=vlm_text,
                confidence=conf,
                status="open",
                cycle=1
            )
            db.add(inv)
            db.commit()
            print(f"[ARIA] New investigation #{inv.id}: {hypothesis} (key={key} conf={conf})")
    except Exception as e:
        print(f"[ARIA] scan error: {e}")
    finally:
        db.close()


# ── Entry point (started by admin_api startup) ────────────────────────────────

async def run():
    print(f"[ARIA] started — scanning every {CYCLE_SECS}s, window={WINDOW_MINS}min, min_cluster={MIN_CLUSTER}")
    while True:
        await asyncio.sleep(CYCLE_SECS)
        try:
            # ponytail: run blocking DB scans and heavy VLM inference in a separate thread so Admin API doesn't freeze
            await asyncio.to_thread(_scan_and_investigate)
        except Exception as e:
            print(f"[ARIA] loop error: {e}")
