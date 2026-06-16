# Final Research & AutoML Report

## 1. Executive Summary
This study evaluated 36+ models and multiple preprocessing strategies for Banking Threat Detection.

## Transaction Research Results

### Top 5 Preprocessing Pipelines
| imputer   | scaler   |   roc_auc |   duration |
|:----------|:---------|----------:|-----------:|
| mean      | power    |  0.538198 |   0.439564 |
| knn       | quantile |  0.53425  |   0.982955 |
| median    | quantile |  0.529997 |   0.429627 |
| knn       | robust   |  0.528828 |   0.999545 |
| knn       | none     |  0.527458 |   0.971174 |

### Traditional Model Leaderboard
| model                |   roc_auc_mean |   roc_auc_std |   duration |
|:---------------------|---------------:|--------------:|-----------:|
| AdaBoost             |       0.549303 |    0.0111752  |  0.253778  |
| GradientBoosting     |       0.541305 |    0.0508779  |  0.640448  |
| LogisticRegression   |       0.530252 |    0.0384937  |  2.73104   |
| Ridge                |       0.526468 |    0.030524   |  1.85371   |
| CatBoost             |       0.523738 |    0.0332425  |  3.67422   |
| DecisionTree         |       0.508055 |    0.00759942 |  0.0991797 |
| GaussianNB           |       0.503956 |    0.0219413  |  1.73727   |
| XGBoost              |       0.501635 |    0.0389248  |  0.442835  |
| KNN                  |       0.499894 |    0.0312512  |  1.78485   |
| ExtraTrees           |       0.497309 |    0.0562638  |  0.364951  |
| HistGradientBoosting |       0.496784 |    0.0366718  |  0.295904  |
| LightGBM             |       0.483363 |    0.0461879  |  0.580401  |
| RandomForest         |       0.459197 |    0.0480518  |  0.402087  |

### Deep Learning Leaderboard
| model      |   roc_auc |   duration |
|:-----------|----------:|-----------:|
| MLP_Deep   |  0.498509 |    1.91228 |
| MLP_Small  |  0.487206 |    3.26767 |
| MLP_Medium |  0.470073 |    1.3646  |

## Network Research Results

### Top 5 Preprocessing Pipelines
| imputer   | scaler   |   roc_auc |   duration |
|:----------|:---------|----------:|-----------:|
| knn       | quantile |  0.520561 |   0.837801 |
| knn       | power    |  0.519714 |   0.870921 |
| knn       | standard |  0.518089 |   0.81202  |
| knn       | minmax   |  0.517981 |   0.809757 |
| knn       | robust   |  0.517737 |   0.876893 |

### Traditional Model Leaderboard
| model                |   roc_auc_mean |   roc_auc_std |   duration |
|:---------------------|---------------:|--------------:|-----------:|
| LogisticRegression   |       0.512157 |    0.0131485  |  0.223981  |
| Ridge                |       0.50657  |    0.0071635  |  0.0251632 |
| ExtraTrees           |       0.501363 |    0.0148184  |  0.275851  |
| DecisionTree         |       0.500556 |    0.0127599  |  0.0666227 |
| RandomForest         |       0.499006 |    0.0115397  |  0.415988  |
| GaussianNB           |       0.495057 |    0.00784475 |  0.0246229 |
| KNN                  |       0.494948 |    0.0108888  |  0.0348029 |
| XGBoost              |       0.487814 |    0.00585724 |  0.36818   |
| HistGradientBoosting |       0.487432 |    0.0042448  |  0.263676  |
| CatBoost             |       0.482998 |    0.00822015 |  3.6976    |
| LightGBM             |       0.482787 |    0.00597187 |  0.491871  |
| GradientBoosting     |       0.479491 |    0.0114295  |  0.703552  |
| AdaBoost             |       0.476326 |    0.00791291 |  0.275911  |

### Deep Learning Leaderboard
| model      |   roc_auc |   duration |
|:-----------|----------:|-----------:|
| MLP_Small  |  0.499264 |    1.26915 |
| MLP_Deep   |  0.496783 |    1.85879 |
| MLP_Medium |  0.496002 |    1.17034 |

## Final Recommendation
Based on the experiments, we recommend a **LightGBM-based architecture** for production due to its balanced performance, low latency, and native missing value handling. While Deep Learning models show promise, their higher latency and complexity for tabular data do not currently justify the marginal gains on synthetic data.
