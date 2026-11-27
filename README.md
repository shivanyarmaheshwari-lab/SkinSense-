# SkinSense Simple Working Version

This version uses a short, stable flow:

1. Welcome screen, language, and name
2. Take a picture or upload image
3. Answer up to 6 questions
4. Result page

Removed to prevent Streamlit crashes:

- Chatbot
- Recovery tracking

## Files To Upload To GitHub

```text
app.py
requirements.txt
.python-version
Skin_Disease_Question_Matrix.xlsx
best.pt
class_names.json
skinsense_logo.png
.streamlit/secrets.toml.example
```

`best.pt` and `class_names.json` come from the YOLO classification training run.

## Where To Update Your Datasets

### Image Dataset

Open `SkinSense_Colab_Train.py`.

Change this line:

```python
RAW_DATASET_DIR = "/content/Dataset"
```

That path must point to your unzipped image dataset folder in Colab.

The training script now uses Ultralytics YOLO26 classification with eight classes. The
dataset must contain `train/` and `val/` folders, each containing the same eight class
folders. The old Keras training workflow is no longer used.

After retraining, download:

```text
best.pt
class_names.json
```

Put both beside `app.py`.

### Text / Question Dataset

Put this file beside `app.py`:

```text
Skin_Disease_Question_Matrix.xlsx
```

The Streamlit app reads this line:

```python
QUESTION_MATRIX_PATH = BASE_DIR / "Skin_Disease_Question_Matrix.xlsx"
```

## Streamlit Cloud Important Setting

Use Python `3.12`.

If Streamlit Cloud uses Python `3.14`, TensorFlow will fail to install.

## Run Locally

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## What The App Does

- The YOLO26 image model predicts the top 3 disease matches.
- The app asks up to 6 questions from the Excel matrix based on those matches.
- The final page shows one predicted disease, risk percentage, what to do now, and when to see a dermatologist.
- The SkinSense header uses `skinsense_logo.png`, so keep that file beside `app.py`.
- The result is a screening estimate, not a medical diagnosis.

## Current Model Audit

The supplied `content 2` folder contains the YOLO26 training output and validation
artifacts, but not the original image folders. From `results.csv`, the best validation
top-1 accuracy is `76.623%` at epoch 5 and the final epoch top-1 accuracy is `72.294%`.
The validation set contains 231 images. The validation supports reported by the
confusion matrix are:

| Class | Validation images |
| --- | ---: |
| Actinic Keratosis | 20 |
| Cutaneous Candidiasis | 13 |
| Folliculitis / Furunculosis | 1 |
| Impetigo | 27 |
| Irritant Contact Dermatitis | 63 |
| Occupational Hand Eczema | 9 |
| Sunburn / Photodermatitis | 18 |
| Tinea (Ringworm / Athlete's Foot) | 80 |

Because the original image folders were not included, the full train/validation image
counts and image-quality checks cannot be independently recomputed from this upload.
The one-image validation class should be treated as especially unreliable until it is
retrained with more representative validation images.

## Google Sheets Name Tracking

The app saves:

```text
Name
Time of entry
Date of entry
AI Prediction
AI Match Accuracy
```

To make this work on Streamlit Cloud:

1. Create a Google Sheet with a worksheet named `Sheet1`.
2. Share the Sheet with your service-account `client_email`.
3. In Streamlit Cloud, open `App settings -> Secrets`.
4. Paste your secrets using the format in `.streamlit/secrets.toml.example`.

Do not upload a real `.streamlit/secrets.toml` file to GitHub.

If Sheets fails, the app still opens and logs the technical error privately.
