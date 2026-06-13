import pandas as pd
import os

os.makedirs("reports/research", exist_ok=True)

missing_components = [
    {"component_name": "Wide and Deep", "category": "Deep Learning", "implemented": False, "executed": False, "reason_missing": "Skipped in Phase E", "estimated_runtime": "5m", "dependencies_required": "pytorch", "priority": 1},
    {"component_name": "AutoEncoder", "category": "Deep Learning", "implemented": False, "executed": False, "reason_missing": "Skipped in Phase E", "estimated_runtime": "3m", "dependencies_required": "pytorch", "priority": 1},
    {"component_name": "Variational AutoEncoder", "category": "Deep Learning", "implemented": False, "executed": False, "reason_missing": "Skipped in Phase E", "estimated_runtime": "5m", "dependencies_required": "pytorch", "priority": 1},
    {"component_name": "TabTransformer", "category": "Deep Learning", "implemented": False, "executed": False, "reason_missing": "Skipped in Phase E", "estimated_runtime": "10m", "dependencies_required": "pytorch", "priority": 1},
    {"component_name": "SAINT", "category": "Deep Learning", "implemented": False, "executed": False, "reason_missing": "Skipped in Phase E", "estimated_runtime": "15m", "dependencies_required": "pytorch", "priority": 1},
    {"component_name": "NODE", "category": "Deep Learning", "implemented": False, "executed": False, "reason_missing": "Skipped in Phase E", "estimated_runtime": "10m", "dependencies_required": "pytorch", "priority": 1},
    {"component_name": "DeepFM", "category": "Deep Learning", "implemented": False, "executed": False, "reason_missing": "Skipped in Phase E", "estimated_runtime": "5m", "dependencies_required": "pytorch", "priority": 1},
    {"component_name": "FT Transformer", "category": "Deep Learning", "implemented": False, "executed": False, "reason_missing": "Skipped in Phase E", "estimated_runtime": "10m", "dependencies_required": "pytorch", "priority": 1},
    {"component_name": "Contrastive Tabular Learning", "category": "Deep Learning", "implemented": False, "executed": False, "reason_missing": "Skipped in Phase E", "estimated_runtime": "15m", "dependencies_required": "pytorch", "priority": 1},
    {"component_name": "TabNet Pretraining", "category": "Deep Learning", "implemented": False, "executed": False, "reason_missing": "Skipped in Phase E", "estimated_runtime": "10m", "dependencies_required": "pytorch-tabnet", "priority": 1},
    {"component_name": "RUSBoost", "category": "Traditional ML", "implemented": False, "executed": False, "reason_missing": "Skipped in Phase C", "estimated_runtime": "2m", "dependencies_required": "imblearn", "priority": 2},
    {"component_name": "Lasso", "category": "Traditional ML", "implemented": False, "executed": False, "reason_missing": "Skipped in Phase C", "estimated_runtime": "1m", "dependencies_required": "sklearn", "priority": 2},
    {"component_name": "ElasticNet", "category": "Traditional ML", "implemented": False, "executed": False, "reason_missing": "Skipped in Phase C", "estimated_runtime": "1m", "dependencies_required": "sklearn", "priority": 2},
    {"component_name": "Local Outlier Factor", "category": "Traditional ML", "implemented": False, "executed": False, "reason_missing": "Skipped in Phase C", "estimated_runtime": "2m", "dependencies_required": "sklearn", "priority": 2},
    {"component_name": "MissForest", "category": "Preprocessing", "implemented": False, "executed": False, "reason_missing": "Skipped in Phase B", "estimated_runtime": "5m", "dependencies_required": "missingpy/sklearn", "priority": 3},
    {"component_name": "Frequency Encoding", "category": "Preprocessing", "implemented": False, "executed": False, "reason_missing": "Skipped in Phase B", "estimated_runtime": "1m", "dependencies_required": "category_encoders", "priority": 3},
    {"component_name": "Boruta", "category": "Preprocessing", "implemented": False, "executed": False, "reason_missing": "Failed in Phase B", "estimated_runtime": "5m", "dependencies_required": "boruta", "priority": 3},
    {"component_name": "SHAP Selection", "category": "Preprocessing", "implemented": False, "executed": False, "reason_missing": "Skipped due to DLL issues", "estimated_runtime": "5m", "dependencies_required": "shap", "priority": 3},
    {"component_name": "Permutation Selection", "category": "Preprocessing", "implemented": False, "executed": False, "reason_missing": "Skipped in Phase B", "estimated_runtime": "3m", "dependencies_required": "sklearn", "priority": 3},
    {"component_name": "Focal Loss", "category": "Imbalance", "implemented": False, "executed": False, "reason_missing": "Skipped in Phase F", "estimated_runtime": "5m", "dependencies_required": "pytorch/xgboost", "priority": 4},
    {"component_name": "SMOTE ENN", "category": "Imbalance", "implemented": False, "executed": False, "reason_missing": "Skipped in Phase F", "estimated_runtime": "3m", "dependencies_required": "imblearn", "priority": 4}
]

df = pd.DataFrame(missing_components)
df.sort_values(by=["priority", "component_name"], inplace=True)
df.to_csv("reports/research/missing_components_audit.csv", index=False)
print("reports/research/missing_components_audit.csv generated.")
