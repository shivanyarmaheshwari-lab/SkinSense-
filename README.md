# SkinSense Simple Working Version

This version uses a short, stable flow:

1. Name + language
2. Upload image
3. Answer 5 questions
4. Result page

Removed to prevent Streamlit crashes:

- Chatbot
- Camera/take-photo page
- Recovery tracking
- Google Sheets login tracking

## Files To Upload To GitHub

```text
app.py
requirements.txt
.python-version
Skin_Disease_Question_Matrix.xlsx
skinsense_model.keras
class_names.json
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

After training, download:

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
- The final result combines image confidence and question answers.
- The result is a screening estimate, not a medical diagnosis.
