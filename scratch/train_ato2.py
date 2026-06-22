import pandas as pd, numpy as np, joblib
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import RobustScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, f1_score, recall_score, precision_score, precision_recall_curve

df = pd.read_csv("datasets/raw/cmu_keystroke/DSL-StrongPasswordData.csv")
H=[c for c in df.columns if c.startswith("H.")]; DD=[c for c in df.columns if c.startswith("DD.")]; UD=[c for c in df.columns if c.startswith("UD.")]
df["dwell_mean"]=df[H].mean(axis=1); df["dwell_std"]=df[H].std(axis=1); df["dwell_range"]=df[H].max(axis=1)-df[H].min(axis=1)
df["flight_mean"]=df[DD].mean(axis=1); df["flight_std"]=df[DD].std(axis=1); df["flight_range"]=df[DD].max(axis=1)-df[DD].min(axis=1)
df["lat_mean"]=df[UD].mean(axis=1); df["lat_std"]=df[UD].std(axis=1); df["lat_range"]=df[UD].max(axis=1)-df[UD].min(axis=1)
df["rhythm"]=df["flight_std"]/(df["flight_mean"]+1e-9)
FEATS=["dwell_mean","dwell_std","dwell_range","flight_mean","flight_std","flight_range","lat_mean","lat_std","lat_range","rhythm"]

y=(df["subject"]=="s002").astype(int)
n_neg,n_pos=(y==0).sum(),(y==1).sum(); spw=n_neg/n_pos
sc=RobustScaler(); X=sc.fit_transform(df[FEATS])
Xtr,Xte,ytr,yte=train_test_split(X,y,test_size=0.2,random_state=42,stratify=y)

mdl=GradientBoostingClassifier(n_estimators=400,learning_rate=0.05,max_depth=4,subsample=0.8,min_samples_leaf=5,random_state=42)
mdl.fit(Xtr,ytr,sample_weight=np.where(ytr==1,spw,1.0))
prob=mdl.predict_proba(Xte)[:,1]
print(f"AUC={roc_auc_score(yte,prob):.4f}")
pa,ra,ta=precision_recall_curve(yte,prob)
for t in [0.3,0.4,0.5,0.6,0.7]:
    idx=np.searchsorted(ta,t)
    if idx<len(pa): print(f"  thr={t}  prec={pa[idx]:.3f}  recall={ra[idx]:.3f}  F1={2*pa[idx]*ra[idx]/(pa[idx]+ra[idx]+1e-9):.3f}")
# use thr that gives recall~60% with best precision
mask=ra[:-1]>=0.6; best_thr=float(ta[np.argmax(pa[:-1]*mask)]) if mask.any() else 0.5
pred=(prob>=best_thr).astype(int)
print(f"chosen thr={best_thr:.3f}  F1={f1_score(yte,pred):.4f}  R={recall_score(yte,pred):.4f}  P={precision_score(yte,pred):.4f}")

joblib.dump({"model":mdl,"scaler":sc,"features":FEATS,"threshold":best_thr,"mode":"binary_gbm"},
            "models/artifacts/behavioral_risk.joblib")
joblib.dump(FEATS,"models/artifacts/behavioral_features.joblib")
print("saved")
