# Social Engineering Models Leaderboard

| model                      | dataset             |   roc_auc |   pr_auc |       f1 |   precision |   recall |   train_time |   inf_time_per_sample |
|:---------------------------|:--------------------|----------:|---------:|---------:|------------:|---------:|-------------:|----------------------:|
| LightGBM                   | Phishing Websites   |  0.995774 | 0.99655  | 0.970396 |    0.966686 | 0.974176 |     1.06722  |           1.08743e-06 |
| RandomForest               | Phishing Websites   |  0.99562  | 0.99575  | 0.973053 |    0.967188 | 0.979048 |     0.867097 |           3.60373e-06 |
| TFIDF + LogisticRegression | SMS Spam Collection |  0.99091  | 0.969629 | 0.857735 |    0.986084 | 0.759034 |     2.17781  |           1.04129e-05 |
| TFIDF + RandomForest       | SMS Spam Collection |  0.990647 | 0.977331 | 0.920286 |    0.992282 | 0.858085 |     2.79624  |           1.70705e-05 |
| TFIDF + LightGBM           | SMS Spam Collection |  0.982782 | 0.959718 | 0.911543 |    0.949269 | 0.876823 |     2.96848  |           2.1121e-05  |
| LogisticRegression         | Phishing Websites   |  0.978737 | 0.982267 | 0.935475 |    0.926105 | 0.945103 |     0.152364 |           4.09528e-07 |