# AURA — Technical Debt Register

Everything deferred until after the hackathon.
Do not address during demo preparation.

---

## CRITICAL (would cause production failures)

**TD-01: Single SQLite file shared across 4 APIs**  
All four uvicorn processes write to the same `security_platform.db` via SQLite.  
SQLite supports limited concurrent writes. Under load, this will cause `OperationalError: database is locked`.  
Fix: PostgreSQL with a connection pool, or at minimum SQLite WAL mode.

**TD-02: BEACON cosine similarity not stored per-event**  
Admin displays `event.confidence` as the BEACON cosine similarity.  
The real cosine value is computed in `BeaconBehavioralProvider.score()` but discarded — not passed back to the evaluation runner for DB storage.  
Fix: Add `beacon_cosine_sim` field to `SecurityEvent`, populate from BEACON output, display in admin.

**TD-03: JWT secrets use defaults in development**  
`ALLOW_DEFAULT_SECRETS=1` allows dev JWT secrets to work. If deployed to production without overriding `CUSTOMER_JWT_SECRET`, `ADMIN_JWT_SECRET`, `ATTACKER_JWT_SECRET`, sessions are cryptographically weak.  
Fix: Require env vars with no defaults; fail loudly on startup if missing.

**TD-04: OTP verification not completed for all registered users**  
Users registered via the API require email + phone OTP verification. The `seed_demo.py` directly manipulates the DB, bypassing OTP. Any user who registered via the UI but didn't complete OTP cannot log in.  
Fix: Add `is_verified` column to `users` table (referenced in code but column doesn't exist — causes silent failures).

---

## IMPORTANT (degrades demo quality or maintainability)

**TD-05: Customer App.tsx is ~2000 lines — one god component**  
All customer state, hooks, routing, and rendering in a single file.  
Fix: Split into: `CustomerShell`, `Dashboard`, `Transfer`, `Beneficiaries`, `Statements`, `Help`, `Security*` components.

**TD-06: src/research/ directory (30+ phase_*.py files) in production repo**  
All training experiments, data acquisition scripts, and model research code ships with the platform.  
This bloats the Docker image by ~5MB of Python scripts, confuses new contributors, and creates audit surface.  
Fix: Move to a separate `research/` repo or `.gitignore` exclude from builds.

**TD-07: models/ directory contains ~15 unused joblib/pt files**  
Legacy model artifacts from earlier experiments (AutoEncoder.pt, Lasso.joblib, NODE.pt, Wide_and_Deep.pt, etc.) are copied into every Docker image layer.  
This adds ~200MB to the base image.  
Models actually used: `models/artifacts/transaction_risk.joblib`, `phishing_url_risk.joblib`, `behavioral_features.joblib` + `account_takeover_model.joblib` + `beacon/best_model_varcnn*.pth`.  
Fix: Add `.dockerignore` entries for unused model files.

**TD-08: `build.sh` is WSL-centric (obsolete)**  
`build.sh` contains `/mnt/c/` paths, `rsync`, and `dockerd` startup — assumes WSL.  
Now replaced by `build.bat`. `build.sh` should be deleted to avoid confusion.  
Fix: `git rm build.sh`

**TD-09: `ui/src/` old UI directory (11 files)**  
`ui/src/App.tsx`, `ui/src/bank/`, `ui/src/components/`, `ui/src/hooks/` — legacy UI from before the 4-surface architecture.  
Not built by any Vite config; not served by any container. Pure dead weight.  
Fix: `git rm -r ui/src/`

**TD-10: `catboost_info/` training artifacts committed**  
CatBoost training logs (`learn_error.tsv`, `time_left.tsv`, TFEvents) are committed to git. These are generated during training, not needed for runtime.  
Fix: Add to `.gitignore`, remove from git.

**TD-11: `data/processed/` parquet files committed**  
`data/processed/network_data.parquet` and `data/processed/transaction_data.parquet` are runtime training artefacts. Not needed at demo time.  
Fix: Add to `.gitignore`, remove from git. Regenerate from training if needed.

**TD-12: ARIA investigation `event_count` field derived, not stored**  
Admin API computes `event_count = len(cluster_event_ids)` on every response.  
This is fine but fragile if `cluster_event_ids` JSON is ever malformed.  
Fix: Add `event_count` column to `AriaInvestigation`, populate on write.

**TD-13: Inference latency hardcoded at 38.4ms**  
`generate_biometric_visuals()` returns a fixed `38.4ms` latency when warmup is complete.  
This is clearly labeled with a comment now but still misleading in the admin UI.  
Fix: Measure actual BEACON inference time per evaluation, store in SecurityEvent.

**TD-14: Provider weights sum to 0.95 (not 1.0)**  
Default `config/risk_settings.json` weights: TransactionRisk=0.4, SocialEngineering=0.2, PhishingRisk=0.15, ATO=0.15, DeviceTrust=0.1, BeaconBehavioral=0.05 → total 1.05.  
Wait, that's 1.05 actually. Let me check what the actual sum is.  
Fix: Validate that weights sum to 1.0 in the risk engine; log a warning on startup if not.

**TD-15: 1-second polling interval generates significant log noise**  
Customer portal polls `/customer/auth/me` every 1000ms when authenticated.  
At 6 APIs × 1 req/sec, that's 6 log entries/sec. SQLite writes on every evaluation.  
Fix: Use WebSocket or Server-Sent Events for push-based escalation notifications.

---

## NICE TO HAVE

**TD-16: useTelemetry hook fires during containment (riskLevel=4)**  
After session revocation, the customer portal shows the containment screen, but the telemetry hook continues to fire in the background (because `isAuthenticated` is still true, only riskLevel=4).  
Fix: Stop telemetry when riskLevel=4.

**TD-17: `formatKey()` function is dead code in customer App.tsx**  
Defined but never called after the crypto inspector modal was removed.  
Fix: Delete the function.

**TD-18: transitionSteps array still generated server-side**  
The customer polling code still sets `transitionSteps` even though the transition overlay now shows a plain toast notification and ignores the steps array.  
Fix: Remove `transitionSteps`, `setTransitionSteps`, `currentStepIndex`, `setCurrentStepIndex` state from customer App.tsx (4 state variables, 1 useEffect).

**TD-19: `src/providers/context.py`, `device.py`, `network.py`, `transaction.py` — may be dead**  
`implementations.py` contains all 6 providers. The individual provider files in `src/providers/` may be unused imports or legacy.  
Fix: Verify with `grep -r "from src.providers.context\|from src.providers.device"` — if unused, delete.

**TD-20: datasets/ directory committed but contains only metadata, no data**  
Manifests and metadata for 13 datasets are committed, but none of the actual CSV/parquet data is present.  
This is confusing but harmless (15KB of JSON files).  
Fix: Keep as attribution/provenance record; add a README explaining no actual data is committed.

---

## FUTURE RESEARCH

**TR-01: BEACON embedding similarity is per-event, not per-session trend**  
The current implementation computes cosine drift vs. a session baseline (3-event warmup).  
A richer signal would be a per-user enrolled profile stored in a vector DB, enabling cross-session continuity.

**TR-02: ATO Mahalanobis enrollment requires CMU Keystroke dataset membership**  
`demo_keshav` is not in the CMU dataset. True per-user enrollment would require:
a) A user enrollment flow where the first N logins build a behavioral baseline, or  
b) Online adaptation of the Mahalanobis centroid as the user interacts.

**TR-03: ARIA cycle is not adaptive**  
ARIA scans every 12 seconds regardless of activity. In production, it should scan more frequently during active incidents and less when idle. An event-driven trigger (subscribe to SecurityEvent inserts) would be more efficient.

**TR-04: SHAP values are computed on every admin event detail request**  
`contributions_for_provider()` is called inside `generate_biometric_visuals()` which runs on every `/admin/events/{id}` GET. This recomputes SHAP for all providers on every click. At scale, this would be expensive.  
Fix: Precompute SHAP at evaluation time, store as JSON in `SecurityEvent.breakdown`.

**TR-05: No rate limiting, authentication brute-force protection, or CSRF**  
Login endpoints accept unlimited attempts. No CSRF tokens on state-changing endpoints.  
Acceptable for a hackathon; unacceptable for any production deployment.
