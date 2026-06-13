# Synthetic vs Real Dataset Performance

| Metric | Synthetic (Transaction Data) | Real (ULB Credit Card) |
| --- | --- | --- |
| Best ROC AUC | ~0.53 | ~0.97+ |
| Best PR AUC | ~0.02 | ~0.80+ |
| Best F1 | 0.00 | ~0.85+ |
| Best Recall | 0.00 | ~0.80+ |

**Conclusion:** The synthetic data completely failed to produce learnable signals (Precision/Recall = 0). The real ULB dataset proves that the architecture (LightGBM/XGBoost) successfully achieves >0.80 Recall and >0.80 F1 when exposed to genuine fraud telemetry.
