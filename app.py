from __future__ import annotations

import base64
import json
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from html import escape
from io import BytesIO
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import numpy as np
import streamlit as st
from PIL import Image, UnidentifiedImageError
from zoneinfo import ZoneInfo

try:
    import tensorflow as tf
except Exception:
    tf = None

try:
    import gspread
    from google.oauth2.service_account import Credentials
except Exception:
    gspread = None
    Credentials = None


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


st.set_page_config(
    page_title="SkinSense",
    page_icon="🩺",
    layout="centered",
    initial_sidebar_state="collapsed",
)


BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "skinsense_model.keras"
CLASS_NAMES_PATH = BASE_DIR / "class_names.json"
QUESTION_MATRIX_PATH = BASE_DIR / "Skin_Disease_Question_Matrix.xlsx"
LOGO_PATH = BASE_DIR / "skinsense_logo.png"

DEFAULT_GOOGLE_SHEET_ID = "1VCwoQWGVI-9y7m9WGlWQlM4nSZ4Hs0F6TqexuuMYbPU"
DEFAULT_WORKSHEET_NAME = "Sheet1"

IMAGE_SIZE = (224, 224)
MAX_IMAGE_MB = 10

VALID_PAGES = {"start", "upload", "questions", "result"}
ANSWER_OPTIONS = ["Yes", "No", "Sometimes", "I don't know"]

GOOGLE_SCOPES = (
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
)


LANG = {
    "English": {
        "title": "SkinSense",
        "subtitle": "AI skin screening support for fishing communities.",
        "description": "Simple skin screening for Koli fisherwomen and fishermen exposed to seawater, sun, and wet work.",
        "name": "Enter your name",
        "name_placeholder": "Your name",
        "language": "Choose language",
        "continue": "Continue",
        "upload_title": "Show us the skin problem",
        "upload_help": "Take or upload a clear photo in good light, close to the skin.",
        "camera": "Take a photo",
        "gallery": "Choose from gallery",
        "analyze": "Continue",
        "questions_title": "A few simple questions",
        "questions_help": "Answer these so SkinSense can refine the result.",
        "result": "See result",
        "back": "Back",
        "home": "Home",
        "logout": "Logout",
        "disclaimer": "SkinSense is a screening aid, not a medical diagnosis. Please see a dermatologist for serious or worsening symptoms.",
    },
    "हिंदी": {
        "title": "SkinSense",
        "subtitle": "मछुआरा समुदायों के लिए AI त्वचा जांच सहायता।",
        "description": "समुद्री पानी, धूप और गीले काम से जुड़ी त्वचा समस्याओं के लिए आसान स्क्रीनिंग।",
        "name": "अपना नाम लिखें",
        "name_placeholder": "आपका नाम",
        "language": "भाषा चुनें",
        "continue": "जारी रखें",
        "upload_title": "त्वचा की समस्या दिखाएं",
        "upload_help": "अच्छी रोशनी में त्वचा के पास से साफ फोटो लें या अपलोड करें।",
        "camera": "फोटो लें",
        "gallery": "गैलरी से चुनें",
        "analyze": "जारी रखें",
        "questions_title": "कुछ आसान सवाल",
        "questions_help": "इन जवाबों से SkinSense परिणाम बेहतर कर पाएगा।",
        "result": "परिणाम देखें",
        "back": "पीछे",
        "home": "होम",
        "logout": "लॉग आउट",
        "disclaimer": "SkinSense केवल स्क्रीनिंग सहायता है, मेडिकल diagnosis नहीं। गंभीर या बढ़ते लक्षणों में dermatologist से मिलें।",
    },
    "मराठी": {
        "title": "SkinSense",
        "subtitle": "मच्छीमार समुदायांसाठी AI त्वचा तपासणी मदत.",
        "description": "समुद्राचे पाणी, ऊन आणि ओल्या कामामुळे होणाऱ्या त्वचा समस्यांसाठी सोपी स्क्रीनिंग.",
        "name": "तुमचे नाव लिहा",
        "name_placeholder": "तुमचे नाव",
        "language": "भाषा निवडा",
        "continue": "पुढे जा",
        "upload_title": "त्वचेची समस्या दाखवा",
        "upload_help": "चांगल्या प्रकाशात त्वचेच्या जवळून स्पष्ट फोटो घ्या किंवा अपलोड करा.",
        "camera": "फोटो घ्या",
        "gallery": "गॅलरीतून निवडा",
        "analyze": "पुढे जा",
        "questions_title": "काही सोपे प्रश्न",
        "questions_help": "या उत्तरांमुळे SkinSense परिणाम सुधारेल.",
        "result": "परिणाम पहा",
        "back": "मागे",
        "home": "होम",
        "logout": "लॉग आउट",
        "disclaimer": "SkinSense ही फक्त स्क्रीनिंग मदत आहे, वैद्यकीय diagnosis नाही. गंभीर किंवा वाढणाऱ्या लक्षणांसाठी dermatologist ला भेटा.",
    },
}


DISEASE_INFO = {
    "Irritant Contact Dermatitis": {
        "what": "Your skin may be irritated from salt water, soap, fish handling, or repeated wet work.",
        "prevention": "Rinse with clean water, dry well, and use a gentle moisturiser after work.",
    },
    "Occupational Hand Eczema": {
        "what": "This may be work-related eczema from frequent wet work and repeated irritation.",
        "prevention": "Keep hands dry when possible and moisturise after washing.",
    },
    "Athlete’s Foot / Tinea Pedis": {
        "what": "This may be a fungal infection, often seen between toes or on damp feet.",
        "prevention": "Keep feet dry, change wet socks, and avoid staying in wet footwear.",
    },
    "Athlete's Foot / Tinea Pedis": {
        "what": "This may be a fungal infection, often seen between toes or on damp feet.",
        "prevention": "Keep feet dry, change wet socks, and avoid staying in wet footwear.",
    },
    "Ringworm / Tinea Corporis": {
        "what": "This may be a fungal rash that can look circular and may spread.",
        "prevention": "Keep the area dry and avoid sharing towels or clothing.",
    },
    "Cutaneous Candidiasis": {
        "what": "This may be a yeast-related rash, often in moist skin folds.",
        "prevention": "Keep the area clean, dry, and avoid tight wet clothing.",
    },
    "Folliculitis": {
        "what": "This may be inflammation or infection around hair follicles.",
        "prevention": "Avoid scratching and keep the area clean and dry.",
    },
    "Cellulitis": {
        "what": "This can be a deeper skin infection and may need quick medical care.",
        "prevention": "Do not scratch or squeeze the area. Keep it clean and covered.",
    },
    "Impetigo": {
        "what": "This may be a contagious bacterial skin infection.",
        "prevention": "Avoid touching the area and do not share towels.",
    },
    "Sunburn": {
        "what": "This may be skin damage from strong sun exposure.",
        "prevention": "Cover skin, use shade, and apply sunscreen when outdoors.",
    },
    "Actinic Keratosis": {
        "what": "This may be a rough sun-damaged patch that should be checked by a dermatologist.",
        "prevention": "Protect the area from sun and avoid repeated direct exposure.",
    },
    "Healthy Skin": {
        "what": "The image may not show a clear skin disease pattern.",
        "prevention": "Keep skin clean, dry, and protected from harsh sun and salt water.",
    },
}


DEFAULT_QUESTIONS = [
    "Does the skin problem itch, burn or hurt?",
    "Is it spreading or getting bigger?",
    "Are your hands or feet in sea water for many hours every day?",
    "Have you had this problem for more than 2 weeks?",
    "Do you see pus, bleeding, or a bad smell?",
]


@dataclass
class PredictionResult:
    condition: str
    confidence: float
    risk_percent: int
    risk_level: str
    what_to_do: str
    dermatologist: str
    prevention: str


def add_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #eef8fb;
            --navy: #071f3d;
            --blue: #1479ad;
            --soft-blue: #d8ebff;
            --muted: #51657d;
            --border: #d5e5ee;
            --white: #ffffff;
        }

        html, body, [class*="stApp"] {
            background: var(--bg) !important;
            color: var(--navy) !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        .block-container {
            max-width: 860px;
            padding-top: 5.5rem;
            padding-bottom: 3rem;
        }

        h1, h2, h3 {
            color: var(--navy) !important;
            letter-spacing: 0 !important;
        }

        h1 {
            font-size: clamp(2.2rem, 6vw, 3.8rem) !important;
            line-height: 1.05 !important;
            font-weight: 850 !important;
        }

        h2 {
            font-size: clamp(1.8rem, 5vw, 2.7rem) !important;
            font-weight: 800 !important;
        }

        h3 {
            font-size: 1.35rem !important;
            font-weight: 800 !important;
        }

        p, li, label, span, div {
            color: var(--navy);
        }

        .stMarkdown p {
            color: var(--muted);
            font-size: 1.08rem;
            line-height: 1.55;
        }

        .brand-bar {
            display: flex;
            align-items: center;
            gap: 1rem;
            padding-bottom: 1.3rem;
            margin-bottom: 2.3rem;
            border-bottom: 1px solid var(--border);
        }

        .brand-logo {
            width: 72px;
            height: 72px;
            border-radius: 999px;
            object-fit: cover;
            background: white;
        }

        .brand-title {
            font-size: 1.45rem;
            font-weight: 850;
            color: var(--navy);
            margin: 0;
        }

        .brand-subtitle {
            font-size: 1rem;
            color: var(--muted);
            margin-top: .15rem;
        }

        .hero-subtitle {
            color: var(--blue) !important;
            font-size: 1.55rem !important;
            font-weight: 800 !important;
            margin-bottom: .75rem !important;
        }

        .section {
            margin-top: 1.4rem;
            margin-bottom: 1.4rem;
        }

        div[data-testid="stForm"], div[data-testid="stVerticalBlockBorderWrapper"] {
            background: rgba(255, 255, 255, 0.72);
            border-radius: 24px;
        }

        .stTextInput label, .stRadio label, .stCameraInput label, .stFileUploader label {
            color: var(--navy) !important;
            font-size: 1rem !important;
            font-weight: 800 !important;
        }

        .stTextInput input {
            background: var(--white) !important;
            color: var(--navy) !important;
            border: 1px solid var(--border) !important;
            border-radius: 18px !important;
            min-height: 3.2rem;
            font-size: 1.05rem !important;
        }

        .stTextInput input::placeholder {
            color: #7f8da0 !important;
            opacity: 1 !important;
        }

        div[role="radiogroup"] label,
        div[role="radiogroup"] span,
        div[role="radiogroup"] p {
            color: var(--navy) !important;
            font-size: 1.05rem !important;
            font-weight: 650 !important;
        }

        .stButton > button, .stFormSubmitButton > button {
            border-radius: 999px !important;
            border: 1px solid var(--blue) !important;
            background: var(--blue) !important;
            color: white !important;
            min-height: 3.35rem;
            font-size: 1.05rem !important;
            font-weight: 800 !important;
            box-shadow: 0 14px 30px rgba(20, 121, 173, 0.14);
        }

        .stButton > button p, .stFormSubmitButton > button p {
            color: white !important;
            font-weight: 800 !important;
        }

        .stButton > button:hover, .stFormSubmitButton > button:hover {
            background: #0f658f !important;
            border-color: #0f658f !important;
            color: white !important;
        }

        .result-card {
            background: white;
            border: 1px solid var(--border);
            border-radius: 26px;
            padding: 1.5rem;
            margin: 1rem 0;
        }

        .result-title {
            color: var(--navy);
            font-size: 1.15rem;
            font-weight: 850;
            text-transform: uppercase;
            letter-spacing: .08em;
            margin-bottom: .35rem;
        }

        .result-big {
            color: var(--navy);
            font-size: clamp(2rem, 7vw, 3.4rem);
            font-weight: 900;
            line-height: 1.05;
        }

        .risk-number {
            color: #159947;
            font-size: clamp(2.4rem, 8vw, 4.1rem);
            font-weight: 900;
        }

        .soft-box {
            background: var(--soft-blue);
            border-radius: 22px;
            padding: 1rem 1.2rem;
            color: var(--navy);
            margin-top: .9rem;
        }

        .warn-box {
            background: #fff7c7;
            border-radius: 22px;
            padding: 1rem 1.2rem;
            color: var(--navy);
            margin-top: .9rem;
        }

        .good-box {
            background: #d5f8e4;
            border-radius: 22px;
            padding: 1rem 1.2rem;
            color: var(--navy);
            margin-top: .9rem;
        }

        @media (max-width: 640px) {
            .block-container {
                padding-top: 3rem;
            }

            .brand-logo {
                width: 58px;
                height: 58px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def text(key: str) -> str:
    lang = st.session_state.get("language", "English")
    return LANG.get(lang, LANG["English"]).get(key, LANG["English"].get(key, key))


def clean_name(value: str) -> str:
    value = re.sub(r"[\x00-\x1f\x7f]", "", value or "")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def normalize_private_key(value: Any) -> str:
    key = str(value).strip()
    key = key.replace("\\n", "\n").replace("\r\n", "\n")
    if "-----BEGIN PRIVATE KEY-----" not in key:
        raise ValueError("Private key is missing BEGIN marker.")
    if "-----END PRIVATE KEY-----" not in key:
        raise ValueError("Private key is missing END marker.")
    return key.rstrip() + "\n"


def get_secret_section(*names: str) -> dict[str, Any] | None:
    try:
        for name in names:
            if name in st.secrets:
                return dict(st.secrets[name])
    except Exception:
        return None
    return None


def get_sheet_config() -> tuple[str, str]:
    sheet_id = DEFAULT_GOOGLE_SHEET_ID
    worksheet = DEFAULT_WORKSHEET_NAME

    try:
        if "google_sheet_id" in st.secrets:
            sheet_id = str(st.secrets["google_sheet_id"])
        if "worksheet_name" in st.secrets:
            worksheet = str(st.secrets["worksheet_name"])

        if "google_sheets" in st.secrets:
            gs = st.secrets["google_sheets"]
            sheet_id = str(gs.get("spreadsheet_id", sheet_id))
            worksheet = str(gs.get("worksheet_name", worksheet))
    except Exception:
        pass

    return sheet_id, worksheet


@st.cache_resource(show_spinner=False)
def get_gspread_client():
    if gspread is None or Credentials is None:
        raise RuntimeError("Google Sheets packages are not installed.")

    info = get_secret_section(
        "gcp_service_account",
        "google_service_account",
        "service_account",
    )

    if not info:
        raise RuntimeError("Google service account secrets are not configured.")

    required = [
        "type",
        "project_id",
        "private_key_id",
        "private_key",
        "client_email",
        "client_id",
        "auth_uri",
        "token_uri",
        "auth_provider_x509_cert_url",
        "client_x509_cert_url",
    ]

    missing = [key for key in required if not info.get(key)]
    if missing:
        raise RuntimeError("Google service account secrets are incomplete.")

    info["private_key"] = normalize_private_key(info["private_key"])
    credentials = Credentials.from_service_account_info(info, scopes=list(GOOGLE_SCOPES))
    return gspread.authorize(credentials)


def append_login_to_sheet(name: str) -> bool:
    if st.session_state.get("login_tracking_attempted"):
        return bool(st.session_state.get("login_tracking_saved"))

    st.session_state["login_tracking_attempted"] = True
    st.session_state["login_tracking_saved"] = False

    try:
        client = get_gspread_client()
        sheet_id, worksheet_name = get_sheet_config()
        worksheet = client.open_by_key(sheet_id).worksheet(worksheet_name)
        timestamp = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(timespec="seconds")
        worksheet.append_row([timestamp, name], value_input_option="RAW")
        st.session_state["login_tracking_saved"] = True
        return True
    except Exception:
        logger.exception("Google Sheets usage tracking failed")
        st.session_state["tracking_warning"] = True
        return False


def init_state() -> None:
    defaults = {
        "screen": "start",
        "logged_in": False,
        "user_name": "",
        "language": "English",
        "image_bytes": None,
        "image_name": None,
        "image_time": None,
        "top_predictions": [],
        "initial_condition": None,
        "initial_confidence": 0.0,
        "questions": [],
        "answers": {},
        "final_result": None,
        "login_tracking_attempted": False,
        "login_tracking_saved": False,
        "tracking_warning": False,
    }

    for key, value in defaults.items():
        st.session_state.setdefault(key, value)

    if st.session_state.get("screen") not in VALID_PAGES:
        st.session_state["screen"] = "start"


def go(screen: str) -> None:
    if screen not in VALID_PAGES:
        screen = "start"
    st.session_state["screen"] = screen
    st.rerun()


def logout() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def logo_html() -> str:
    if LOGO_PATH.exists():
        encoded = base64.b64encode(LOGO_PATH.read_bytes()).decode("utf-8")
        return f'<img class="brand-logo" src="data:image/png;base64,{encoded}" alt="SkinSense logo">'
    return '<div class="brand-logo" style="display:grid;place-items:center;font-size:2rem;background:#075579;color:white;">🩺</div>'


def brand_header(show_logout: bool = True) -> None:
    st.markdown(
        f"""
        <div class="brand-bar">
            {logo_html()}
            <div>
                <div class="brand-title">SkinSense</div>
                <div class="brand-subtitle">Coastal Skin Care Workspace</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if show_logout and st.session_state.get("logged_in"):
        _, col = st.columns([3, 1])
        with col:
            if st.button(text("logout"), use_container_width=True, key="logout_btn"):
                logout()


@st.cache_resource(show_spinner=False)
def load_class_names() -> list[str]:
    if CLASS_NAMES_PATH.exists():
        with open(CLASS_NAMES_PATH, "r", encoding="utf-8") as file:
            names = json.load(file)
        if isinstance(names, dict):
            names = [names[str(i)] for i in range(len(names))]
        return [str(name) for name in names]

    return list(DISEASE_INFO.keys())


@st.cache_resource(show_spinner=False)
def load_model():
    if tf is None:
        raise RuntimeError("TensorFlow is not installed.")
    if not MODEL_PATH.exists():
        raise FileNotFoundError("Model file skinsense_model.keras was not found.")
    return tf.keras.models.load_model(MODEL_PATH)


def validate_image(uploaded_file: Any) -> tuple[bytes, Image.Image]:
    if uploaded_file is None:
        raise ValueError("Please upload or take a photo first.")

    data = uploaded_file.getvalue()
    size_mb = len(data) / (1024 * 1024)
    if size_mb > MAX_IMAGE_MB:
        raise ValueError(f"Image is too large. Please use an image under {MAX_IMAGE_MB} MB.")

    try:
        image = Image.open(BytesIO(data))
        image.verify()
        image = Image.open(BytesIO(data)).convert("RGB")
    except UnidentifiedImageError as exc:
        raise ValueError("This file is not a valid image.") from exc

    if image.width < 20 or image.height < 20:
        raise ValueError("The image is too small. Please use a clearer photo.")

    return data, image


def preprocess_image(image_bytes: bytes) -> np.ndarray:
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    image = image.resize(IMAGE_SIZE)
    array = np.asarray(image, dtype=np.float32) / 255.0
    return np.expand_dims(array, axis=0)


def softmax(values: np.ndarray) -> np.ndarray:
    values = values.astype(np.float64)
    values = values - np.max(values)
    exp = np.exp(values)
    return exp / np.sum(exp)


def run_image_inference(image_bytes: bytes) -> tuple[str, float, list[tuple[str, float]]]:
    class_names = load_class_names()
    model = load_model()

    batch = preprocess_image(image_bytes)
    raw = model.predict(batch, verbose=0)
    vector = np.asarray(raw[0], dtype=np.float64)

    if len(vector) != len(class_names):
        raise RuntimeError(
            f"Model output has {len(vector)} classes, but class_names.json has {len(class_names)} labels."
        )

    if np.min(vector) < 0 or np.max(vector) > 1.0 or not np.isclose(np.sum(vector), 1.0, atol=0.05):
        probs = softmax(vector)
    else:
        probs = vector / np.sum(vector)

    order = np.argsort(probs)[::-1]
    top = [(class_names[i], float(probs[i])) for i in order[:3]]
    return top[0][0], top[0][1], top


def read_xlsx_rows(path: Path) -> list[list[str]]:
    if not path.exists():
        return []

    with ZipFile(path) as archive:
        shared_strings: list[str] = []

        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            for item in root.findall("a:si", ns):
                parts = [node.text or "" for node in item.findall(".//a:t", ns)]
                shared_strings.append("".join(parts))

        sheet_name = "xl/worksheets/sheet1.xml"
        if sheet_name not in archive.namelist():
            return []

        root = ET.fromstring(archive.read(sheet_name))
        ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

        rows = []
        for row in root.findall(".//a:row", ns):
            values = []
            for cell in row.findall("a:c", ns):
                value_node = cell.find("a:v", ns)
                if value_node is None:
                    values.append("")
                    continue

                value = value_node.text or ""
                if cell.attrib.get("t") == "s":
                    try:
                        value = shared_strings[int(value)]
                    except Exception:
                        value = ""

                values.append(value)
            rows.append(values)

    return rows


@st.cache_data(show_spinner=False)
def load_question_matrix() -> dict[str, list[str]]:
    rows = read_xlsx_rows(QUESTION_MATRIX_PATH)
    if not rows:
        return {}

    header = [cell.strip().lower() for cell in rows[0]]
    disease_idx = 0
    question_indices = list(range(1, min(6, len(header))))

    for i, name in enumerate(header):
        if "disease" in name or "condition" in name:
            disease_idx = i
        if "question" in name:
            question_indices.append(i)

    question_indices = sorted(set(question_indices))
    matrix: dict[str, list[str]] = {}

    for row in rows[1:]:
        if disease_idx >= len(row):
            continue

        disease = row[disease_idx].strip()
        if not disease:
            continue

        questions = []
        for i in question_indices:
            if i < len(row) and row[i].strip():
                questions.append(row[i].strip())

        if questions:
            matrix[disease] = questions[:5]

    return matrix


def get_questions_for_condition(condition: str) -> list[str]:
    matrix = load_question_matrix()

    if condition in matrix:
        return matrix[condition][:5]

    lower = condition.lower()
    for disease, questions in matrix.items():
        if disease.lower() == lower:
            return questions[:5]

    return DEFAULT_QUESTIONS


def calculate_risk(condition: str, confidence: float, answers: dict[str, str]) -> tuple[int, str, str]:
    yes_count = sum(1 for answer in answers.values() if answer == "Yes")
    sometimes_count = sum(1 for answer in answers.values() if answer == "Sometimes")

    risk = int(round(confidence * 70))
    risk += yes_count * 6
    risk += sometimes_count * 3

    urgent_words = ["pus", "bleeding", "bad smell", "fever", "swelling", "severe"]
    urgent_answer = False

    for question, answer in answers.items():
        if answer == "Yes" and any(word in question.lower() for word in urgent_words):
            urgent_answer = True

    if condition in {"Cellulitis", "Impetigo"}:
        risk += 12

    risk = max(1, min(98, risk))

    if urgent_answer or risk >= 75:
        return risk, "High", "Please see a dermatologist or doctor as soon as possible, especially if pain, swelling, pus, fever, or fast spreading is present."

    if risk >= 45:
        return risk, "Medium", "Please see a dermatologist soon if it does not improve, spreads, or keeps coming back."

    return risk, "Low", "You can monitor it at home, but see a dermatologist if it gets worse or does not improve."


def build_final_result() -> PredictionResult:
    condition = st.session_state.get("initial_condition") or "Skin concern"
    confidence = float(st.session_state.get("initial_confidence") or 0.0)
    answers = dict(st.session_state.get("answers") or {})

    risk_percent, risk_level, dermatologist = calculate_risk(condition, confidence, answers)
    info = DISEASE_INFO.get(condition, {})

    return PredictionResult(
        condition=condition,
        confidence=confidence,
        risk_percent=risk_percent,
        risk_level=risk_level,
        what_to_do=info.get("what", "The image may show a skin concern that should be monitored carefully."),
        dermatologist=dermatologist,
        prevention=info.get("prevention", "Keep the area clean and dry, and avoid scratching it."),
    )


def start_page() -> None:
    brand_header(show_logout=False)

    st.markdown(f"# {text('title')}")
    st.markdown(f"<p class='hero-subtitle'>{escape(text('subtitle'))}</p>", unsafe_allow_html=True)
    st.markdown(text("description"))

    with st.form("start_form"):
        name = st.text_input(text("name"), placeholder=text("name_placeholder"))
        language = st.radio(
            text("language"),
            ["मराठी", "हिंदी", "English"],
            index=["मराठी", "हिंदी", "English"].index(st.session_state.get("language", "English")),
            horizontal=True,
        )
        submitted = st.form_submit_button(text("continue"), use_container_width=True)

    if submitted:
        cleaned = clean_name(name)

        if not cleaned:
            st.warning("Please enter your name.")
            return

        if len(cleaned) > 80:
            st.warning("Please enter a shorter name.")
            return

        st.session_state["logged_in"] = True
        st.session_state["user_name"] = cleaned
        st.session_state["language"] = language

        append_login_to_sheet(cleaned)
        go("upload")

    st.markdown(f"<div class='soft-box'>{escape(text('disclaimer'))}</div>", unsafe_allow_html=True)


def upload_page() -> None:
    brand_header()

    st.markdown(f"## {text('upload_title')}")
    st.markdown(text("upload_help"))

    tab_camera, tab_gallery = st.tabs([text("camera"), text("gallery")])

    uploaded = None

    with tab_camera:
        uploaded = st.camera_input(text("camera"), key="camera_input")

    with tab_gallery:
        gallery_file = st.file_uploader(
            text("gallery"),
            type=["jpg", "jpeg", "png"],
            key="gallery_input",
        )
        if gallery_file is not None:
            uploaded = gallery_file

    if uploaded is not None:
        try:
            image_bytes, image = validate_image(uploaded)
            st.session_state["image_bytes"] = image_bytes
            st.session_state["image_name"] = getattr(uploaded, "name", "camera_photo.png")
            st.session_state["image_time"] = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(timespec="seconds")
            st.image(image, caption="Uploaded image", use_container_width=True)
        except ValueError as exc:
            st.error(str(exc))

    if st.session_state.get("image_bytes"):
        if st.button(text("analyze"), use_container_width=True, key="analyze_btn"):
            try:
                with st.spinner("Checking the image..."):
                    condition, confidence, top = run_image_inference(st.session_state["image_bytes"])
                st.session_state["initial_condition"] = condition
                st.session_state["initial_confidence"] = confidence
                st.session_state["top_predictions"] = top
                st.session_state["questions"] = get_questions_for_condition(condition)
                st.session_state["answers"] = {}
                go("questions")
            except Exception as exc:
                logger.exception("Image inference failed")
                st.error(
                    "The AI model could not run. Please check that skinsense_model.keras and class_names.json are uploaded correctly."
                )
                st.caption(str(exc))

    if st.button(text("back"), use_container_width=True, key="upload_back_btn"):
        go("start")


def questions_page() -> None:
    brand_header()

    questions = st.session_state.get("questions") or DEFAULT_QUESTIONS

    st.markdown(f"## {text('questions_title')}")
    st.markdown(text("questions_help"))

    with st.form("questions_form"):
        answers = {}
        for index, question in enumerate(questions[:5], start=1):
            st.markdown(f"### Q{index}. {question}")
            answers[question] = st.radio(
                f"Answer for question {index}",
                ANSWER_OPTIONS,
                index=None,
                horizontal=True,
                label_visibility="collapsed",
                key=f"question_{index}",
            )

        submitted = st.form_submit_button(text("result"), use_container_width=True)

    if submitted:
        unanswered = [question for question, answer in answers.items() if not answer]
        if unanswered:
            st.warning("Please answer all the questions before continuing.")
            return

        st.session_state["answers"] = answers
        st.session_state["final_result"] = build_final_result()
        go("result")

    if st.button(text("back"), use_container_width=True, key="questions_back_btn"):
        go("upload")


def result_page() -> None:
    brand_header()

    result = st.session_state.get("final_result")
    if result is None:
        result = build_final_result()
        st.session_state["final_result"] = result

    if st.session_state.get("image_bytes"):
        st.image(st.session_state["image_bytes"], caption="Photo checked", use_container_width=True)

    risk_color = {
        "Low": "#159947",
        "Medium": "#d49100",
        "High": "#d43b3b",
    }.get(result.risk_level, "#159947")

    st.markdown(
        f"""
        <div class="result-card">
            <div class="result-title">Possible condition</div>
            <div class="result-big">{escape(result.condition)}</div>
            <p>{escape(result.what_to_do)}</p>
        </div>

        <div class="result-card">
            <div class="result-title">Risk percentage</div>
            <div style="font-size:1.25rem;font-weight:850;color:{risk_color};">{escape(result.risk_level)} risk</div>
            <div class="risk-number" style="color:{risk_color};">{result.risk_percent}%</div>
        </div>

        <h3>What you can do</h3>
        <div class="good-box">{escape(result.prevention)}</div>

        <h3>When to see a dermatologist</h3>
        <div class="warn-box">{escape(result.dermatologist)}</div>

        <div class="soft-box">{escape(text('disclaimer'))}</div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Check another image", use_container_width=True, key="another_btn"):
            st.session_state["image_bytes"] = None
            st.session_state["image_name"] = None
            st.session_state["image_time"] = None
            st.session_state["top_predictions"] = []
            st.session_state["initial_condition"] = None
            st.session_state["initial_confidence"] = 0.0
            st.session_state["questions"] = []
            st.session_state["answers"] = {}
            st.session_state["final_result"] = None
            go("upload")

    with col2:
        if st.button(text("home"), use_container_width=True, key="result_home_btn"):
            go("upload")


def main() -> None:
    add_css()
    init_state()

    if not st.session_state.get("logged_in"):
        st.session_state["screen"] = "start"

    if st.session_state.get("tracking_warning") and st.session_state.get("logged_in"):
        st.warning("SkinSense opened successfully, but usage tracking could not be saved.")

    pages = {
        "start": start_page,
        "upload": upload_page,
        "questions": questions_page,
        "result": result_page,
    }

    screen = st.session_state.get("screen", "start")
    pages.get(screen, start_page)()

if __name__ == "__main__":
    main()
