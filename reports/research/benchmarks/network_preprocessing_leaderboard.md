# Preprocessing Leaderboard: network

| imputer       | scaler   | encoder   | selector    |   roc_auc |   duration |
|:--------------|:---------|:----------|:------------|----------:|-----------:|
| most_frequent | quantile | onehot    | mutual_info |  0.507937 |   0.512918 |
| mean          | quantile | onehot    | mutual_info |  0.507937 |   0.421154 |
| most_frequent | quantile | onehot    | none        |  0.507937 |   0.410139 |
| native        | quantile | onehot    | none        |  0.507937 |   1.06392  |
| most_frequent | quantile | onehot    | kbest       |  0.507937 |   0.416126 |
| most_frequent | quantile | onehot    | rfe         |  0.507937 |   0.489181 |
| most_frequent | quantile | ordinal   | none        |  0.507937 |   0.48749  |
| most_frequent | quantile | ordinal   | mutual_info |  0.507937 |   0.557815 |
| most_frequent | quantile | ordinal   | kbest       |  0.507937 |   0.48426  |
| most_frequent | quantile | ordinal   | rfe         |  0.507937 |   0.549035 |
| most_frequent | quantile | target    | none        |  0.507937 |   0.430317 |
| most_frequent | quantile | target    | mutual_info |  0.507937 |   0.505377 |
| most_frequent | quantile | target    | kbest       |  0.507937 |   0.428181 |
| most_frequent | quantile | target    | rfe         |  0.507937 |   0.499127 |
| most_frequent | quantile | catboost  | none        |  0.507937 |   0.418074 |
| most_frequent | quantile | catboost  | mutual_info |  0.507937 |   0.519294 |
| most_frequent | quantile | catboost  | kbest       |  0.507937 |   0.425369 |
| most_frequent | quantile | catboost  | rfe         |  0.507937 |   0.491859 |
| mean          | quantile | catboost  | rfe         |  0.507937 |   0.397238 |
| mean          | quantile | catboost  | kbest       |  0.507937 |   0.372514 |