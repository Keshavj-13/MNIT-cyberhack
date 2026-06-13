# Preprocessing Leaderboard: transaction

| imputer       | scaler   | encoder   | selector    |   roc_auc |   duration |
|:--------------|:---------|:----------|:------------|----------:|-----------:|
| most_frequent | minmax   | ordinal   | mutual_info |  0.619984 |   0.773715 |
| native        | minmax   | ordinal   | mutual_info |  0.619984 |   0.672343 |
| native        | minmax   | onehot    | mutual_info |  0.619984 |   0.652449 |
| iterative     | minmax   | catboost  | mutual_info |  0.619984 |   0.583277 |
| iterative     | minmax   | ordinal   | mutual_info |  0.619984 |   0.535674 |
| knn           | minmax   | target    | mutual_info |  0.619984 |   0.496616 |
| iterative     | minmax   | onehot    | mutual_info |  0.619984 |   0.556894 |
| most_frequent | minmax   | onehot    | mutual_info |  0.619984 |   0.996964 |
| knn           | minmax   | ordinal   | mutual_info |  0.619984 |   0.503637 |
| native        | minmax   | target    | mutual_info |  0.619984 |   0.662211 |
| median        | minmax   | catboost  | mutual_info |  0.619984 |   1.08882  |
| native        | minmax   | catboost  | mutual_info |  0.619984 |   0.550232 |
| median        | minmax   | target    | mutual_info |  0.619984 |   1.3191   |
| mean          | minmax   | catboost  | mutual_info |  0.619984 |   0.462736 |
| most_frequent | minmax   | target    | mutual_info |  0.619984 |   0.739878 |
| iterative     | minmax   | target    | mutual_info |  0.619984 |   0.597319 |
| median        | quantile | catboost  | mutual_info |  0.611351 |   1.32122  |
| median        | quantile | target    | mutual_info |  0.611351 |   1.35596  |
| mean          | quantile | ordinal   | mutual_info |  0.611351 |   0.773467 |
| knn           | quantile | catboost  | mutual_info |  0.611351 |   0.553796 |