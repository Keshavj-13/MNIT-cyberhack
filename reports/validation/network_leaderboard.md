# Network Model Leaderboard

| model              |   roc_auc_cv |   roc_auc_std |      f1_cv |   pr_auc |   accuracy |   precision |    recall | status   |
|:-------------------|-------------:|--------------:|-----------:|---------:|-----------:|------------:|----------:|:---------|
| LogisticRegression |     0.497417 |    0.016552   | 0          | 0.219467 |      0.803 |   0         | 0         | UNUSABLE |
| RandomForest       |     0.495458 |    0.0164185  | 0.00597045 | 0.219419 |      0.803 |   0.5       | 0.0203046 | UNUSABLE |
| XGBoost            |     0.475153 |    0.00567434 | 0.0718607  | 0.181372 |      0.769 |   0.0952381 | 0.0203046 | UNUSABLE |
| LightGBM           |     0.474    |    0.00920357 | 0.0229788  | 0.186138 |      0.797 |   0.2       | 0.0101523 | UNUSABLE |

## Recommendations
**WARNING:** All models for network are currently flagged as **UNUSABLE** (AUC < 0.60).
This is expected for synthetic development data. Real data is required for meaningful training.
- **High Variance:** Model performance is inconsistent across folds.
