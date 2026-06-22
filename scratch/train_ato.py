import pandas as pd, numpy as np, joblib
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import LabelEncoder, RobustScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, f1_score, recall_score, precision_score, precision_recall_curve
from scipy.stats import entropy as scipy_entropy

df = pd.read_csv("datasets/raw/cmu_keystroke/DSL-StrongPasswordData.csv")
H=[c for c in df.columns if c.startswith("H.")]; DD=[c for c in df.columns if c.startswith("DD.")]; UD=[c for c in df.columns if c.startswith("UD.")]
df["dm"]=df[H].mean(axis=1); df["ds"]=df[H].std(axis=1); df["dr"]=df[H].max(axis=1)-df[H].min(axis=1)
df["fm"]=df[DD].mean(axis=1); df["fs"]=df[DD].std(axis=1); df["fr"]=df[DD].max(axis=1)-df[DD].min(axis=1)
df["lm"]=df[UD].mean(axis=1); df["ls"]=df[UD].std(axis=1); df["lr"]=df[UD].max(axis=1)-df[UD].min(axis=1)
df["ry"]=df["fs"]/(df["fm"]+1e-9)
FEATS=["dm","ds","dr","fm","fs","fr","lm","ls","lr","ry"]
le=LabelEncoder().fit(df["subject"]); y=le.transform(df["subject"]); max_ent=np.log(len(le.classes_))
sc=RobustScaler(); X=sc.fit_transform(df[FEATS])
Xtr,Xte,ytr,yte=train_test_split(X,y,test_size=0.2,random_state=42,stratify=y)
yb=(le.inverse_transform(yte)!="s002").astype(int)
mdl=GradientBoostingClassifier(n_estimators=200,learning_rate=0.1,max_depth=4,subsample=0.8,random_state=42)
mdl.fit(Xtr,ytr)
probs=mdl.predict_proba(Xte); ent=scipy_entropy(probs,axis=1)/max_ent
print("AUC",round(roc_auc_score(yb,ent),4),"mc_acc",round((mdl.predict(Xte)==yte).mean(),4))
pa,ra,ta=precision_recall_curve(yb,ent); f1a=2*pa*ra/(pa+ra+1e-9); bt=float(ta[np.argmax(f1a[:-1])])
pred=(ent>=bt).astype(int)
print(f"F1={f1_score(yb,pred):.4f} R={recall_score(yb,pred):.4f} P={precision_score(yb,pred):.4f} thr={bt:.3f}")
joblib.dump({"model":mdl,"scaler":sc,"le":le,"features":FEATS,"max_entropy":float(max_ent),"threshold":bt,"mode":"entropy"},"models/artifacts/behavioral_risk.joblib")
joblib.dump(FEATS,"models/artifacts/behavioral_features.joblib")
print("saved")
