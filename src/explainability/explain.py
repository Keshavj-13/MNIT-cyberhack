import io, base64
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import List, Dict, Any, Optional


def _top5_contributions(model, feature_names: List[str], X: pd.DataFrame) -> List[Dict]:
    """Per-sample feature contributions using importance × signed deviation from zero.

    When payload is sparse (most features zero), falls back to global importance ranking
    so the chart still shows something meaningful rather than an empty bar.
    """
    imp = np.array(model.feature_importances_, dtype=float)
    imp_norm = imp / (imp.max() + 1e-9)            # normalise to [0,1] regardless of unit
    vals = X.values[0].astype(float)
    mx = np.abs(vals).max()

    if mx > 1e-9:
        # at least one non-zero feature — weight by value magnitude
        contribs = imp_norm * (vals / (mx + 1e-9))
    else:
        # sparse payload: show top features by global importance, direction unknown
        contribs = imp_norm  # all positive; chart shows "these matter most"

    top_idx = np.argsort(np.abs(contribs))[-5:][::-1]
    return [
        {"feature": feature_names[i], "value": round(float(vals[i]), 4),
         "contribution": round(float(contribs[i]), 4),
         "direction": "risk" if contribs[i] > 0 else "safe"}
        for i in top_idx
    ]


def contributions_for_provider(provider, data: Dict[str, Any]) -> List[Dict]:
    from src.providers.implementations import (
        TransactionRiskProvider, SocialEngineeringRiskProvider, AccountTakeoverProvider
    )
    try:
        if isinstance(provider, TransactionRiskProvider) and provider.model and provider.features:
            X = pd.DataFrame([data]).reindex(columns=provider.features, fill_value=0)
            for c in provider.cat_cols:
                if c in X and c in provider.encoders:
                    enc = provider.encoders[c]
                    # only encode known categories; unknown → 0
                    X[c] = X[c].astype(str).apply(
                        lambda v: enc.transform([v])[0] if v in enc.classes_ else 0
                    )
            for col in X.select_dtypes(include=["object"]).columns:
                X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0)
            return _top5_contributions(provider.model, provider.features, X)

        if isinstance(provider, AccountTakeoverProvider) and provider.model:
            feats = provider.BEHAVIOR_FEATURES
            X = pd.DataFrame([data]).reindex(columns=feats, fill_value=0)
            if provider.scaler:
                X = pd.DataFrame(provider.scaler.transform(X), columns=feats)
            return _top5_contributions(provider.model, feats, X)

        if isinstance(provider, SocialEngineeringRiskProvider) and provider.model:
            from src.providers.implementations import _url_features
            url = data.get("current_url") or data.get("url") or ""
            feats = _url_features(url)
            X = pd.DataFrame([feats]).reindex(columns=provider.URL_FEATS, fill_value=0)
            return _top5_contributions(provider.model, provider.URL_FEATS, X)
    except Exception:
        pass
    return []


def make_chart(contributions: List[Dict], provider_name: str, score: float, decision: str) -> str:
    if not contributions:
        return ""
    labels = [f"{c['feature']}  ({c['value']:g})" for c in contributions]
    vals   = [c["contribution"] for c in contributions]
    colors = ["#e74c3c" if v > 0 else "#27ae60" for v in vals]

    fig, ax = plt.subplots(figsize=(7, max(2.5, len(labels) * 0.55)))
    ax.barh(labels[::-1], vals[::-1], color=colors[::-1], height=0.6)
    ax.axvline(0, color="#888", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Feature contribution", fontsize=8)
    ax.set_title(f"{provider_name}   score={score:.3f}   {decision}", fontsize=9, fontweight="bold", pad=6)
    ax.tick_params(axis="y", labelsize=7.5)
    ax.tick_params(axis="x", labelsize=7.5)
    fig.patch.set_facecolor("#f9f9f9"); ax.set_facecolor("#f9f9f9")
    plt.tight_layout(pad=0.8)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def make_grid_chart(charts: Dict[str, str], title: str) -> str:
    """Stitch multiple provider charts into a grid for VLM multi-chart analysis."""
    valid = {k: v for k, v in charts.items() if v}
    if not valid:
        return ""
    import PIL.Image
    imgs = []
    for b64 in valid.values():
        imgs.append(PIL.Image.open(io.BytesIO(base64.b64decode(b64))))

    n = len(imgs)
    cols = min(2, n); rows = (n + cols - 1) // cols
    w = max(img.width for img in imgs); h = max(img.height for img in imgs)
    grid = PIL.Image.new("RGB", (cols * w, rows * h + 40), (249, 249, 249))
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(grid)
    draw.text((10, 10), title, fill=(50, 50, 50))
    for i, img in enumerate(imgs):
        r, c = divmod(i, cols)
        grid.paste(img, (c * w, r * h + 40))

    buf = io.BytesIO()
    grid.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def auto_summary(contributions: List[Dict], score: float) -> str:
    risk_drivers = [c for c in contributions if c["direction"] == "risk"][:3]
    if not risk_drivers:
        return f"Score {score:.3f}: no strong risk drivers — possible false positive."
    drivers = ", ".join(f"{c['feature']}={c['value']:g}" for c in risk_drivers)
    return f"Score {score:.3f} driven by: {drivers}."
