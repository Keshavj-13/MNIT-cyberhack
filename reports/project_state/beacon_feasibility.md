# Beacon Feasibility Assessment (arXiv:2605.10867)

**Date:** 2026-06-13
**Scope:** Sprint C of Phase 29 — investigate whether the paper at
https://arxiv.org/abs/2605.10867 provides a public model/checkpoint that could be
integrated into the mnit(cyberhack) RiskEngine, in particular as the real
implementation behind the currently-stubbed `BehavioralBiometricsProvider`.

## 1. What the paper actually is

**Title:** *BEACON: A Multimodal Dataset for Learning Behavioral Fingerprints from
Gameplay Data*
**Authors:** Ishpuneet Singh, Gursmeep Kaur, Uday Pratap Singh Atwal, Guramrit Singh,
Gurjot Singh, Maninder Singh

BEACON is a **dataset paper**, not a fraud-detection model paper. It releases a
large multimodal behavioral-biometrics dataset collected from **28 players across 79
competitive Valorant (video game) sessions** (~102.5 hours, ~445 GB), and benchmarks
six existing architectures on a **28-class player-identification (continuous
authentication) task**.

Captured modalities per session:
- High-frequency mouse dynamics (position, speed, clicks, scroll — CSV)
- Keystroke events (key identity, press/release, duration — CSV)
- Raw network packet captures (PCAP, addresses anonymized)
- Screen recordings (MP4)
- Hardware metadata (JSON)

## 2. Public artifacts located

| Artifact | Location | Status |
|---|---|---|
| Raw dataset | https://huggingface.co/datasets/beacon-gui/BEACON-Dataset | **Public**, ~445 GB, organized by `participant_P###/session_S###/{mouse,keyboard,packets,screen,hardware}` |
| Data-collection logger tool | https://zenodo.org/records/20062628 ("BEACON-Logger") | Public — this is the *recording* tool used by the authors, not an inference model |
| Paper record (Zenodo DOI) | 10.5281/zenodo.20034625 | Public |
| **Trained model code / checkpoints** | Searched arXiv PDF/HTML full text, Hugging Face dataset card, and GitHub (`beacon-gui` org and related search terms) | **NOT FOUND** |

The paper text and the Hugging Face dataset card both claim "code released on GitHub",
but no working GitHub repository or org could be located via direct lookup
(`github.com/beacon-gui` → 404) or web search. No trained weights/checkpoints for
any of the six baseline models are publicly available.

## 3. Models evaluated in the paper (no checkpoints released)

The paper benchmarks six existing architectures — ARES, BAPM, NetCLR, TCN, TMWF,
Var-CNN — trained from scratch by the authors on **33 engineered features** (mouse
movement rate/speed/clicks/displacement, keystroke dwell/inter-key intervals, packet
rate/inter-arrival time) over 10/30/45/60-second windows. Best result: Var-CNN,
70.82% top-1 accuracy / 4.31% EER on the 28-class identification task at 60s
windows. This is a research benchmark result, not a deployable artifact.

## 4. Compatibility with the current architecture

Even setting aside the missing checkpoints, the BEACON task and the platform's
`BehavioralBiometricsProvider` are a poor structural fit:

- **Different task shape.** BEACON is *closed-set, 28-class player identification*
  trained per-cohort. `BehavioralBiometricsProvider` needs an *open-set anomaly /
  risk score* for arbitrary bank customers — these require fundamentally different
  training setups (verification/anomaly models, not classifiers over a fixed
  participant roster).
- **Different input modality.** BEACON's features come from raw, high-frequency
  (sub-second) mouse/keyboard event streams and packet captures recorded during
  gameplay. The platform's `/evaluate` payload (`amount`, `sms_text`, `url`,
  `login_anomaly`, `new_device`, `vpn_detected`, `rooted`, `failed_attempts`, etc.)
  contains no raw input-device telemetry at all, and the BankSimulator frontend does
  not currently instrument mouse/keystroke timing.
- **No domain transfer story.** Esports mouse/keyboard dynamics during competitive
  gameplay have no demonstrated relationship to banking-session behavioral
  biometrics; using a Valorant-trained Var-CNN on banking sessions would be a fully
  speculative integration with no evidence of validity.

## 5. Recommendation

**NOT AVAILABLE for integration.** No trained model artifact exists publicly for
this paper — only a raw 445 GB gameplay dataset and a description of baselines
trained on it. Per the "no speculative integration" / "if model artifacts not
publicly available, state NOT AVAILABLE, do not invent implementations" directive,
`BehavioralBiometricsProvider` should remain the zero-score placeholder it is today
(`mode: "placeholder"`, reported honestly via `/health`).

If genuine behavioral-biometrics support is wanted in the future, the realistic path
is **not** "integrate BEACON" but:
1. Instrument the BankSimulator frontend to capture coarse session telemetry
   (typing cadence on the login form, mouse movement variance, time-on-page).
2. Collect a small first-party baseline-vs-anomaly dataset from demo sessions.
3. Train a lightweight anomaly model (e.g. isolation forest / autoencoder) on that
   first-party data.

This is new work, not integration of BEACON, and is out of scope for this sprint.

## 6. No code changes made

This sprint was research-only. `BehavioralBiometricsProvider` is unchanged and
continues to report `mode: "placeholder"` via `/health`, which is the honest and
correct state given the findings above.
