from __future__ import annotations

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
from zoneinfo import ZoneInfo

import numpy as np
import streamlit as st
from PIL import Image, UnidentifiedImageError
from tensorflow.keras.models import load_model


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# ============================================================
# UPDATE THESE FILES AFTER TRAINING IN COLAB
# ============================================================
BASE_DIR = Path(__file__).resolve().parent

# Put the model downloaded from Colab in the same GitHub folder as app.py.
MODEL_PATH = BASE_DIR / "skinsense_model.keras"

# Put the class_names.json downloaded from Colab in the same GitHub folder as app.py.
CLASS_NAMES_PATH = BASE_DIR / "class_names.json"

# Put your Excel text/question dataset in the same GitHub folder as app.py.
QUESTION_MATRIX_PATH = BASE_DIR / "Skin_Disease_Question_Matrix.xlsx"

# Google Sheets name tracking. These can be overridden in Streamlit Secrets.
DEFAULT_GOOGLE_SHEET_ID = "1VCwoQWGVI-9y7m9WGlWQlM4nSZ4Hs0F6TqexuuMYbPU"
DEFAULT_WORKSHEET_NAME = "Sheet1"
GOOGLE_SCOPES = (
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
)


# ============================================================
# App settings
# ============================================================
st.set_page_config(
    page_title="SkinSense",
    page_icon="🩺",
    layout="centered",
    initial_sidebar_state="collapsed",
)

IMAGE_SIZE = (224, 224)
MAX_IMAGE_MB = 10
ANSWER_OPTIONS = ["Yes", "No", "Sometimes", "I don't know"]
VALID_PAGES = {"start", "upload", "questions", "result"}


TEXT = {
    "English": {
        "tagline": "AI skin screening support for fishing communities.",
        "name": "Enter your name",
        "language": "Choose language",
        "continue": "Continue",
        "upload_title": "Upload a clear skin photo",
        "upload_help": "Take a new photo or upload a JPG/PNG under 10 MB. Keep the skin close to the camera in good light.",
        "questions_title": "Answer 5 simple questions",
        "result_title": "Your SkinSense result",
        "disclaimer": "SkinSense is a screening aid, not a medical diagnosis. Please see a dermatologist for serious or worsening symptoms.",
    },
    "हिंदी": {
        "tagline": "मछुआरा समुदायों के लिए AI त्वचा स्क्रीनिंग सहायता.",
        "name": "अपना नाम लिखें",
        "language": "भाषा चुनें",
        "continue": "आगे बढ़ें",
        "upload_title": "त्वचा की साफ फोटो अपलोड करें",
        "upload_help": "नई फोटो लें या 10 MB से कम JPG/PNG अपलोड करें. फोटो अच्छी रोशनी में त्वचा के पास से लें.",
        "questions_title": "5 आसान सवालों के जवाब दें",
        "result_title": "आपका SkinSense परिणाम",
        "disclaimer": "SkinSense स्क्रीनिंग सहायता है, मेडिकल निदान नहीं. गंभीर या बढ़ते लक्षणों के लिए त्वचा डॉक्टर से मिलें.",
    },
    "मराठी": {
        "tagline": "मच्छीमार समुदायांसाठी AI त्वचा स्क्रीनिंग मदत.",
        "name": "तुमचे नाव लिहा",
        "language": "भाषा निवडा",
        "continue": "पुढे",
        "upload_title": "त्वचेचा स्पष्ट फोटो अपलोड करा",
        "upload_help": "नवीन फोटो घ्या किंवा 10 MB पेक्षा कमी JPG/PNG अपलोड करा. चांगल्या प्रकाशात जवळून फोटो घ्या.",
        "questions_title": "5 सोप्या प्रश्नांची उत्तरे द्या",
        "result_title": "तुमचा SkinSense निकाल",
        "disclaimer": "SkinSense ही स्क्रीनिंग मदत आहे, वैद्यकीय निदान नाही. गंभीर किंवा वाढणाऱ्या लक्षणांसाठी त्वचा डॉक्टरांना भेटा.",
    },
}


DISEASE_INFO = {
    "Irritant Contact Dermatitis": "Often linked with repeated contact with seawater, detergents, fish fluids, or wet gloves.",
    "Occupational Hand Eczema": "A recurring hand rash that can be worsened by wet work, friction, and irritants.",
    "Athlete's Foot (Tinea pedis)": "A fungal infection that often affects skin between the toes or feet kept wet in boots.",
    "Ringworm (Tinea corporis)": "A fungal rash that can look circular or ring-shaped with a red edge.",
    "Cutaneous Candidiasis": "A yeast infection that can happen in moist skin folds.",
    "Paronychia": "Inflammation or infection around a fingernail or toenail.",
    "Folliculitis": "Inflamed hair follicles that can look like small pimples or bumps.",
    "Cellulitis": "A deeper skin infection that can spread and may need urgent medical care.",
    "Impetigo": "A contagious bacterial skin infection that may form yellow crusting or fluid.",
    "Sunburn": "Skin irritation or injury after sun exposure.",
    "Actinic Keratosis": "A rough sun-damaged patch that should be checked by a dermatologist.",
}


DERM_GUIDANCE = {
    "Cellulitis": "See a dermatologist or doctor as soon as possible, especially if redness spreads, skin feels warm, pain increases, or fever appears.",
    "Impetigo": "See a dermatologist soon if sores spread, leak fluid, form yellow crust, or others at home develop similar sores.",
    "Paronychia": "See a dermatologist soon if swelling, pus, or nail pain gets worse.",
    "Actinic Keratosis": "Book a dermatologist visit soon because rough sun-damaged patches should be checked.",
    "Sunburn": "See a doctor if there are large blisters, fever, severe pain, dizziness, or dehydration.",
    "Ringworm (Tinea corporis)": "See a dermatologist if it spreads, does not improve, or keeps coming back.",
    "Athlete's Foot (Tinea pedis)": "See a dermatologist if cracks, swelling, pus, or spreading redness appears.",
    "Cutaneous Candidiasis": "See a dermatologist if the rash spreads, becomes painful, or keeps returning.",
    "Folliculitis": "See a dermatologist if bumps become painful, form pus, or spread quickly.",
    "Occupational Hand Eczema": "See a dermatologist if cracks are painful, bleeding, or keep returning with wet work.",
    "Irritant Contact Dermatitis": "See a dermatologist if it does not improve after avoiding irritants or if skin cracks and bleeds.",
}


PREVENTION_TIP = {
    "Cellulitis": "Keep the area clean and cover cuts quickly so germs do not enter broken skin.",
    "Impetigo": "Do not scratch or share towels, and wash hands after touching the area.",
    "Paronychia": "Keep fingers and toes dry and avoid cutting nails too short.",
    "Actinic Keratosis": "Use sun protection and cover the area when working outdoors.",
    "Sunburn": "Cover skin from strong sun and reapply sunscreen when outdoors.",
    "Ringworm (Tinea corporis)": "Keep the area dry and avoid sharing towels or clothing.",
    "Athlete's Foot (Tinea pedis)": "Dry between toes after seawater work and change wet socks/footwear.",
    "Cutaneous Candidiasis": "Keep skin folds dry and change out of wet clothes quickly.",
    "Folliculitis": "Avoid friction and keep the skin clean after sweating or seawater work.",
    "Occupational Hand Eczema": "Rinse hands after seawater work, dry well, and use a simple moisturizer.",
    "Irritant Contact Dermatitis": "Rinse off seawater/irritants and moisturize after work.",
}


@dataclass
class Prediction:
    condition: str
    image_confidence: float
    final_score: float
    risk_percentage: int
    top_predictions: list[tuple[str, float]]
    urgency: str
    advice: str
    prevention: str
    explanation: str


def css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #eef9fc;
            --navy: #071f3d;
            --blue: #1479ad;
            --deep-blue: #064765;
            --muted: #50647a;
            --line: #d9e9f0;
            --soft-blue: #d8ebff;
            --white: #ffffff;
            --green-soft: #d7fae8;
            --yellow-soft: #fff8bf;
        }
        .stApp { background: var(--bg); }
        .block-container {
            max-width: 860px;
            padding-top: 1.4rem;
            padding-bottom: 3rem;
        }
        h1, h2, h3, p, label, li, span {
            color: var(--navy);
        }
        h1 {
            font-size: 3rem;
            line-height: 1.05;
            margin-bottom: .7rem;
            letter-spacing: 0;
        }
        h2 { font-size: 2rem; }
        h3 { font-size: 1.35rem; }
        .topbar {
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 0 0 26px 0;
            margin-bottom: 24px;
            border-bottom: 1px solid var(--line);
        }
        .brand-icon {
            width: 64px;
            height: 64px;
            border-radius: 50%;
            background: var(--deep-blue);
            color: #ffffff;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 31px;
            flex: 0 0 auto;
        }
        .brand-name {
            color: var(--navy);
            font-size: 1.45rem;
            font-weight: 900;
            line-height: 1.1;
        }
        .brand-subtitle {
            color: var(--muted);
            font-size: 1.08rem;
            font-weight: 500;
            margin-top: 4px;
        }
        .lead-blue {
            color: var(--blue);
            font-size: 1.5rem;
            font-weight: 850;
            margin-bottom: .8rem;
        }
        .body-copy {
            color: var(--muted);
            font-size: 1.22rem;
            line-height: 1.45;
            margin-bottom: 2rem;
        }
        .disclaimer-box {
            background: var(--soft-blue);
            color: var(--navy);
            border-radius: 22px;
            padding: 22px 26px;
            font-size: 1.05rem;
            line-height: 1.5;
            margin-top: 26px;
        }
        .result-panel {
            background: var(--white);
            border: 1px solid var(--line);
            border-radius: 22px;
            padding: 24px;
            margin: 16px 0;
        }
        .result-kicker {
            color: var(--muted);
            font-size: .86rem;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: .08em;
            margin-bottom: .35rem;
        }
        .result-disease {
            color: var(--navy);
            font-size: 2.35rem;
            font-weight: 950;
            line-height: 1.08;
        }
        .risk-big {
            color: #18a24f;
            font-size: 4rem;
            font-weight: 950;
            line-height: 1;
        }
        .soft-green {
            background: var(--green-soft);
            color: var(--navy);
            border-radius: 22px;
            padding: 22px 26px;
            font-size: 1.2rem;
            line-height: 1.5;
        }
        .soft-yellow {
            background: var(--yellow-soft);
            color: var(--navy);
            border-radius: 22px;
            padding: 22px 26px;
            font-size: 1.2rem;
            line-height: 1.5;
        }
        input, textarea {
            color: var(--navy) !important;
        }
        .stButton > button, .stFormSubmitButton > button {
            min-height: 52px;
            border-radius: 14px;
            font-weight: 850;
            font-size: 1.05rem;
            background: #ffffff !important;
            border: 1px solid var(--blue) !important;
            color: var(--navy) !important;
        }
        .stButton > button p, .stFormSubmitButton > button p {
            color: var(--navy) !important;
            font-weight: 850 !important;
        }
        .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
            background: var(--blue) !important;
            border-color: var(--blue) !important;
            color: #ffffff !important;
        }
        .stButton > button[kind="primary"] p, .stFormSubmitButton > button[kind="primary"] p {
            color: #ffffff !important;
        }
        div[role="radiogroup"] label p {
            color: var(--navy) !important;
            font-size: 1.05rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def brand_header() -> None:
    st.markdown(
        """
        <div class="topbar">
            <div class="brand-icon">🖐</div>
            <div>
                <div class="brand-name">SkinSense</div>
                <div class="brand-subtitle">Coastal Skin Care Workspace</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def t(key: str) -> str:
    language = st.session_state.get("language", "English")
    return TEXT.get(language, TEXT["English"]).get(key, key)


def clean_name(name: str) -> str:
    name = re.sub(r"[\x00-\x1f\x7f]", "", name or "")
    return re.sub(r"\s+", " ", name).strip()


def init_state() -> None:
    defaults = {
        "page": "start",
        "name": "",
        "language": "English",
        "image_bytes": None,
        "image_name": "",
        "image_prediction": None,
        "question_list": [],
        "answers": {},
        "final_prediction": None,
        "name_logged_to_sheet": False,
        "sheet_warning": "",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def go(page: str) -> None:
    st.session_state["page"] = page if page in VALID_PAGES else "start"
    st.rerun()


def normalize_private_key(value: Any) -> str:
    key = str(value or "").strip()
    key = key.replace("\\n", "\n").replace("\r\n", "\n").replace("\r", "\n")
    begin_marker = "-----BEGIN PRIVATE KEY-----"
    end_marker = "-----END PRIVATE KEY-----"
    if begin_marker not in key or end_marker not in key:
        raise ValueError("Malformed service-account private key.")
    start = key.index(begin_marker)
    end = key.index(end_marker) + len(end_marker)
    lines = [line.strip() for line in key[start:end].split("\n") if line.strip()]
    return "\n".join(lines) + "\n"


def get_secret_text(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, default)).strip()
    except Exception:
        return default


def get_service_account_info() -> dict[str, Any]:
    try:
        for section_name in ("gcp_service_account", "google_service_account", "service_account"):
            if section_name in st.secrets:
                info = dict(st.secrets[section_name])
                break
        else:
            raise RuntimeError("No service-account section found.")
    except Exception as exc:
        raise RuntimeError("Google Sheets credentials are missing.") from exc

    required_fields = ("type", "project_id", "private_key", "client_email", "token_uri")
    missing_fields = [field for field in required_fields if not info.get(field)]
    if missing_fields:
        raise RuntimeError("Google Sheets credentials are incomplete.")

    info["private_key"] = normalize_private_key(info["private_key"])
    return info


def get_sheet_config() -> tuple[str, str]:
    sheet_id = get_secret_text("google_sheet_id", DEFAULT_GOOGLE_SHEET_ID)
    worksheet_name = get_secret_text("worksheet_name", DEFAULT_WORKSHEET_NAME)

    try:
        if "google_sheets" in st.secrets:
            google_sheets = dict(st.secrets["google_sheets"])
            sheet_id = str(google_sheets.get("spreadsheet_id", sheet_id)).strip()
            worksheet_name = str(google_sheets.get("worksheet_name", worksheet_name)).strip()
    except Exception:
        pass

    return sheet_id or DEFAULT_GOOGLE_SHEET_ID, worksheet_name or DEFAULT_WORKSHEET_NAME


@st.cache_resource(show_spinner=False)
def authorize_gspread(credentials_json: str):
    import gspread
    from google.oauth2.service_account import Credentials

    credentials_info = json.loads(credentials_json)
    credentials = Credentials.from_service_account_info(credentials_info, scopes=list(GOOGLE_SCOPES))
    return gspread.authorize(credentials)


def append_name_to_sheet(name: str) -> bool:
    """Append one name row to Google Sheets without blocking the app if it fails."""
    try:
        credentials_info = get_service_account_info()
        sheet_id, worksheet_name = get_sheet_config()
        client = authorize_gspread(json.dumps(credentials_info, sort_keys=True))
        worksheet = client.open_by_key(sheet_id).worksheet(worksheet_name)
        timestamp = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(timespec="seconds")
        worksheet.append_row([timestamp, name], value_input_option="RAW")
        return True
    except Exception:
        logger.exception("Google Sheets name tracking failed")
        return False


def cell_text(cell: ET.Element, shared_strings: list[str], ns: dict[str, str]) -> str:
    if cell.attrib.get("t") == "inlineStr":
        return "".join((node.text or "") for node in cell.findall(".//a:t", ns)).strip()
    value = cell.find("a:v", ns)
    if value is None:
        return ""
    raw = value.text or ""
    if cell.attrib.get("t") == "s" and raw.isdigit():
        return shared_strings[int(raw)].strip()
    return raw.strip()


def col_index(cell_ref: str) -> int:
    letters = "".join(char for char in cell_ref if char.isalpha())
    number = 0
    for char in letters:
        number = number * 26 + ord(char.upper()) - 64
    return number - 1


@st.cache_data(show_spinner=False)
def load_question_matrix() -> tuple[list[str], list[str], dict[str, dict[str, str]], dict[str, list[str]]]:
    """Read the Excel question matrix without pandas/openpyxl."""
    if not QUESTION_MATRIX_PATH.exists():
        raise FileNotFoundError(f"Missing question matrix: {QUESTION_MATRIX_PATH.name}")

    ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with ZipFile(QUESTION_MATRIX_PATH) as workbook:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in workbook.namelist():
            root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
            for item in root.findall("a:si", ns):
                shared_strings.append("".join((text.text or "") for text in item.findall(".//a:t", ns)))

        sheet = ET.fromstring(workbook.read("xl/worksheets/sheet1.xml"))
        row_values: dict[int, dict[int, str]] = {}
        max_col = 0
        for row in sheet.findall("a:sheetData/a:row", ns):
            row_number = int(row.attrib["r"])
            row_values[row_number] = {}
            for cell in row.findall("a:c", ns):
                index = col_index(cell.attrib["r"])
                row_values[row_number][index] = cell_text(cell, shared_strings, ns)
                max_col = max(max_col, index)

    table = [
        [row_values.get(row_number, {}).get(col, "") for col in range(max_col + 1)]
        for row_number in sorted(row_values)
    ]
    if len(table) < 3:
        raise ValueError("Question matrix must contain headers, questions, and disease rows.")

    disease_headers = table[0]
    question_texts = table[1]
    disease_profiles: dict[str, dict[str, str]] = {}
    question_groups: dict[str, list[str]] = {}

    for col in range(1, len(question_texts)):
        group = disease_headers[col].strip()
        question = question_texts[col].strip()
        if group and question:
            question_groups.setdefault(group, []).append(question)

    diseases: list[str] = []
    for row in table[2:]:
        disease = row[0].strip()
        if not disease or disease.lower().startswith("note"):
            continue
        diseases.append(disease)
        disease_profiles[disease] = {}
        for col in range(1, min(len(row), len(question_texts))):
            question = question_texts[col].strip()
            expected = row[col].strip()
            if question and expected:
                disease_profiles[disease][question] = expected

    return diseases, question_texts[1:], disease_profiles, question_groups


def normalize_condition(label: str) -> str:
    aliases = {
        "FU-athlete-foot": "Athlete's Foot (Tinea pedis)",
        "athlete-foot": "Athlete's Foot (Tinea pedis)",
        "athletes foot": "Athlete's Foot (Tinea pedis)",
        "Athlete's Foot / Tinea Pedis": "Athlete's Foot (Tinea pedis)",
        "FU-ringworm": "Ringworm (Tinea corporis)",
        "Tinea corporis": "Ringworm (Tinea corporis)",
        "BA- cellulitis": "Cellulitis",
        "BA-impetigo": "Impetigo",
        "Actinic_Keratosis": "Actinic Keratosis",
        "Sun_Sunlight_Damage": "Sunburn",
    }
    return aliases.get(label, label)


@st.cache_resource(show_spinner=False)
def load_ai_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError("skinsense_model.keras is missing. Train the model in Colab first, then upload it beside app.py.")
    if not CLASS_NAMES_PATH.exists():
        raise FileNotFoundError("class_names.json is missing. Download it from Colab and upload it beside app.py.")
    model = load_model(MODEL_PATH)
    class_names = json.loads(CLASS_NAMES_PATH.read_text(encoding="utf-8"))
    class_names = [normalize_condition(str(name)) for name in class_names]
    return model, class_names


def validate_image(uploaded_file) -> tuple[bytes, Image.Image]:
    if uploaded_file is None:
        raise ValueError("Please upload an image.")
    image_bytes = uploaded_file.getvalue()
    if not image_bytes:
        raise ValueError("The uploaded file is empty.")
    if len(image_bytes) > MAX_IMAGE_MB * 1024 * 1024:
        raise ValueError(f"Please upload an image under {MAX_IMAGE_MB} MB.")
    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Please upload a valid JPG or PNG image.") from exc
    return image_bytes, image


def predict_image(image: Image.Image) -> tuple[str, float, list[tuple[str, float]]]:
    model, class_names = load_ai_model()
    resized = image.resize(IMAGE_SIZE)
    array = np.asarray(resized, dtype=np.float32)
    batch = np.expand_dims(array, axis=0)
    probabilities = model.predict(batch, verbose=0)[0]

    if len(probabilities) != len(class_names):
        raise ValueError("Model output count does not match class_names.json.")

    top_indices = np.argsort(probabilities)[::-1][:3]
    top_predictions = [(class_names[index], float(probabilities[index])) for index in top_indices]
    return top_predictions[0][0], top_predictions[0][1], top_predictions


def choose_five_questions(top_predictions: list[tuple[str, float]]) -> list[str]:
    _diseases, _all_questions, _profiles, question_groups = load_question_matrix()
    selected: list[str] = []

    for condition, _confidence in top_predictions:
        for question in question_groups.get(condition, []):
            if question not in selected:
                selected.append(question)
            if len(selected) == 5:
                return selected

    for question in question_groups.get("Universal", []):
        if question not in selected:
            selected.append(question)
        if len(selected) == 5:
            return selected

    fallback = [
        "Has it been there for more than one week?",
        "Is it itchy?",
        "Is it painful?",
        "Is it getting worse?",
        "Did it start after working in seawater?",
    ]
    for question in fallback:
        if question not in selected:
            selected.append(question)
        if len(selected) == 5:
            break
    return selected


def answer_match_score(answer: str, expected: str) -> float:
    answer = answer.lower()
    expected = expected.lower()
    if answer == "i don't know":
        return 0.45
    if answer == expected:
        return 1.0
    if expected == "sometimes" and answer in {"yes", "sometimes"}:
        return 0.75
    if answer == "sometimes" and expected in {"yes", "sometimes"}:
        return 0.65
    return 0.0


def combine_image_and_questions() -> Prediction:
    image_prediction = st.session_state["image_prediction"]
    top_predictions: list[tuple[str, float]] = image_prediction["top_predictions"]
    answers: dict[str, str] = st.session_state["answers"]
    _diseases, _questions, disease_profiles, _groups = load_question_matrix()

    ranked: list[tuple[str, float, float]] = []
    for condition, image_confidence in top_predictions:
        profile = disease_profiles.get(condition, {})
        scores = []
        for question, answer in answers.items():
            expected = profile.get(question, "Sometimes")
            scores.append(answer_match_score(answer, expected))
        question_score = sum(scores) / len(scores) if scores else 0.5
        final_score = (0.72 * image_confidence) + (0.28 * question_score)
        ranked.append((condition, image_confidence, final_score))

    ranked.sort(key=lambda item: item[2], reverse=True)
    condition, image_confidence, final_score = ranked[0]
    yes_count = sum(1 for answer in answers.values() if answer == "Yes")
    sometimes_count = sum(1 for answer in answers.values() if answer == "Sometimes")
    symptom_boost = min(0.18, (yes_count * 0.04) + (sometimes_count * 0.02))

    if condition == "Cellulitis":
        urgency = "Visit a dermatologist soon"
        risk_floor = 0.68
    elif condition in {"Impetigo", "Paronychia"}:
        urgency = "See a doctor if it spreads or forms pus"
        risk_floor = 0.55
    else:
        urgency = "Monitor and care at home, but see a dermatologist if it worsens"
        risk_floor = 0.35

    risk_percentage = int(round(max(risk_floor, min(0.96, final_score + symptom_boost)) * 100))
    advice = DERM_GUIDANCE.get(condition, "See a dermatologist if symptoms spread, hurt, form pus, or do not improve.")
    prevention = PREVENTION_TIP.get(condition, "Keep the skin clean and dry, and avoid scratching.")

    return Prediction(
        condition=condition,
        image_confidence=image_confidence,
        final_score=final_score,
        risk_percentage=risk_percentage,
        top_predictions=top_predictions,
        urgency=urgency,
        advice=advice,
        prevention=prevention,
        explanation=DISEASE_INFO.get(condition, "This result is based on the image model and your answers."),
    )


def start_page() -> None:
    brand_header()
    st.title("SkinSense")
    st.markdown(f"<div class='lead-blue'>{t('tagline')}</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='body-copy'>Simple skin screening for Koli fisherwomen and fishermen exposed to seawater, sun, and wet work.</div>",
        unsafe_allow_html=True,
    )

    with st.form("start_form"):
        name = st.text_input(t("name"), max_chars=80, placeholder="Your name")
        language = st.radio(t("language"), ["मराठी", "हिंदी", "English"], horizontal=True, index=2)
        submitted = st.form_submit_button(t("continue"), type="primary", use_container_width=True)

    if submitted:
        cleaned = clean_name(name)
        if not cleaned:
            st.warning("Please enter your name.")
            return
        st.session_state["name"] = cleaned
        st.session_state["language"] = language
        if not st.session_state["name_logged_to_sheet"]:
            saved = append_name_to_sheet(cleaned)
            st.session_state["name_logged_to_sheet"] = True
            if not saved:
                st.session_state["sheet_warning"] = "SkinSense opened, but the name could not be saved to the spreadsheet."
        go("upload")

    if st.session_state.get("sheet_warning"):
        st.warning(st.session_state["sheet_warning"])
    st.markdown(f"<div class='disclaimer-box'>{t('disclaimer')}</div>", unsafe_allow_html=True)


def upload_page() -> None:
    brand_header()
    st.title(t("upload_title"))
    st.write(t("upload_help"))

    photo_tab, upload_tab = st.tabs(["Take picture", "Upload image"])
    uploaded_file = None
    with photo_tab:
        camera_file = st.camera_input("Take a clear photo")
        if camera_file is not None:
            uploaded_file = camera_file
    with upload_tab:
        gallery_file = st.file_uploader("Choose from gallery/files", type=["jpg", "jpeg", "png"], accept_multiple_files=False)
        if gallery_file is not None:
            uploaded_file = gallery_file

    if uploaded_file is not None:
        try:
            image_bytes, image = validate_image(uploaded_file)
        except ValueError as exc:
            st.warning(str(exc))
            return

        st.session_state["image_bytes"] = image_bytes
        st.session_state["image_name"] = uploaded_file.name
        st.image(image_bytes, caption=uploaded_file.name, use_container_width=True)

        if st.button("Analyze image", type="primary", use_container_width=True):
            try:
                with st.spinner("Checking image..."):
                    condition, confidence, top_predictions = predict_image(image)
                st.session_state["image_prediction"] = {
                    "condition": condition,
                    "confidence": confidence,
                    "top_predictions": top_predictions,
                }
                st.session_state["question_list"] = choose_five_questions(top_predictions)
                st.session_state["answers"] = {}
                go("questions")
            except Exception as exc:
                st.error(str(exc))
                st.info("If this says the model is missing, train in Colab and upload `skinsense_model.keras` and `class_names.json` beside app.py.")

    if st.button("Back", use_container_width=True):
        go("start")


def questions_page() -> None:
    if not st.session_state.get("image_prediction"):
        go("upload")

    brand_header()
    st.title(t("questions_title"))
    st.write("These questions help narrow the top image matches.")

    with st.form("questions_form"):
        answers: dict[str, str] = {}
        for index, question in enumerate(st.session_state["question_list"], start=1):
            answers[question] = st.radio(f"Q{index}. {question}", ANSWER_OPTIONS, horizontal=True, index=None)
        submitted = st.form_submit_button("See result", type="primary", use_container_width=True)

    if submitted:
        if any(answer is None for answer in answers.values()):
            st.warning("Please answer all 5 questions.")
            return
        st.session_state["answers"] = answers
        st.session_state["final_prediction"] = combine_image_and_questions()
        go("result")

    if st.button("Back to upload", use_container_width=True):
        go("upload")


def result_page() -> None:
    prediction: Prediction | None = st.session_state.get("final_prediction")
    if prediction is None:
        go("questions")

    brand_header()
    st.title(t("result_title"))
    if st.session_state.get("image_bytes"):
        st.image(st.session_state["image_bytes"], caption=st.session_state.get("image_name", "Uploaded image"), use_container_width=True)

    st.markdown(
        f"""
        <div class="result-panel">
            <div class="result-kicker">Predicted disease</div>
            <div class="result-disease">{escape(prediction.condition)}</div>
            <p>{escape(prediction.explanation)}</p>
        </div>
        <div class="result-panel">
            <div class="result-kicker">Risk percentage</div>
            <div class="risk-big">{prediction.risk_percentage}%</div>
        </div>
        <h3>What you can do</h3>
        <div class="soft-green">{escape(prediction.prevention)}</div>
        <h3>When to see a dermatologist</h3>
        <div class="soft-yellow">{escape(prediction.advice)}</div>
        <div class="disclaimer-box">{escape(t("disclaimer"))}</div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Check another image", type="primary", use_container_width=True):
            st.session_state["image_bytes"] = None
            st.session_state["image_prediction"] = None
            st.session_state["final_prediction"] = None
            go("upload")
    with col2:
        if st.button("Start over", use_container_width=True):
            st.session_state.clear()
            st.rerun()


def main() -> None:
    init_state()
    css()
    page = st.session_state.get("page", "start")
    if page not in VALID_PAGES:
        page = "start"

    if page == "start":
        start_page()
    elif page == "upload":
        upload_page()
    elif page == "questions":
        questions_page()
    elif page == "result":
        result_page()


if __name__ == "__main__":
    main()
