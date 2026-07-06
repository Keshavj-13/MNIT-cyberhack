from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
import os
from typing import Dict, Any, List

from src.engine.registry import ProviderRegistry
from src.providers.implementations import (
    TransactionRiskProvider, SocialEngineeringRiskProvider,
    AccountTakeoverProvider, DeviceTrustProvider, NetworkRiskProvider,
    BeaconBehavioralProvider
)

app = FastAPI(title="MNIT Research Showcase Portal API", version="1.0.0")

# Strict CORS: Allow showcase frontend (port 3004) to request GET
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3004", "http://127.0.0.1:3004"],
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# Bootstrap the registry so the showcase can dynamically query all models
def bootstrap_showcase():
    registry = ProviderRegistry()
    registry.clear_registry()
    registry.register_provider(TransactionRiskProvider())
    registry.register_provider(SocialEngineeringRiskProvider())
    registry.register_provider(AccountTakeoverProvider())
    registry.register_provider(NetworkRiskProvider())
    registry.register_provider(DeviceTrustProvider())
    registry.register_provider(BeaconBehavioralProvider())

bootstrap_showcase()

MODEL_REGISTRY_META = {
    "TransactionRiskProvider": {
        "display_name": "Transaction Risk Model",
        "risk_category": "Transaction Risk",
        "training_summary_key": "transaction_risk",
        "explainability_file": "reports/research/benchmarks/transaction_explainability.json",
        "dataset": "feedzai_baf",
        "input_description": "31 numeric/categorical features describing a single transaction request: account profile, velocity counters, device signals, etc.",
        "collection_description": "Captured live from the Bank Simulator's transfer form at submission time, mapped onto the Feedzai BAF feature template.",
    },
    "SocialEngineeringRiskProvider": {
        "display_name": "URL Phishing Detection Model",
        "risk_category": "Intent Risk",
        "training_summary_key": "phishing_url_risk",
        "explainability_file": None,
        "dataset": "phishing_websites",
        "input_description": "8 URL-lexical features computable from any URL without DNS/API calls: IP address in URL, URL length, @ symbol, double-slash redirect, dash prefix, subdomain count, SSL state, HTTPS token in domain.",
        "collection_description": "Extracted from page_load telemetry events in the customer session. Previous SMS text model replaced after UI decoupling removed message capture.",
    },
    "AccountTakeoverProvider": {
        "display_name": "Keystroke Behavioral Biometrics",
        "risk_category": "Behavioral Risk",
        "training_summary_key": "behavioral_risk",
        "explainability_file": None,
        "dataset": "cmu_keystroke",
        "input_description": "10 aggregated keystroke features derived from session telemetry: dwell_mean/std/range, flight_mean/std/range, latency_mean/std/range, rhythm (coefficient of variation of flight times).",
        "collection_description": "Computed by FeatureExtractor from raw keystroke dwell/flight events captured client-side. Retrained on CMU DSL dataset aggregated to match live feature schema.",
    },
    "NetworkRiskProvider": {
        "display_name": "Network Session Heuristics",
        "risk_category": "Environment Risk",
        "training_summary_key": None,
        "explainability_file": None,
        "dataset": None,
        "input_description": "HTTP session metadata flags: vpn_detected, proxy_detected, tor_detected, impossible_geo (location velocity anomaly), blacklisted_ip.",
        "collection_description": "Rule-based heuristics on connection metadata available at API request time. Previous SIMARGL2021 packet-level model replaced — packet features are unavailable from banking session telemetry.",
    },
    "DeviceTrustProvider": {
        "display_name": "Device Trust Rules",
        "risk_category": "Device Risk",
        "training_summary_key": None,
        "explainability_file": None,
        "dataset": None,
        "input_description": "Device fingerprint flags: `vpn_detected`, `rooted` (jailbroken device).",
        "collection_description": "Captured from client device fingerprint reported at session start. Rule-based.",
    },
    "BeaconBehavioralProvider": {
        "display_name": "BEACON VarCNN Behavioral Fingerprint",
        "risk_category": "Behavioral Risk",
        "training_summary_key": "beacon_behavioral",
        "explainability_file": None,
        "dataset": "beacon",
        "input_description": "1024-point min-max normalised inter-event timing sequence + 10 scalar metadata features. Dual-stream architecture: ResNet backbone (4 stages, 64→512 channels) + metadata MLP, outputs 512-d GAP embedding.",
        "collection_description": "Inter-event timing deltas extracted from all session events (keystroke, mouse, page_load). Embedding cosine drift vs session baseline detects mid-session behavioural shift. Model: Singh et al. 2026, arXiv:2605.10867.",
    },
}

MOCK_PAPERS = [
    {
        "title": "BEACON: A Multimodal Dataset for Learning Behavioral Fingerprints from Gameplay Data",
        "authors": "Ishpuneet Singh, Gursmeep Kaur, Uday Pratap Singh Atwal, Guramrit Singh, Gurjot Singh, Maninder Singh",
        "journal": "arXiv:2605.10867",
        "abstract": "Continuous authentication in high-stakes digital environments requires datasets with fine-grained behavioral signals under realistic cognitive and motor demands. But current benchmarks are often limited by small scale, unimodal sensing or lack of synchronised environmental context. To address this gap, this paper introduces BEACON (Behavioral Engine for Authentication & Continuous Monitoring), a large-scale multimodal dataset that captures diverse skill tiers in competitive Valorant gameplay. BEACON contains approximately 430 GB of synchronised modality data (461 GB total on-disk including auxiliary Valorant configuration captures) from 79 sessions across 28 distinct players, estimated at 102.51 hours of active gameplay, including high-frequency mouse dynamics, keystroke events, network packet captures, screen recordings, hardware metadata, and in-game configuration context. BEACON leverages the high precision motor skills and high cognitive load that are inherent to tactical shooters, making it a rigorous stress test for the robustness of behavioral biometrics. The dataset allows for the study of continuous authentication, behavioral profiling, user drift and multimodal representation learning in a high-fidelity esports setting. The authors release the dataset and code on Hugging Face and GitHub to create a reproducible benchmark for evaluating next-generation behavioral fingerprinting and security models.",
        "citation": "Singh et al. (2026). arXiv:2605.10867 [cs.CR]"
    }
]

# --- Dynamic Model Reports (Exact replica of original `/model-reports` endpoint) ---
@app.get("/model-reports")
def get_model_reports():
    training_metrics: Dict[str, Any] = {}
    metrics_path = "reports/models/training_summary.json"
    if os.path.exists(metrics_path):
        try:
            with open(metrics_path, "r") as f:
                training_metrics = json.load(f)
        except Exception:
            pass

    reports = []
    for provider in ProviderRegistry.get_providers():
        name = provider.__class__.__name__
        meta = MODEL_REGISTRY_META.get(name, {})
        model_info = dict(getattr(provider, "model_info", {"mode": "unknown"}))

        # Feature list, if the provider exposes one.
        features = getattr(provider, "features", None) or getattr(provider, "BEHAVIOR_FEATURES", None)

        # Underlying model class
        model_obj = getattr(provider, "model", None)
        model_type = type(model_obj).__name__ if model_obj is not None else model_info.get("mode", "rules")

        metrics = training_metrics.get(meta.get("training_summary_key") or "")

        explainability = None
        exp_file = meta.get("explainability_file")
        if exp_file and os.path.exists(exp_file):
            try:
                with open(exp_file, "r") as f:
                    explainability = json.load(f)
            except Exception:
                pass

        dataset_meta = None
        dataset_name = meta.get("dataset")
        if dataset_name:
            ds_path = f"datasets/{dataset_name}/aura_metadata.json"
            if os.path.exists(ds_path):
                try:
                    with open(ds_path, "r") as mf:
                        dataset_meta = json.load(mf)
                except Exception:
                    pass

        reports.append({
            "provider_name": name,
            "display_name": meta.get("display_name", name),
            "risk_category": meta.get("risk_category", "Unknown"),
            "model_type": model_type,
            "model_info": model_info,
            "features": features,
            "metrics": metrics,
            "explainability": explainability,
            "input_description": meta.get("input_description"),
            "collection_description": meta.get("collection_description"),
            "dataset_name": dataset_name,
            "dataset_meta": dataset_meta,
        })

    return reports

# --- Dynamic Verification Reports (Exact replica of original `/verification-reports` endpoint) ---
@app.get("/verification-reports")
def get_verification_reports():
    report_path = "reports/verification_run/summary.json"
    if os.path.exists(report_path):
        try:
            with open(report_path, "r") as f:
                reports = json.load(f)
                
                # Enrich with aura_metadata.json if exists
                for report in reports:
                    meta_path = f"datasets/{report['name']}/aura_metadata.json"
                    if os.path.exists(meta_path):
                        with open(meta_path, "r") as mf:
                            report["aura_metadata"] = json.load(mf)
                return reports
        except Exception:
            pass
    return []

@app.get("/showcase/models")
def get_legacy_models():
    return get_model_reports()

@app.get("/showcase/datasets")
def get_legacy_datasets():
    return get_verification_reports()

@app.get("/showcase/papers")
def get_papers():
    return MOCK_PAPERS

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8004)
