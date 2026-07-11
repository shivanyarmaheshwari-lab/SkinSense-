import json
import logging
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st


logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="SkinSense",
    page_icon="✋",
    layout="centered",
    initial_sidebar_state="expanded",
)


# ============================================================
# CHANGE THESE VALUES IF YOUR FILE NAMES OR SHEET CHANGE
# ============================================================
DEFAULT_GOOGLE_SHEET_ID = "1VCwoQWGVI-9y7m9WGlWQlM4nSZ4Hs0F6TqexuuMYbPU"
QUESTION_BANK_FILE = "skinsense_questions.xlsx"
MODEL_FILE = "skinsense_model.keras"
LABELS_FILE = "skinsense_labels.json"
IMAGE_SIZE = 224


ANSWER_OPTIONS = ["Choose one", "Yes", "No", "I don't know", "Maybe"]
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


DISEASE_INFO = {
    "Irritant Contact Dermatitis": {
        "risk": 72,
        "doctor": "Visit a dermatologist soon if it does not improve or keeps coming back.",
        "advice": [
            "Rinse skin with clean water after fishing work.",
            "Keep the affected area dry when possible.",
            "Use clean dry gloves when handling fish or wet nets.",
        ],
    },
    "Occupational Hand Eczema": {
        "risk": 70,
        "doctor": "Visit a dermatologist soon if cracking, pain, or repeated flare-ups continue.",
        "advice": [
            "Avoid long contact with wet gloves when possible.",
            "Dry hands well after work.",
            "Use a simple moisturizer if available.",
        ],
    },
    "Athlete's Foot": {
        "risk": 66,
        "doctor": "Visit a dermatologist if itching, peeling, or cracks continue.",
        "advice": [
            "Dry between your toes after work.",
            "Change wet socks quickly.",
            "Keep boots dry when possible.",
        ],
    },
    "Ringworm": {
        "risk": 78,
        "doctor": "Visit a dermatologist soon because fungal rashes can spread.",
        "advice": [
            "Keep the rash dry.",
            "Do not share towels or gloves.",
            "Avoid scratching the area.",
        ],
    },
    "Cutaneous Candidiasis": {
        "risk": 70,
        "doctor": "Visit a dermatologist if redness, itching, or wet skin folds continue.",
        "advice": [
            "Keep skin folds dry.",
            "Change wet clothes quickly.",
            "Avoid scratching the area.",
        ],
    },
    "Folliculitis": {
        "risk": 74,
        "doctor": "Visit a dermatologist if bumps are painful, spreading, or filled with pus.",
        "advice": [
            "Keep the area clean.",
            "Avoid squeezing bumps.",
            "Use clean clothing and towels.",
        ],
    },
    "Cellulitis": {
        "risk": 91,
        "doctor": "Seek medical help immediately, especially with fever, swelling, heat, pus, or severe pain.",
        "advice": [
            "Do not wait if the area is hot, swollen, or very painful.",
            "Keep the area clean.",
            "Avoid squeezing or scratching the skin.",
        ],
    },
    "Impetigo": {
        "risk": 78,
        "doctor": "Visit a dermatologist soon because bacterial skin infections can spread.",
        "advice": [
            "Do not scratch sores.",
            "Wash hands after touching the area.",
            "Avoid sharing towels.",
        ],
    },
    "Sunburn": {
        "risk": 58,
        "doctor": "Manage at home unless there are blisters, fever, or severe pain.",
        "advice": [
            "Cool the skin with clean water.",
            "Drink water.",
            "Cover skin during strong sun.",
        ],
    },
    "Actinic Keratosis": {
        "risk": 76,
        "doctor": "Visit a dermatologist soon for rough or scaly sun-damaged patches.",
        "advice": [
            "Protect skin from strong sun.",
            "Do not pick rough patches.",
            "Ask a doctor to check long-lasting spots.",
        ],
    },
}


FALLBACK_QUESTIONS = {
    "Irritant Contact Dermatitis": [
        ("Did it start after working in sea water?", 0.20, 0.0, 0.05, 0.0),
        ("Does the skin burn or sting?", 0.12, 0.0, 0.04, 0.0),
        ("Is the skin dry or cracked?", 0.10, 0.0, 0.04, 0.0),
    ],
    "Occupational Hand Eczema": [
        ("Has this been happening again and again on your hands?", 0.18, 0.0, 0.05, 0.0),
        ("Are your hands dry, cracked, or thickened?", 0.18, 0.0, 0.05, 0.0),
    ],
    "Athlete's Foot": [
        ("Is it between your toes?", 0.25, -0.12, 0.05, 0.0),
        ("Are your feet often wet inside boots?", 0.18, 0.0, 0.05, 0.0),
        ("Is there peeling or cracking on your feet?", 0.16, 0.0, 0.05, 0.0),
    ],
    "Ringworm": [
        ("Is the rash circular?", 0.25, -0.12, 0.05, 0.0),
        ("Is the edge of the rash more red than the center?", 0.15, 0.0, 0.04, 0.0),
        ("Is it itchy?", 0.12, 0.0, 0.04, 0.0),
    ],
    "Cutaneous Candidiasis": [
        ("Is the area usually wet or sweaty?", 0.18, 0.0, 0.05, 0.0),
        ("Is it in a skin fold?", 0.20, 0.0, 0.05, 0.0),
    ],
    "Folliculitis": [
        ("Do you see small bumps around hair roots?", 0.20, 0.0, 0.05, 0.0),
        ("Are the bumps painful or filled with pus?", 0.22, 0.0, 0.06, 0.0),
    ],
    "Cellulitis": [
        ("Is it painful, swollen, or warm?", 0.25, 0.0, 0.08, 0.0),
        ("Do you see pus, bleeding, or a bad smell?", 0.30, 0.0, 0.10, 0.0),
        ("Do you have fever?", 0.30, 0.0, 0.10, 0.0),
    ],
    "Impetigo": [
        ("Do you see yellow or honey-colored crust?", 0.25, 0.0, 0.08, 0.0),
        ("Are there open sores or blisters?", 0.18, 0.0, 0.05, 0.0),
    ],
    "Sunburn": [
        ("Did it start after strong sunlight?", 0.25, 0.0, 0.05, 0.0),
        ("Does the skin feel hot or burning?", 0.18, 0.0, 0.05, 0.0),
    ],
    "Actinic Keratosis": [
        ("Is the patch rough or scaly?", 0.25, 0.0, 0.08, 0.0),
        ("Has it been there for many weeks?", 0.18, 0.0, 0.06, 0.0),
    ],
}


def apply_branding() -> None:
    """Small, stable CSS only for typography and simple branding."""
    st.markdown(
        """
        <style>
        :root {
            --skinsense-bg: #eef8fb;
            --skinsense-navy: #071f3d;
            --skinsense-teal: #0b7f8a;
        }
        .stApp {
            background: var(--skinsense-bg);
        }
        h1, h2, h3 {
            color: var(--skinsense-navy);
        }
        .skinsense-logo {
            width: 5rem;
            height: 5rem;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: var(--skinsense-teal);
            color: white;
            font-size: 2.4rem;
            margin-bottom: 0.75rem;
        }
        .muted-copy {
            color: #4f6678;
            font-size: 1.08rem;
            line-height: 1.45;
        }
        .small-label {
            color: #4f6678;
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0.12rem;
            text-transform: uppercase;
        }
        .result-name {
            font-size: 1.8rem;
            font-weight: 800;
            color: var(--skinsense-navy);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state() -> None:
    """Create all session keys used by the app."""
    defaults = {
        "logged_in": False,
        "user_name": "",
        "screen": "language",
        "language": "English",
        "uploaded_name": "",
        "top_3_predictions": None,
        "question_rows": [],
        "prediction": None,
        "chat_history": [],
        "login_tracking_attempted": False,
        "login_tracking_saved": False,
        "login_tracking_warning": "",
        "login_tracking_warning_shown": False,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def clean_name(value: str) -> str:
    """Trim, remove control characters, and validate a simple display name."""
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", str(value or "")).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def normalize_private_key(value: str) -> str:
    """Normalize PEM newlines without changing Base64 content."""
    key = str(value or "").strip()
    key = key.replace("\\n", "\n").replace("\r\n", "\n").replace("\r", "\n")

    begin = "-----BEGIN PRIVATE KEY-----"
    end = "-----END PRIVATE KEY-----"
    if begin not in key or end not in key:
        raise ValueError("The Google service-account private key is malformed or incomplete.")

    start = key.index(begin)
    finish = key.index(end) + len(end)
    key = key[start:finish]

    lines = [line.strip() for line in key.split("\n") if line.strip()]
    normalized = "\n".join(lines) + "\n"
    if not normalized.startswith(begin) or not normalized.rstrip().endswith(end):
        raise ValueError("The Google service-account private key is malformed or incomplete.")
    return normalized


def get_credentials_section() -> dict:
    """Read one supported service-account section from Streamlit Secrets."""
    section_names = ("gcp_service_account", "google_service_account", "service_account")
    for section_name in section_names:
        if section_name in st.secrets:
            return dict(st.secrets[section_name])
    raise KeyError("Missing Google service-account credentials in Streamlit Secrets.")


def build_google_config() -> tuple[str, str, dict]:
    """Validate Google Sheet settings and credentials without logging secrets."""
    sheet_id = st.secrets.get("google_sheet_id", DEFAULT_GOOGLE_SHEET_ID)
    worksheet_name = st.secrets.get("worksheet_name", "Sheet1")
    credentials_info = get_credentials_section()

    required_fields = ("type", "project_id", "private_key", "client_email", "token_uri")
    missing_fields = [field for field in required_fields if not credentials_info.get(field)]
    if not sheet_id:
        missing_fields.append("google_sheet_id")
    if missing_fields:
        raise ValueError("Missing required Google configuration values.")

    credentials_info["private_key"] = normalize_private_key(credentials_info["private_key"])
    return str(sheet_id).strip(), str(worksheet_name).strip() or "Sheet1", credentials_info


def append_login_to_sheet(name: str) -> bool:
    """Append one login row. Exceptions are logged but never shown raw to users."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except Exception:
        logger.exception("Google Sheets login tracking failed: missing Google packages")
        return False

    try:
        sheet_id, worksheet_name, credentials_info = build_google_config()
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=GOOGLE_SCOPES,
        )
        client = gspread.authorize(credentials)
        spreadsheet = client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet(worksheet_name)
        timestamp = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(timespec="seconds")
        worksheet.append_row([timestamp, name], value_input_option="RAW")
        return True
    except KeyError:
        logger.exception("Google Sheets login tracking failed: missing Streamlit secrets")
    except ValueError:
        logger.exception("Google Sheets login tracking failed: malformed TOML values or private key")
    except gspread.exceptions.SpreadsheetNotFound:
        logger.exception("Google Sheets login tracking failed: incorrect spreadsheet ID or sheet not shared")
    except gspread.exceptions.WorksheetNotFound:
        logger.exception("Google Sheets login tracking failed: missing worksheet")
    except gspread.exceptions.APIError:
        logger.exception("Google Sheets login tracking failed: Google API or permission error")
    except Exception:
        logger.exception("Google Sheets login tracking failed")
    return False


def complete_name_entry(name: str) -> tuple[bool, str]:
    """Validate the user's name and enter the app even if tracking fails."""
    cleaned_name = clean_name(name)
    if not cleaned_name:
        return False, "Please enter your name to continue."
    if len(cleaned_name) > 80:
        return False, "Please use a shorter name, up to 80 characters."

    st.session_state["logged_in"] = True
    st.session_state["user_name"] = cleaned_name
    st.session_state["screen"] = "language"

    if not st.session_state.get("login_tracking_attempted"):
        st.session_state["login_tracking_attempted"] = True
        saved = append_login_to_sheet(cleaned_name)
        st.session_state["login_tracking_saved"] = saved
        if not saved:
            st.session_state["login_tracking_warning"] = (
                "You are signed in, but usage tracking could not be saved."
            )

    return True, "Welcome to SkinSense."


def logout() -> None:
    """Clear the session and return to the name-entry screen."""
    st.session_state.clear()
    st.rerun()


def render_sidebar() -> None:
    """Sidebar controls shown after the user enters the app."""
    with st.sidebar:
        st.subheader("SkinSense")
        st.write(f"Name: **{st.session_state.get('user_name', '')}**")
        st.divider()
        if st.button("Home", use_container_width=True):
            st.session_state["screen"] = "language"
            st.rerun()
        if st.button("Logout", use_container_width=True):
            logout()


def login_page() -> None:
    """Simple name entry. This is not OAuth or secure authentication."""
    left, center, right = st.columns([1, 1.4, 1])
    with center:
        with st.container(border=True):
            st.markdown('<div class="skinsense-logo">✋</div>', unsafe_allow_html=True)
            st.title("Welcome to SkinSense")
            st.markdown(
                '<p class="muted-copy">Coastal skin care support for Koli fisherwomen and fishermen.</p>',
                unsafe_allow_html=True,
            )
            with st.form("name_entry_form", clear_on_submit=False):
                name = st.text_input("Enter your name", max_chars=80)
                submitted = st.form_submit_button("Continue", use_container_width=True)
            if submitted:
                success, message = complete_name_entry(name)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.warning(message)


def show_tracking_warning_once() -> None:
    """Show non-blocking tracking warning once after successful name entry."""
    warning = st.session_state.get("login_tracking_warning")
    shown = st.session_state.get("login_tracking_warning_shown")
    if warning and not shown:
        st.warning(warning)
        st.session_state["login_tracking_warning_shown"] = True


@st.cache_resource
def load_skin_model():
    """Load the optional image model and labels."""
    model_path = Path(MODEL_FILE)
    labels_path = Path(LABELS_FILE)
    if not model_path.exists() or not labels_path.exists():
        return None, None, "Model files are not uploaded yet, so demo predictions are being used."

    try:
        import tensorflow as tf
    except Exception:
        logger.exception("Skin model loading failed: missing TensorFlow")
        return None, None, "TensorFlow is not installed, so demo predictions are being used."

    try:
        model = tf.keras.models.load_model(model_path)
        with labels_path.open("r", encoding="utf-8") as file:
            labels = json.load(file)
        return model, labels, None
    except Exception:
        logger.exception("Skin model loading failed")
        return None, None, "The model could not be loaded, so demo predictions are being used."


def demo_top_three() -> list[dict]:
    """Fallback top-3 predictions while the trained model is not uploaded."""
    return [
        {"disease": "Irritant Contact Dermatitis", "score": 0.62},
        {"disease": "Ringworm", "score": 0.48},
        {"disease": "Athlete's Foot", "score": 0.35},
    ]


def predict_top_three_from_image(uploaded_file) -> tuple[list[dict], str | None]:
    """Return top-3 model predictions for an uploaded image."""
    model, labels, warning = load_skin_model()
    if warning:
        return demo_top_three(), warning

    try:
        import numpy as np
        from PIL import Image
    except Exception:
        logger.exception("Image prediction failed: missing image packages")
        return demo_top_three(), "Image packages are missing, so demo predictions are being used."

    try:
        uploaded_file.seek(0)
        image = Image.open(uploaded_file).convert("RGB")
        image = image.resize((IMAGE_SIZE, IMAGE_SIZE))
        image_array = np.array(image)
        image_array = np.expand_dims(image_array, axis=0)
        predictions = model.predict(image_array, verbose=0)[0]
        top_indices = np.argsort(predictions)[-3:][::-1]
        top_three = [
            {"disease": labels[int(index)], "score": float(predictions[int(index)])}
            for index in top_indices
        ]
        return top_three, None
    except Exception:
        logger.exception("Image prediction failed")
        return demo_top_three(), "The image could not be analyzed, so demo predictions are being used."


@st.cache_data
def load_question_bank(question_bank_file: str):
    """Load disease-specific question rows from Excel."""
    try:
        import pandas as pd
    except Exception:
        logger.exception("Question bank loading failed: missing pandas/openpyxl")
        return None, "Question bank needs pandas and openpyxl in requirements.txt."

    try:
        is_url = str(question_bank_file).startswith(("http://", "https://"))
        if not is_url and not Path(question_bank_file).exists():
            return None, "Excel question bank was not found. Default questions are being used."

        df = pd.read_excel(question_bank_file)
        df.columns = (
            df.columns.astype(str).str.strip().str.lower().str.replace(" ", "_")
        )
        required_columns = {"disease", "question"}
        missing_columns = required_columns - set(df.columns)
        if missing_columns:
            return None, "Excel question bank is missing disease or question columns."

        for column in ("yes_boost", "no_boost", "maybe_boost", "dont_know_boost"):
            if column not in df.columns:
                df[column] = 0.0
            df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0.0)

        df["disease"] = df["disease"].astype(str).str.strip()
        df["question"] = df["question"].astype(str).str.strip()
        df = df[(df["disease"] != "") & (df["question"] != "")]
        return df, None
    except Exception:
        logger.exception("Question bank loading failed")
        return None, "Excel question bank could not be read. Default questions are being used."


def fallback_question_rows(top_three: list[dict]) -> list[dict]:
    """Return up to five built-in question rows for the current top three diseases."""
    rows = []
    for item in top_three:
        disease = item["disease"]
        for question, yes_boost, no_boost, maybe_boost, dont_know_boost in FALLBACK_QUESTIONS.get(disease, []):
            rows.append(
                {
                    "disease": disease,
                    "question": question,
                    "yes_boost": yes_boost,
                    "no_boost": no_boost,
                    "maybe_boost": maybe_boost,
                    "dont_know_boost": dont_know_boost,
                }
            )
    return rows[:5]


def choose_question_rows(top_three: list[dict]) -> tuple[list[dict], str | None]:
    """Choose five questions from Excel based on the top three model diseases."""
    top_diseases = [item["disease"] for item in top_three]
    question_bank, warning = load_question_bank(QUESTION_BANK_FILE)
    if question_bank is None:
        return fallback_question_rows(top_three), warning

    filtered = question_bank[question_bank["disease"].isin(top_diseases)].copy()
    if filtered.empty:
        return fallback_question_rows(top_three), "No Excel questions matched the top three diseases."

    disease_order = {disease: index for index, disease in enumerate(top_diseases)}
    filtered["disease_order"] = filtered["disease"].map(disease_order)
    filtered = filtered.sort_values(["disease_order"]).drop_duplicates("question")
    rows = filtered.head(5).to_dict("records")
    if len(rows) < 5:
        fallback = fallback_question_rows(top_three)
        seen = {row["question"] for row in rows}
        for row in fallback:
            if row["question"] not in seen:
                rows.append(row)
                seen.add(row["question"])
            if len(rows) == 5:
                break
    return rows[:5], warning


def refine_prediction(top_three: list[dict], question_rows: list[dict], answers: dict) -> dict:
    """Refine image-model scores using answer boosts from Excel or fallback rules."""
    scores = {item["disease"]: float(item["score"]) for item in top_three}

    for row in question_rows:
        disease = row["disease"]
        question = row["question"]
        answer = answers.get(question, "Choose one")
        if disease not in scores:
            continue
        if answer == "Yes":
            scores[disease] += float(row.get("yes_boost", 0))
        elif answer == "No":
            scores[disease] += float(row.get("no_boost", 0))
        elif answer == "Maybe":
            scores[disease] += float(row.get("maybe_boost", 0))
        elif answer == "I don't know":
            scores[disease] += float(row.get("dont_know_boost", 0))

    scores = {disease: max(0.0, min(score, 0.96)) for disease, score in scores.items()}
    disease = max(scores, key=scores.get)
    risk = round(scores[disease] * 100)
    info = DISEASE_INFO.get(disease, DISEASE_INFO["Irritant Contact Dermatitis"]).copy()
    info.update(
        {
            "name": disease,
            "risk": risk,
            "scores": scores,
            "level": "High" if risk >= 80 else "Medium" if risk >= 60 else "Low",
        }
    )
    return info


def language_page() -> None:
    st.title("SkinSense")
    st.subheader("AI skin screening for fishing communities")
    st.caption(f"Welcome, {st.session_state.get('user_name', '')}")

    with st.container(border=True):
        st.markdown('<p class="small-label">Choose your language</p>', unsafe_allow_html=True)
        choice = st.radio(
            "Language",
            ["Marathi", "Hindi", "English"],
            horizontal=True,
            label_visibility="collapsed",
        )
        st.session_state["language"] = choice
        if st.button("Continue", use_container_width=True):
            st.session_state["screen"] = "menu"
            st.rerun()

    st.info(
        "SkinSense is a screening aid, not a medical diagnosis. For serious or worsening symptoms, please visit a dermatologist."
    )


def menu_page() -> None:
    st.title("What would you like to do?")
    check_col, chat_col = st.columns(2)
    with check_col:
        with st.container(border=True):
            st.header("📷 Check my skin")
            st.write("Upload or take a photo of the skin problem and get a quick check.")
            if st.button("Start skin check", use_container_width=True):
                st.session_state["screen"] = "upload"
                st.rerun()
    with chat_col:
        with st.container(border=True):
            st.header("💬 Ask a question")
            st.write("Ask simple questions about skin care, sea water, sun, itching, or rashes.")
            if st.button("Open skin helper", use_container_width=True):
                st.session_state["screen"] = "chat"
                st.rerun()


def upload_page() -> None:
    st.title("Show us the skin problem")
    st.write("Take a clear photo in good light, close to the affected skin.")

    with st.form("image_upload_form"):
        camera_photo = st.camera_input("Take a photo")
        uploaded_photo = st.file_uploader("Or choose from gallery", type=["jpg", "jpeg", "png"])
        submitted = st.form_submit_button("Continue", use_container_width=True)

    image_file = camera_photo or uploaded_photo
    if image_file:
        st.image(image_file, caption="Selected image", use_container_width=True)

    if submitted:
        if image_file is None:
            st.warning("Please take or upload a photo first.")
            return
        st.session_state["uploaded_name"] = getattr(image_file, "name", "camera_photo.jpg")
        with st.status("Checking image...", expanded=False):
            top_three, warning = predict_top_three_from_image(image_file)
            st.session_state["top_3_predictions"] = top_three
            question_rows, question_warning = choose_question_rows(top_three)
            st.session_state["question_rows"] = question_rows
        if warning:
            st.info(warning)
        if question_warning:
            st.info(question_warning)
        st.session_state["screen"] = "questions"
        st.rerun()


def questions_page() -> None:
    top_three = st.session_state.get("top_3_predictions") or demo_top_three()
    question_rows = st.session_state.get("question_rows") or choose_question_rows(top_three)[0]

    st.title("A few simple questions")
    st.write("These five questions are chosen from the top three possible image results.")

    with st.expander("Top three possible results"):
        for item in top_three:
            st.write(f"{item['disease']}: {round(item['score'] * 100)}%")

    with st.form("followup_questions_form"):
        answers = {}
        for index, row in enumerate(question_rows, start=1):
            answers[row["question"]] = st.selectbox(
                f"Q{index}. {row['question']}",
                ANSWER_OPTIONS,
                key=f"answer_{index}",
            )
        submitted = st.form_submit_button("See result", use_container_width=True)

    if submitted:
        unanswered = [answer for answer in answers.values() if answer == "Choose one"]
        if unanswered:
            st.warning("Please choose an answer for each question. Use “I don't know” if unsure.")
            return
        st.session_state["prediction"] = refine_prediction(top_three, question_rows, answers)
        st.session_state["screen"] = "result"
        st.rerun()


def result_page() -> None:
    prediction = st.session_state.get("prediction")
    if not prediction:
        st.session_state["screen"] = "upload"
        st.rerun()

    st.caption("Your result")
    st.markdown(f'<div class="result-name">{prediction["name"]}</div>', unsafe_allow_html=True)
    st.write("This is an early screening result based on the image and your answers.")

    with st.container(border=True):
        st.subheader("Risk level")
        st.metric(label=prediction["level"], value=f"{prediction['risk']}%")
        st.progress(min(prediction["risk"], 100) / 100)

    with st.container(border=True):
        st.subheader("When to see a dermatologist")
        st.success(prediction["doctor"])

    with st.container(border=True):
        st.subheader("What you can do")
        for item in prediction["advice"]:
            st.write(f"✓ {item}")

    st.warning("This is not a medical diagnosis. It is only a guide. If it gets worse, please see a doctor.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Check another", use_container_width=True):
            st.session_state["screen"] = "upload"
            st.session_state["prediction"] = None
            st.rerun()
    with col2:
        if st.button("Home", use_container_width=True):
            st.session_state["screen"] = "menu"
            st.rerun()


def chat_answer(question: str) -> str:
    """Simple rule-based helper for common skin care questions."""
    q = question.lower()
    if "toe" in q or "white" in q:
        return "White patches between toes can happen when feet stay wet. Dry between toes and see a dermatologist if it spreads."
    if "salt" in q or "water" in q or "sea" in q:
        return "Rinse with clean water after work, dry well, change wet gloves or boots, and cover small cuts."
    if "itch" in q:
        return "Do not scratch. Wash gently, dry the skin, and avoid wet gloves for long periods."
    if "doctor" in q or "dermatologist" in q:
        return "See a dermatologist if there is pain, pus, swelling, fever, spreading, or no improvement."
    return "Keep the skin clean and dry. If symptoms worsen, please see a dermatologist."


def chat_page() -> None:
    st.title("Ask about skin care")
    st.write("Ask simple questions about skin problems from sea water, sun, or fishing work.")

    prompts = [
        "My hands itch after fishing",
        "How to protect skin from salt water?",
        "White patches between my toes",
    ]
    cols = st.columns(3)
    for col, prompt in zip(cols, prompts):
        with col:
            if st.button(prompt, use_container_width=True):
                st.session_state["chat_history"].append(("user", prompt))
                st.session_state["chat_history"].append(("assistant", chat_answer(prompt)))
                st.rerun()

    for role, message in st.session_state["chat_history"]:
        with st.chat_message(role):
            st.write(message)

    question = st.chat_input("Type your question...")
    if question:
        st.session_state["chat_history"].append(("user", question))
        st.session_state["chat_history"].append(("assistant", chat_answer(question)))
        st.rerun()


def main() -> None:
    init_state()
    apply_branding()

    if not st.session_state.get("logged_in"):
        login_page()
        return

    render_sidebar()
    show_tracking_warning_once()

    screen = st.session_state.get("screen", "language")
    if screen == "language":
        language_page()
    elif screen == "menu":
        menu_page()
    elif screen == "upload":
        upload_page()
    elif screen == "questions":
        questions_page()
    elif screen == "result":
        result_page()
    elif screen == "chat":
        chat_page()
    else:
        st.session_state["screen"] = "language"
        st.rerun()


if __name__ == "__main__":
    main()
