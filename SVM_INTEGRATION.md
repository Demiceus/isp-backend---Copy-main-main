# Linear SVM Sentiment Model Integration

The production review sentiment classifier has been updated from Logistic Regression to **TF-IDF + Linear SVM**.

## Training data

- `data/sentiment_train.csv`: 16,000 reviews
- `data/sentiment_val.csv`: 2,000 reviews
- Combined training set: 18,000 reviews
- `data/sentiment_test.csv`: 2,000 reviews, held out for final evaluation
- `data/sentiment_hard_test.csv`: 120 hard cases, held out for additional evaluation

The test and hard-test datasets were not used during fitting.

## Production model

- `services/sentiment_classifier.pkl`
- `dataset/linear_svm_sentiment_model_fulltrain.pkl`

Model pipeline:

1. TF-IDF word features
2. Unigrams + bigrams
3. Linear SVM (`LinearSVC`)
4. Balanced class weights

## Evaluation

On the untouched 2,000-review test set:

- Accuracy: **96.10%**
- Negative precision: **100.00%**
- Negative recall: **90.25%**
- Negative F1: **94.88%**
- Missed negative reviews: **78 / 800**

On the 120-review hard-test set:

- Accuracy: **92.50%**
- Negative precision: **97.56%**
- Negative recall: **100.00%**
- Negative F1: **98.77%**

## Application integration

`services/sentiment.py` now loads the Linear SVM model while preserving the existing:

```python
sentiment, confidence = score_sentiment(review_text)
```

interface used by `routes/reviews.py`.

Linear SVM does not provide calibrated `predict_proba()` values. The existing API `confidence` field is therefore populated from a softmax transformation of the SVM decision scores. It should be treated as **relative model confidence**, not a calibrated probability.

## Retraining

Run:

```bash
python dataset/train_classifier.py
```

This retrains using train + validation data and evaluates against the untouched test and hard-test datasets before saving the production model.
