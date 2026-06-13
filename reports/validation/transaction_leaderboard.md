# Transaction Model Leaderboard

| model              |   roc_auc_cv |   roc_auc_std |   f1_cv |    pr_auc |   accuracy |   precision |   recall | status   |
|:-------------------|-------------:|--------------:|--------:|----------:|-----------:|------------:|---------:|:---------|
| LogisticRegression |     0.528668 |     0.0526191 |       0 | 0.031502  |      0.981 |           0 |        0 | UNUSABLE |
| RandomForest       |     0.524578 |     0.0752412 |       0 | 0.0175089 |      0.981 |           0 |        0 | UNUSABLE |
| LightGBM           |     0.512732 |     0.0589222 |       0 | 0.0177102 |      0.981 |           0 |        0 | UNUSABLE |
| XGBoost            |     0.49142  |     0.0572715 |       0 | 0.0180836 |      0.979 |           0 |        0 | UNUSABLE |

## Recommendations
**WARNING:** All models for transaction are currently flagged as **UNUSABLE** (AUC < 0.60).
This is expected for synthetic development data. Real data is required for meaningful training.
- **High Variance:** Model performance is inconsistent across folds.
