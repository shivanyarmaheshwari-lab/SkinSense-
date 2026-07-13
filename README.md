# SkinSense Simple Working Version

This version uses a short, stable flow:

1. Name + language
2. Take a picture or upload image
3. Answer 5 questions
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
skinsense_model.keras
class_names.json
skinsense_logo.png
.streamlit/secrets.toml.example
```

The last two files come from Colab after training.

## Where To Update Your Datasets

### Image Dataset

Open `SkinSense_Colab_Train.py`.

Change this line:

```python
RAW_DATASET_DIR = "/content/Dataset"
```

That path must point to your unzipped image dataset folder in Colab.

The latest training notebook/script uses class weights because the dataset is imbalanced. This should improve rare classes like Impetigo, Athlete's Foot, and Cellulitis.

After retraining, download:

```text
skinsense_model.keras
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

- The image model predicts the top 3 disease matches.
- The app asks 5 questions from the Excel matrix based on those matches.
- The final page shows one predicted disease, risk percentage, what to do now, and when to see a dermatologist.
- The SkinSense header uses `skinsense_logo.png`, so keep that file beside `app.py`.
- The result is a screening estimate, not a medical diagnosis.

## Google Sheets Name Tracking

The app saves only:

```text
Timestamp
Name
```

To make this work on Streamlit Cloud:

1. Create a Google Sheet with a worksheet named `Sheet1`.
2. Share the Sheet with your service-account `client_email`.
3. In Streamlit Cloud, open `App settings -> Secrets`.
4. Paste your secrets using the format in `.streamlit/secrets.toml.example`.

Do not upload a real `.streamlit/secrets.toml` file to GitHub.

If Sheets fails, the app still opens and logs the technical error privately.
