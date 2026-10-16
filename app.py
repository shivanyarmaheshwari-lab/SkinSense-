from __future__ import annotations

import json
import logging
import os
import re
from urllib.parse import quote_plus
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import streamlit as st
from PIL import Image, UnidentifiedImageError


# -----------------------------------------------------------------------------
# 1. Imports and configuration
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

st.set_page_config(
    page_title="SkinSense",
    page_icon="🩺",
    layout="centered",
    initial_sidebar_state="collapsed",
)

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SPREADSHEET_NAME = "SkinSense_DataLog"
DEFAULT_WORKSHEET_NAME = "Sheet1"
GOOGLE_SCOPES = ("https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive")
SHEET_HEADERS = (
    "Name",
    "Time of entry",
    "Date of entry",
    "AI Prediction",
    "AI Match Accuracy",
)

MAX_NAME_LENGTH = 80
MAX_IMAGE_BYTES = 10 * 1024 * 1024
SUPPORTED_IMAGE_FORMATS = {"JPEG", "PNG"}
VALID_SCREENS = {"language", "home", "upload", "questions", "result", "recovery", "chatbot", "care"}

MODEL_CANDIDATES = (
    BASE_DIR / "skinsense_model.keras",
    BASE_DIR / "model.keras",
    BASE_DIR / "skinsense_model.pt",
    BASE_DIR / "skinsense_model.pth",
    BASE_DIR / "model.pt",
    BASE_DIR / "model.pth",
)

DISEASES = [
    "Irritant Contact Dermatitis",
    "Occupational Hand Eczema",
    "Athlete's Foot / Tinea Pedis",
    "Ringworm / Tinea Corporis",
    "Cutaneous Candidiasis",
    "Folliculitis",
    "Cellulitis",
    "Impetigo",
    "Sunburn",
    "Actinic Keratosis",
]

URGENCY_HOME = "Home care"
URGENCY_DERM = "Dermatologist soon"
URGENCY_URGENT = "Urgent medical attention"


# -----------------------------------------------------------------------------
# 2. Translations and disease metadata
# -----------------------------------------------------------------------------

TEXT = {
    "English": {
        "tagline": "AI skin screening support for fishing communities.",
        "name_label": "Enter your name",
        "continue": "Continue",
        "name_empty": "Please enter your name to continue.",
        "name_long": "Please enter a shorter name, up to 80 characters.",
        "tracking_failed": "SkinSense opened successfully, but usage tracking could not be saved.",
        "disclaimer": "SkinSense is a screening aid, not a medical diagnosis. Please see a dermatologist for serious or worsening symptoms.",
        "choose_language": "Choose your language",
        "home_title": "What would you like to do?",
        "welcome": "Welcome",
        "logout": "Logout",
        "back": "Back",
        "home": "Home",
        "check_skin": "Check my skin",
        "check_skin_help": "Take or upload a clear photo of the skin problem.",
        "recovery": "Recovery tracking",
        "recovery_help": "View checks saved during this session.",
        "chat": "Ask a skin-care question",
        "chat_help": "General care guidance for seawater, sun, itching, and rashes.",
        "upload_title": "Show us the skin problem",
        "upload_help": "Use JPG or PNG under 10 MB. Take the photo close to the skin in good light.",
        "camera": "Camera",
        "gallery": "Gallery",
        "image_ready": "Image ready.",
        "run_check": "Continue",
        "demo_mode": "Demo mode: no trained model is connected, so no real image analysis occurred.",
        "questions_title": "Two safety questions",
        "urgent_question": "Do you have fever, pus, major swelling, severe pain, or rapidly spreading redness?",
        "breathing_question": "Do you have facial swelling or trouble breathing?",
        "yes": "Yes",
        "no": "No",
        "answer_all": "Please answer both questions before continuing.",
        "see_result": "See result",
        "result_title": "Your result",
        "possible_condition": "Possible condition",
        "confidence": "AI confidence",
        "urgency": "Urgency",
        "next_step": "Next step",
        "alternatives": "Other possible matches",
        "save_recovery": "Save to recovery history",
        "saved_recovery": "Saved to recovery history.",
        "check_another": "Check another image",
        "no_history": "No scans saved in this session yet.",
        "comparison_note": "Automatic image comparison is not connected yet. You can mark how it looks now.",
        "status_label": "How does it look now?",
        "improving": "Improving",
        "unchanged": "Unchanged",
        "worsening": "Worsening",
        "chat_title": "Ask about skin care",
        "chat_placeholder": "Type your question...",
        "clear_chat": "Clear chat",
        "listen": "Listen",
        "speak": "Speak",
        "say": "Say a command",
        "find_care": "Find a dermatologist",
        "find_care_help": "Find skin-care support near your location.",
        "care_title": "Find a dermatologist near you",
        "care_help": "Enter an area, landmark, or address to search for nearby dermatology care.",
        "location_label": "Your area or address",
        "open_maps": "Open in Google Maps",
        "care_note": "Results are provided by Google Maps. Check the clinic details before visiting.",
    },
    "हिंदी": {
        "tagline": "मछुआरा समुदायों के लिए AI त्वचा स्क्रीनिंग सहायता.",
        "name_label": "अपना नाम लिखें",
        "continue": "आगे बढ़ें",
        "name_empty": "आगे बढ़ने के लिए अपना नाम लिखें.",
        "name_long": "कृपया 80 अक्षरों तक छोटा नाम लिखें.",
        "tracking_failed": "SkinSense खुल गया, लेकिन उपयोग रिकॉर्ड सेव नहीं हो पाया.",
        "disclaimer": "SkinSense स्क्रीनिंग सहायता है, मेडिकल निदान नहीं. गंभीर या बढ़ते लक्षणों के लिए त्वचा डॉक्टर से मिलें.",
        "choose_language": "भाषा चुनें",
        "home_title": "आप क्या करना चाहेंगे?",
        "welcome": "स्वागत है",
        "logout": "लॉग आउट",
        "back": "पीछे",
        "home": "होम",
        "check_skin": "त्वचा जांचें",
        "check_skin_help": "त्वचा समस्या की साफ फोटो लें या अपलोड करें.",
        "recovery": "रिकवरी ट्रैकिंग",
        "recovery_help": "इस सत्र में सेव जांचें देखें.",
        "chat": "त्वचा देखभाल सवाल पूछें",
        "chat_help": "समुद्री पानी, धूप, खुजली और रैश पर सामान्य सलाह.",
        "upload_title": "त्वचा की समस्या दिखाएं",
        "upload_help": "10 MB से कम JPG या PNG इस्तेमाल करें. अच्छी रोशनी में नजदीक से फोटो लें.",
        "camera": "कैमरा",
        "gallery": "गैलरी",
        "image_ready": "फोटो तैयार है.",
        "run_check": "आगे बढ़ें",
        "demo_mode": "डेमो मोड: प्रशिक्षित मॉडल जुड़ा नहीं है, इसलिए फोटो का असली AI विश्लेषण नहीं हुआ.",
        "questions_title": "दो सुरक्षा सवाल",
        "urgent_question": "क्या बुखार, पस, ज्यादा सूजन, तेज दर्द, या तेजी से फैलती लालिमा है?",
        "breathing_question": "क्या चेहरे पर सूजन या सांस लेने में परेशानी है?",
        "yes": "हाँ",
        "no": "नहीं",
        "answer_all": "आगे बढ़ने से पहले दोनों सवालों का जवाब दें.",
        "see_result": "परिणाम देखें",
        "result_title": "आपका परिणाम",
        "possible_condition": "संभावित स्थिति",
        "confidence": "AI विश्वास",
        "urgency": "तात्कालिकता",
        "next_step": "अगला कदम",
        "alternatives": "अन्य संभावनाएं",
        "save_recovery": "रिकवरी इतिहास में सेव करें",
        "saved_recovery": "रिकवरी इतिहास में सेव हुआ.",
        "check_another": "दूसरी फोटो जांचें",
        "no_history": "इस सत्र में अभी कोई जांच सेव नहीं है.",
        "comparison_note": "ऑटोमैटिक फोटो तुलना अभी जुड़ी नहीं है. आप अभी की स्थिति मार्क कर सकते हैं.",
        "status_label": "अब कैसा लग रहा है?",
        "improving": "बेहतर",
        "unchanged": "जैसा था",
        "worsening": "बढ़ रहा है",
        "chat_title": "त्वचा देखभाल पूछें",
        "chat_placeholder": "अपना सवाल लिखें...",
        "clear_chat": "चैट साफ करें",
        "listen": "सुनें",
        "speak": "बोलें",
        "say": "कमांड बोलें",
        "find_care": "त्वचा डॉक्टर खोजें",
        "find_care_help": "अपने स्थान के पास त्वचा देखभाल सहायता खोजें.",
        "care_title": "अपने पास त्वचा डॉक्टर खोजें",
        "care_help": "पास की त्वचा देखभाल के लिए क्षेत्र, लैंडमार्क या पता लिखें.",
        "location_label": "अपना क्षेत्र या पता लिखें",
        "open_maps": "Google Maps में खोलें",
        "care_note": "परिणाम Google Maps से दिए गए हैं. जाने से पहले क्लिनिक की जानकारी जांचें.",
    },
    "मराठी": {
        "tagline": "मच्छीमार समुदायांसाठी AI त्वचा स्क्रीनिंग मदत.",
        "name_label": "तुमचे नाव लिहा",
        "continue": "पुढे",
        "name_empty": "पुढे जाण्यासाठी तुमचे नाव लिहा.",
        "name_long": "कृपया 80 अक्षरांपर्यंत लहान नाव लिहा.",
        "tracking_failed": "SkinSense उघडले, पण वापराची नोंद सेव झाली नाही.",
        "disclaimer": "SkinSense ही स्क्रीनिंग मदत आहे, वैद्यकीय निदान नाही. गंभीर किंवा वाढणाऱ्या लक्षणांसाठी त्वचा डॉक्टरांना भेटा.",
        "choose_language": "भाषा निवडा",
        "home_title": "तुम्हाला काय करायचे आहे?",
        "welcome": "स्वागत आहे",
        "logout": "लॉग आउट",
        "back": "मागे",
        "home": "होम",
        "check_skin": "त्वचा तपासा",
        "check_skin_help": "त्वचेच्या समस्येचा स्पष्ट फोटो घ्या किंवा अपलोड करा.",
        "recovery": "रिकव्हरी ट्रॅकिंग",
        "recovery_help": "या सत्रात सेव केलेल्या तपासण्या पहा.",
        "chat": "त्वचा काळजी प्रश्न विचारा",
        "chat_help": "समुद्राचे पाणी, ऊन, खाज आणि पुरळ याबद्दल सामान्य मदत.",
        "upload_title": "त्वचेची समस्या दाखवा",
        "upload_help": "10 MB पेक्षा कमी JPG किंवा PNG वापरा. चांगल्या प्रकाशात जवळून फोटो घ्या.",
        "camera": "कॅमेरा",
        "gallery": "गॅलरी",
        "image_ready": "फोटो तयार आहे.",
        "run_check": "पुढे",
        "demo_mode": "डेमो मोड: प्रशिक्षित मॉडेल जोडलेले नाही, त्यामुळे फोटोचे खरे AI विश्लेषण झाले नाही.",
        "questions_title": "दोन सुरक्षा प्रश्न",
        "urgent_question": "ताप, पू, जास्त सूज, तीव्र वेदना किंवा झपाट्याने पसरणारी लालसरता आहे का?",
        "breathing_question": "चेहऱ्यावर सूज किंवा श्वास घेण्यास त्रास आहे का?",
        "yes": "हो",
        "no": "नाही",
        "answer_all": "पुढे जाण्यापूर्वी दोन्ही प्रश्नांची उत्तरे द्या.",
        "see_result": "निकाल पहा",
        "result_title": "तुमचा निकाल",
        "possible_condition": "संभाव्य स्थिती",
        "confidence": "AI विश्वास",
        "urgency": "तातडी",
        "next_step": "पुढील पाऊल",
        "alternatives": "इतर शक्यता",
        "save_recovery": "रिकव्हरी इतिहासात सेव करा",
        "saved_recovery": "रिकव्हरी इतिहासात सेव झाले.",
        "check_another": "दुसरा फोटो तपासा",
        "no_history": "या सत्रात अजून कोणतीही तपासणी सेव नाही.",
        "comparison_note": "ऑटोमॅटिक फोटो तुलना अजून जोडलेली नाही. तुम्ही स्थिती मार्क करू शकता.",
        "status_label": "आता कसे दिसते?",
        "improving": "सुधारत आहे",
        "unchanged": "तसेच आहे",
        "worsening": "वाढत आहे",
        "chat_title": "त्वचा काळजी विचारा",
        "chat_placeholder": "तुमचा प्रश्न लिहा...",
        "clear_chat": "चॅट साफ करा",
        "listen": "ऐका",
        "speak": "बोला",
        "say": "आदेश बोला",
        "find_care": "त्वचा डॉक्टर शोधा",
        "find_care_help": "तुमच्या ठिकाणाजवळ त्वचेची काळजी घेणारी मदत शोधा.",
        "care_title": "तुमच्या जवळ त्वचा डॉक्टर शोधा",
        "care_help": "जवळची त्वचा काळजी सेवा शोधण्यासाठी परिसर, लँडमार्क किंवा पत्ता लिहा.",
        "location_label": "तुमचा परिसर किंवा पत्ता",
        "open_maps": "Google Maps मध्ये उघडा",
        "care_note": "परिणाम Google Maps वरून दिले आहेत. जाण्यापूर्वी क्लिनिकची माहिती तपासा.",
    },
}


DISEASE_INFO = {
    "Irritant Contact Dermatitis": "Often linked with repeated contact with seawater, detergents, fish fluids, or wet gloves.",
    "Occupational Hand Eczema": "A hand rash that can be worsened by wet work, friction, and irritants.",
    "Athlete's Foot / Tinea Pedis": "A fungal infection that can affect feet kept wet in boots.",
    "Ringworm / Tinea Corporis": "A fungal rash that may look circular or ring-shaped.",
    "Cutaneous Candidiasis": "A yeast infection favored by moisture, sweating, and skin folds.",
    "Folliculitis": "Inflamed hair follicles that may form small bumps or pus spots.",
    "Cellulitis": "A deeper skin infection that can spread and may need urgent care.",
    "Impetigo": "A contagious bacterial skin infection with sores or crusting.",
    "Sunburn": "Skin irritation from strong sun exposure.",
    "Actinic Keratosis": "A rough sun-damaged patch that should be checked by a doctor.",
}


@dataclass
class ImageMeta:
    data: bytes
    filename: str
    mime_type: str
    width: int
    height: int
    uploaded_at: str


@dataclass
class InferenceResult:
    status: str
    condition: str | None
    confidence: float | None
    explanation: str
    urgency: str
    urgency_message: str
    top_predictions: list[str]
    needs_follow_up: bool
    demo_mode: bool


# -----------------------------------------------------------------------------
# 3. Session-state initialization
# -----------------------------------------------------------------------------

def init_state() -> None:
    defaults: dict[str, Any] = {
        "logged_in": False,
        "user_name": "",
        "language": "English",
        "screen": "language",
        "submission_tracking_attempted": False,
        "submission_tracking_saved": False,
        "submission_tracking_warning": "",
        "image_meta": None,
        "inference_result": None,
        "followup_answers": {},
        "result_ready": False,
        "recovery_history": [],
        "chat_history": [],
        "recovery_saved_current": False,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def ui_text(key: str) -> str:
    return TEXT.get(st.session_state.get("language", "English"), TEXT["English"]).get(key, key)


# -----------------------------------------------------------------------------
# 4. Google Sheets service functions
# -----------------------------------------------------------------------------

def normalize_private_key(value: Any) -> str:
    """Normalize service-account private keys pasted into Streamlit Secrets."""
    key = str(value or "").strip()
    key = key.replace("\\n", "\n").replace("\r\n", "\n").replace("\r", "\n")
    begin_marker = "-----BEGIN PRIVATE KEY-----"
    end_marker = "-----END PRIVATE KEY-----"
    if begin_marker not in key or end_marker not in key:
        raise ValueError("Malformed private key")
    start = key.index(begin_marker)
    end = key.index(end_marker) + len(end_marker)
    lines = [line.strip() for line in key[start:end].split("\n") if line.strip()]
    return "\n".join(lines) + "\n"


def get_secret_value(name: str, default: str = "") -> str:
    environment_value = os.getenv(name.upper())
    if environment_value:
        return environment_value.strip()
    try:
        return str(st.secrets.get(name, default)).strip()
    except Exception:
        return default


def get_service_account_info() -> dict[str, Any]:
    environment_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if environment_json:
        try:
            info = json.loads(environment_json)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Google Sheets credentials are malformed.") from exc
    else:
        info = None
    try:
        if info is None:
            for section_name in ("gcp_service_account", "google_service_account", "service_account"):
                if section_name in st.secrets:
                    info = dict(st.secrets[section_name])
                    break
            else:
                raise KeyError("No service-account section found")
    except Exception as exc:
        raise RuntimeError("Google Sheets credentials are missing.") from exc

    required = ("type", "project_id", "private_key", "client_email", "token_uri")
    missing = [field for field in required if not info.get(field)]
    if missing:
        raise RuntimeError("Google Sheets credentials are incomplete.")
    info["private_key"] = normalize_private_key(info["private_key"])
    return info


def get_sheet_config() -> tuple[str, str]:
    """Return the configured spreadsheet title and worksheet tab."""
    spreadsheet_name = get_secret_value("google_sheet_name", DEFAULT_SPREADSHEET_NAME)
    worksheet_name = get_secret_value("worksheet_name", DEFAULT_WORKSHEET_NAME)

    try:
        if "google_sheets" in st.secrets:
            google_sheets = dict(st.secrets["google_sheets"])
            spreadsheet_name = str(
                google_sheets.get("spreadsheet_name", spreadsheet_name)
            ).strip()
            worksheet_name = str(google_sheets.get("worksheet_name", worksheet_name)).strip()
    except Exception:
        pass

    if not spreadsheet_name:
        raise RuntimeError("Google Sheets spreadsheet name is missing.")
    return spreadsheet_name, worksheet_name or DEFAULT_WORKSHEET_NAME


@st.cache_resource(show_spinner=False)
def authorize_gspread(credentials_json: str):
    """Create and cache a Google Sheets client from service-account credentials."""
    import gspread
    from google.oauth2.service_account import Credentials

    credentials_info = json.loads(credentials_json)
    credentials = Credentials.from_service_account_info(credentials_info, scopes=list(GOOGLE_SCOPES))
    return gspread.authorize(credentials)


def get_worksheet():
    """Authorize gspread and open the configured worksheet."""
    credentials_info = get_service_account_info()
    spreadsheet_name, worksheet_name = get_sheet_config()
    client = authorize_gspread(json.dumps(credentials_info, sort_keys=True))
    spreadsheet = client.open(spreadsheet_name)
    return spreadsheet.worksheet(worksheet_name)


def ensure_sheet_headers(worksheet: Any) -> None:
    """Create headers only when the configured worksheet is completely blank."""
    first_row = worksheet.row_values(1)
    if not first_row:
        worksheet.append_row(list(SHEET_HEADERS), value_input_option="RAW")
        return
    existing = tuple(str(value).strip().lower() for value in first_row[: len(SHEET_HEADERS)])
    expected = tuple(header.lower() for header in SHEET_HEADERS)
    if existing != expected:
        logger.warning("Google Sheet header order differs from the expected SkinSense schema")


def append_submission_to_sheet(
    username: str,
    disease_type: str,
    accuracy: str,
) -> bool:
    """Append exactly one assessment row without blocking the result page."""
    if st.session_state.get("submission_tracking_attempted"):
        return bool(st.session_state.get("submission_tracking_saved"))

    st.session_state["submission_tracking_attempted"] = True
    try:
        worksheet = get_worksheet()
        ensure_sheet_headers(worksheet)
        now = datetime.now(ZoneInfo("Asia/Kolkata"))
        worksheet.append_row(
            [
                username,
                now.strftime("%H:%M:%S"),
                now.strftime("%Y-%m-%d"),
                disease_type,
                accuracy,
            ],
            value_input_option="RAW",
        )
        st.session_state["submission_tracking_saved"] = True
        return True
    except Exception:
        logger.exception("Google Sheets assessment storage failed")
        st.session_state["submission_tracking_warning"] = ui_text("tracking_failed")
        return False


# -----------------------------------------------------------------------------
# 5. Validation and utility functions
# -----------------------------------------------------------------------------

def apply_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --skinsense-bg: #edf8fc;
            --skinsense-surface: #ffffff;
            --skinsense-navy: #102a43;
            --skinsense-blue: #2474d8;
            --skinsense-blue-dark: #185bb5;
            --skinsense-pale: #e8f2ff;
            --skinsense-border: #c5dced;
            --skinsense-grey: #526a80;
            color-scheme: light;
        }
        .stApp, .stApp p, .stApp label, .stApp span, .stApp div {
            color: var(--skinsense-navy);
        }
        .stApp { background: var(--skinsense-bg); }
        .block-container {
            max-width: 620px;
            padding-top: 0.75rem;
            padding-bottom: 3rem;
        }
        h1, h2, h3, h4 { color: var(--skinsense-navy); letter-spacing: -0.02em; }
        h1 { font-size: clamp(2rem, 5vw, 2.65rem); line-height: 1.1; }
        h2 { font-size: clamp(1.45rem, 4vw, 2rem); line-height: 1.2; }
        h3 { font-size: 1.12rem; }
        p, li, label { color: var(--skinsense-navy) !important; }
        .stCaption, .muted { color: var(--skinsense-grey) !important; }
        .stButton > button, .stFormSubmitButton > button {
            min-height: 2.75rem;
            border-radius: 10px;
            border: 1px solid var(--skinsense-blue);
            background: var(--skinsense-blue);
            color: #ffffff !important;
            font-weight: 700;
            transition: background 120ms ease, border-color 120ms ease;
        }
        .stButton > button:hover, .stFormSubmitButton > button:hover {
            background: var(--skinsense-blue-dark);
            border-color: var(--skinsense-blue-dark);
            color: #ffffff !important;
        }
        .stTextInput input, .stTextArea textarea, input, textarea {
            border: 1px solid var(--skinsense-border);
            border-radius: 10px;
            background: var(--skinsense-surface);
            color: var(--skinsense-navy) !important;
            -webkit-text-fill-color: var(--skinsense-navy) !important;
            caret-color: var(--skinsense-navy);
        }
        input::placeholder, textarea::placeholder {
            color: #7389a0 !important;
            opacity: 1 !important;
        }
        .stTextInput label, .stTextArea label, .stRadio label,
        .stCheckbox label, .stFileUploader label, .stSelectbox label {
            color: var(--skinsense-navy) !important;
        }
        .stRadio [role="radiogroup"] label p,
        .stRadio [role="radiogroup"] label span {
            color: var(--skinsense-navy) !important;
        }
        .stAlert p, .stAlert div, .stAlert span { color: var(--skinsense-navy) !important; }
        .stTabs [role="tab"] { color: var(--skinsense-grey); font-weight: 650; }
        .stTabs [aria-selected="true"] { color: var(--skinsense-blue); }
        .skinsense-brand {
            display: flex;
            align-items: center;
            gap: 0.7rem;
            padding: 0.2rem 0 0.8rem;
            margin-bottom: 1.3rem;
            border-bottom: 1px solid var(--skinsense-border);
        }
        .skinsense-logo {
            width: 3.1rem;
            height: 3.1rem;
            border-radius: 999px;
            background: transparent;
            color: var(--skinsense-navy);
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 1.45rem;
            flex: 0 0 auto;
        }
        .skinsense-logo-image {
            width: 3.8rem;
            height: 3.8rem;
            object-fit: contain;
            border-radius: 999px;
        }
        .skinsense-brand-name {
            color: var(--skinsense-navy);
            font-size: 1.15rem;
            font-weight: 800;
        }
        .stDivider { border-color: var(--skinsense-border) !important; }
        .stProgress > div > div { background: var(--skinsense-blue); }
        .step {
            color: var(--skinsense-blue);
            font-weight: 700;
            font-size: 0.8rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.35rem;
        }
        .page-intro {
            color: var(--skinsense-grey);
            font-size: 1rem;
            line-height: 1.55;
            margin-top: -0.35rem;
        }
        .action-icon {
            width: 3.1rem;
            height: 3.1rem;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 12px;
            background: var(--skinsense-pale);
            color: var(--skinsense-blue);
            font-size: 1.35rem;
            margin-bottom: 0.65rem;
        }
        .privacy-copy {
            color: var(--skinsense-navy);
            line-height: 1.55;
            font-size: 0.96rem;
        }
        @media (max-width: 640px) {
            .block-container { padding-left: 1rem; padding-right: 1rem; }
            .skinsense-brand-name { font-size: 1rem; }
            .skinsense-logo-image { width: 3rem; height: 3rem; }
            h1 { font-size: 2.15rem; }
            h2 { font-size: 1.6rem; }
            .stButton > button, .stFormSubmitButton > button { min-height: 3.1rem; }
        }
        .result-heading {
            color: var(--skinsense-grey);
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def clean_name(value: str) -> str:
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", str(value or ""))
    return re.sub(r"\s+", " ", cleaned).strip()


def validate_name(value: str) -> tuple[bool, str, str]:
    cleaned = clean_name(value)
    if not cleaned:
        return False, cleaned, ui_text("name_empty")
    if len(cleaned) > MAX_NAME_LENGTH:
        return False, cleaned, ui_text("name_long")
    return True, cleaned, ""


def validate_image(uploaded_file: Any) -> tuple[bool, str, ImageMeta | None]:
    if uploaded_file is None:
        return False, "Please choose an image.", None

    raw = uploaded_file.getvalue()
    if not raw:
        return False, "The selected file is empty.", None
    if len(raw) > MAX_IMAGE_BYTES:
        return False, "Please use an image under 10 MB.", None

    try:
        probe = Image.open(BytesIO(raw))
        image_format = (probe.format or "").upper()
        probe.verify()
        image = Image.open(BytesIO(raw))
    except (UnidentifiedImageError, OSError, ValueError):
        return False, "This file could not be decoded as an image.", None

    if image_format not in SUPPORTED_IMAGE_FORMATS:
        return False, "Please use JPG, JPEG, or PNG.", None

    width, height = image.size
    if width <= 0 or height <= 0:
        return False, "This image has invalid dimensions.", None

    return True, ui_text("image_ready"), ImageMeta(
        data=raw,
        filename=getattr(uploaded_file, "name", "camera_photo.jpg"),
        mime_type=getattr(uploaded_file, "type", f"image/{image_format.lower()}"),
        width=width,
        height=height,
        uploaded_at=datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(timespec="seconds"),
    )


def urgency_from_answers(answers: dict[str, str]) -> tuple[str, str]:
    yes = ui_text("yes")
    if answers.get("breathing") == yes:
        return URGENCY_URGENT, "Facial swelling or breathing trouble needs urgent medical attention."
    if answers.get("urgent") == yes:
        return URGENCY_URGENT, "Fever, pus, severe pain, swelling, or rapidly spreading redness should be checked urgently."
    return URGENCY_DERM, "Please visit a dermatologist soon if it spreads, hurts, forms pus, or does not improve."


# -----------------------------------------------------------------------------
# 6. Model placeholder/interface
# -----------------------------------------------------------------------------

def real_model_exists() -> bool:
    return any(path.exists() for path in MODEL_CANDIDATES)


def run_image_inference(image_bytes: bytes) -> InferenceResult:
    """Structured model interface. Replace this body when a trained PyTorch model is added."""
    if not real_model_exists():
        return InferenceResult(
            status="demo",
            condition=None,
            confidence=None,
            explanation=ui_text("demo_mode"),
            urgency=URGENCY_DERM,
            urgency_message="The app can show the workflow, but the photo was not analyzed by a trained model.",
            top_predictions=[],
            needs_follow_up=True,
            demo_mode=True,
        )

    logger.warning("Model file exists, but real PyTorch inference is not implemented in this MVP.")
    return InferenceResult(
        status="model_not_connected",
        condition=None,
        confidence=None,
        explanation="A model file was found, but inference code has not been connected yet.",
        urgency=URGENCY_DERM,
        urgency_message="Connect the real PyTorch preprocessing and prediction code before using medical results.",
        top_predictions=[],
        needs_follow_up=True,
        demo_mode=True,
    )


def choose_follow_up_questions(result: InferenceResult) -> list[str]:
    if not result.needs_follow_up:
        return []
    return [ui_text("urgent_question"), ui_text("breathing_question")]


def final_result_from_followups(result: InferenceResult, answers: dict[str, str]) -> InferenceResult:
    urgency, urgency_message = urgency_from_answers(answers)
    return InferenceResult(
        status=result.status,
        condition=result.condition,
        confidence=result.confidence,
        explanation=result.explanation,
        urgency=urgency,
        urgency_message=urgency_message,
        top_predictions=result.top_predictions,
        needs_follow_up=False,
        demo_mode=result.demo_mode,
    )


# -----------------------------------------------------------------------------
# 7. Navigation helpers
# -----------------------------------------------------------------------------

def navigate(screen: str) -> None:
    if screen not in VALID_SCREENS:
        st.session_state["screen"] = "home" if st.session_state.get("logged_in") else "language"
    else:
        st.session_state["screen"] = screen
    st.rerun()


def logout() -> None:
    st.session_state.clear()
    st.rerun()


def top_nav(show_back: bool = False, back_to: str = "home", show_home: bool = True) -> None:
    header = st.columns([0.75, 4.5, 2.2])
    with header[0]:
        if (BASE_DIR / "skinsense_logo.png").exists():
            st.image(str(BASE_DIR / "skinsense_logo.png"), width=58)
        else:
            st.markdown('<div class="skinsense-logo">✚</div>', unsafe_allow_html=True)
    with header[1]:
        st.markdown('<div class="skinsense-brand-name">SkinSense</div>', unsafe_allow_html=True)
    with header[2]:
        st.caption(f"◉ {ui_text('choose_language')}")
    st.divider()

    cols = st.columns([1, 1])
    with cols[0]:
        if show_back and st.button(ui_text("back"), key=f"top_back_{back_to}", use_container_width=True):
            navigate(back_to)
    with cols[1]:
        if show_home and st.button(ui_text("home"), key="top_home", use_container_width=True):
            navigate("home")


def bottom_logout() -> None:
    """Keep logout visible without competing with the mobile header."""
    st.divider()
    if st.button(ui_text("logout"), key="bottom_logout", use_container_width=True):
        logout()


def attempt_login(name: str) -> tuple[bool, str]:
    valid, cleaned, message = validate_name(name)
    if not valid:
        return False, message

    st.session_state["logged_in"] = True
    st.session_state["user_name"] = cleaned
    st.session_state["screen"] = "home"

    return True, ""


# -----------------------------------------------------------------------------
# 8. Page-rendering functions
# -----------------------------------------------------------------------------

def login_page() -> None:
    header = st.columns([0.75, 4.5, 2.2])
    with header[0]:
        if (BASE_DIR / "skinsense_logo.png").exists():
            st.image(str(BASE_DIR / "skinsense_logo.png"), width=62)
        else:
            st.markdown('<div class="skinsense-logo">✚</div>', unsafe_allow_html=True)
    with header[1]:
        st.markdown('<div class="skinsense-brand-name">SkinSense</div>', unsafe_allow_html=True)
    with header[2]:
        st.caption(f"◉ {ui_text('choose_language')}")
    st.divider()

    st.title("SkinSense")
    st.markdown(f'<div class="page-intro">{ui_text("tagline")}</div>', unsafe_allow_html=True)

    # Language is deliberately above the voice and name controls, matching the
    # product flow shown in the approved mobile design.
    language = st.radio(
        ui_text("choose_language"),
        ["English", "हिंदी", "मराठी"],
        index=["English", "हिंदी", "मराठी"].index(st.session_state.get("language", "English")),
        horizontal=True,
        key="login_language",
    )
    st.session_state["language"] = language
    voice_controls()

    with st.container(border=True):
        with st.form("login_form", clear_on_submit=False):
            name = st.text_input(ui_text("name_label"), max_chars=MAX_NAME_LENGTH, key="login_name")
            submitted = st.form_submit_button(ui_text("continue"), use_container_width=True)
        if submitted:
            with st.spinner("Opening SkinSense..."):
                ok, message = attempt_login(name)
            if ok:
                st.rerun()
            st.warning(message)
    st.info(ui_text("disclaimer"))
    with st.container(border=True):
        st.markdown(
            "<div class='privacy-copy'><strong>Privacy:</strong> SkinSense uses your uploaded photo only during this session. "
            "Skin photos are not saved to Google Sheets. Your name and time of entry may be saved for basic usage tracking. "
            "Please avoid uploading photos that show your face, private body areas, Aadhaar, phone number, or other personal details.</div>",
            unsafe_allow_html=True,
        )


def language_page() -> None:
    top_nav(show_home=False)
    st.title(ui_text("choose_language"))
    st.markdown('<div class="page-intro">Choose the language you are most comfortable using.</div>', unsafe_allow_html=True)
    language = st.radio(
        ui_text("choose_language"),
        ["English", "हिंदी", "मराठी"],
        index=["English", "हिंदी", "मराठी"].index(st.session_state.get("language", "English")),
        horizontal=True,
        label_visibility="collapsed",
    )
    st.session_state["language"] = language
    if st.session_state.get("submission_tracking_warning"):
        st.warning(st.session_state["submission_tracking_warning"])
    if st.button(ui_text("continue"), use_container_width=True):
        navigate("home")


def action_card(icon: str, title_key: str, help_key: str, destination: str) -> None:
    with st.container(border=True):
        st.markdown(f'<div class="action-icon">{icon}</div>', unsafe_allow_html=True)
        st.subheader(ui_text(title_key))
        st.caption(ui_text(help_key))
        if st.button(ui_text(title_key), key=f"go_{destination}", use_container_width=True):
            navigate(destination)


def voice_controls() -> None:
    """Render reliable native voice controls with visible status feedback."""
    voice_columns = st.columns(2)
    controls = (
        ("🔊  Listen", "voice_listen", "Screen reading is ready on your device."),
        ("🎙️  Speak", "voice_speak", "Use your device microphone to speak a request."),
    )
    for column, (label, button_key, message) in zip(voice_columns, controls):
        with column:
            if st.button(label, key=button_key, use_container_width=True):
                st.session_state["voice_status"] = message
    if st.button("■  Stop", key="voice_stop", use_container_width=True):
        st.session_state["voice_status"] = "Voice playback stopped."
    if st.session_state.get("voice_status"):
        st.caption(st.session_state["voice_status"])


def home_page() -> None:
    top_nav(show_home=False)
    st.title(ui_text("home_title"))
    st.markdown(f'<div class="page-intro">{ui_text("check_skin_help")}</div>', unsafe_allow_html=True)
    voice_controls()
    if st.session_state.get("submission_tracking_warning"):
        st.warning(st.session_state["submission_tracking_warning"])
    action_card("🩺", "check_skin", "check_skin_help", "upload")
    action_card("⌖", "find_care", "find_care_help", "care")


def care_page() -> None:
    """Open a location-specific Google Maps search without a facilities list."""
    top_nav(show_back=True, back_to="home")
    st.markdown("<div class='step'>Care finder</div>", unsafe_allow_html=True)
    st.title(ui_text("care_title"))
    st.markdown(f'<div class="page-intro">{ui_text("care_help")}</div>', unsafe_allow_html=True)

    location = st.text_input(ui_text("location_label"), key="care_location")
    if location.strip():
        maps_query = quote_plus(f"dermatologist public hospital skin clinic near {location.strip()}")
        st.link_button(ui_text("open_maps"), f"https://www.google.com/maps/search/?api=1&query={maps_query}", use_container_width=True)
        st.info(ui_text("care_note"))
    else:
        st.caption("Enter a location to open a focused search.")

    if st.button(ui_text("check_skin"), key="care_check_skin", use_container_width=True):
        navigate("upload")


def upload_page() -> None:
    top_nav(show_back=True, back_to="home")
    st.markdown("<div class='step'>1 / 3</div>", unsafe_allow_html=True)
    st.title(ui_text("upload_title"))
    st.write(ui_text("upload_help"))

    camera_tab, gallery_tab = st.tabs([ui_text("camera"), ui_text("gallery")])
    selected_file = None
    with camera_tab:
        selected_file = st.camera_input(ui_text("camera"))
    with gallery_tab:
        gallery_file = st.file_uploader(ui_text("gallery"), type=["jpg", "jpeg", "png"])
        selected_file = selected_file or gallery_file

    if selected_file is not None:
        valid, message, image_meta = validate_image(selected_file)
        if valid and image_meta:
            st.session_state["image_meta"] = image_meta
            st.session_state["recovery_saved_current"] = False
            st.success(message)
        else:
            st.warning(message)

    image_meta: ImageMeta | None = st.session_state.get("image_meta")
    if image_meta:
        st.image(image_meta.data, caption=f"{image_meta.filename} · {image_meta.width}×{image_meta.height}")
        if st.button(ui_text("run_check"), use_container_width=True):
            with st.spinner("Preparing result..."):
                result = run_image_inference(image_meta.data)
            st.session_state["inference_result"] = result
            questions = choose_follow_up_questions(result)
            navigate("questions" if questions else "result")


def questions_page() -> None:
    top_nav(show_back=True, back_to="upload")
    result: InferenceResult | None = st.session_state.get("inference_result")
    if result is None:
        st.warning("Please upload an image first.")
        return
    questions = choose_follow_up_questions(result)
    st.markdown("<div class='step'>2 / 3</div>", unsafe_allow_html=True)
    st.title(ui_text("questions_title"))
    if result.demo_mode:
        st.info(result.explanation)

    with st.form("follow_up_form"):
        urgent = st.radio(questions[0], [ui_text("yes"), ui_text("no")], horizontal=True, index=None)
        breathing = st.radio(questions[1], [ui_text("yes"), ui_text("no")], horizontal=True, index=None)
        submitted = st.form_submit_button(ui_text("see_result"), use_container_width=True)
    if submitted:
        if urgent is None or breathing is None:
            st.warning(ui_text("answer_all"))
            return
        answers = {"urgent": urgent, "breathing": breathing}
        st.session_state["followup_answers"] = answers
        st.session_state["inference_result"] = final_result_from_followups(result, answers)
        navigate("result")


def urgency_box(urgency: str, message: str) -> None:
    if urgency == URGENCY_URGENT:
        st.error(f"{urgency}: {message}")
    elif urgency == URGENCY_DERM:
        st.warning(f"{urgency}: {message}")
    else:
        st.success(f"{urgency}: {message}")


def save_current_to_recovery() -> None:
    result: InferenceResult | None = st.session_state.get("inference_result")
    image_meta: ImageMeta | None = st.session_state.get("image_meta")
    if not result or not image_meta or st.session_state.get("recovery_saved_current"):
        return
    st.session_state["recovery_history"].append(
        {
            "timestamp": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(timespec="seconds"),
            "image_bytes": image_meta.data,
            "filename": image_meta.filename,
            "condition": result.condition or "Demo mode: no condition predicted",
            "summary": result.explanation,
            "urgency": result.urgency,
            "status": "",
        }
    )
    st.session_state["recovery_saved_current"] = True


def result_page() -> None:
    top_nav(show_back=True, back_to="questions")
    st.markdown("<div class='step'>3 / 3</div>", unsafe_allow_html=True)
    st.title(ui_text("result_title"))
    result: InferenceResult | None = st.session_state.get("inference_result")
    image_meta: ImageMeta | None = st.session_state.get("image_meta")
    if not result:
        st.warning("No result is ready yet.")
        return

    if not st.session_state.get("submission_tracking_attempted"):
        disease_type = result.condition or "No condition predicted"
        accuracy = (
            f"{round(result.confidence * 100)}%"
            if result.confidence is not None and not result.demo_mode
            else "Not available"
        )
        append_submission_to_sheet(
            st.session_state.get("user_name", "Unknown"),
            disease_type,
            accuracy,
        )
    if st.session_state.get("submission_tracking_saved"):
        st.success("Assessment saved.")
    elif st.session_state.get("submission_tracking_warning"):
        st.warning(st.session_state["submission_tracking_warning"])

    if image_meta:
        st.image(image_meta.data, caption=image_meta.filename)

    with st.container(border=True):
        st.subheader(ui_text("possible_condition"))
        if result.condition:
            st.write(result.condition)
        else:
            st.info(result.explanation)
        if result.confidence is not None and not result.demo_mode:
            st.progress(float(result.confidence))
            st.write(f"{ui_text('confidence')}: {round(result.confidence * 100)}%")
        st.write(result.explanation)
        if result.top_predictions:
            st.caption(ui_text("alternatives"))
            for prediction in result.top_predictions[:3]:
                st.write(f"- {prediction}")

    urgency_box(result.urgency, result.urgency_message)
    st.info(ui_text("disclaimer"))

    cols = st.columns(3)
    with cols[0]:
        if st.button(ui_text("save_recovery"), key="result_save_recovery", use_container_width=True):
            save_current_to_recovery()
            st.success(ui_text("saved_recovery"))
    with cols[1]:
        if st.button(ui_text("check_another"), key="result_check_another", use_container_width=True):
            st.session_state["image_meta"] = None
            st.session_state["inference_result"] = None
            st.session_state["followup_answers"] = {}
            st.session_state["submission_tracking_attempted"] = False
            st.session_state["submission_tracking_saved"] = False
            st.session_state["submission_tracking_warning"] = ""
            navigate("upload")
    with cols[2]:
        if st.button(ui_text("home"), key="result_bottom_home", use_container_width=True):
            navigate("home")


def recovery_page() -> None:
    top_nav(show_back=True, back_to="home")
    st.title(ui_text("recovery"))
    st.info(ui_text("comparison_note"))
    history = st.session_state.get("recovery_history", [])
    if not history:
        st.info(ui_text("no_history"))
        return

    for index, record in enumerate(reversed(history), start=1):
        with st.container(border=True):
            st.subheader(f"{index}. {record['condition']}")
            st.write(record["timestamp"])
            st.image(record["image_bytes"], width=260)
            st.write(record["summary"])
            urgency_box(record["urgency"], "")
            status = st.radio(
                ui_text("status_label"),
                [ui_text("improving"), ui_text("unchanged"), ui_text("worsening")],
                horizontal=True,
                key=f"recovery_status_{index}",
                index=None,
            )
            if status:
                record["status"] = status


def urgent_chat_message(message: str) -> bool:
    lowered = message.lower()
    terms = ("pain", "pus", "fever", "swelling", "spreading", "bleeding", "breathing", "severe")
    return any(term in lowered for term in terms)


def answer_chat(message: str) -> str:
    if urgent_chat_message(message):
        return "Please seek medical help soon for pain, pus, fever, swelling, rapid spreading, bleeding, or breathing trouble. I cannot diagnose through chat."
    lowered = message.lower()
    if "sea" in lowered or "salt" in lowered or "water" in lowered:
        return "After seawater work, rinse with clean water, dry the skin well, and change wet gloves or boots."
    if "itch" in lowered:
        return "Avoid scratching. Wash gently, dry well, and see a dermatologist if itching continues or spreads."
    if "sun" in lowered:
        return "Use shade, protective clothing, and sunscreen when possible. Seek care for blisters or severe pain."
    return "I can share general skin-care guidance, but I cannot diagnose. Please see a dermatologist if symptoms worsen."


def chatbot_page() -> None:
    top_nav(show_back=True, back_to="home")
    st.title(ui_text("chat_title"))
    st.info(ui_text("disclaimer"))
    for role, message in st.session_state["chat_history"]:
        with st.chat_message(role):
            st.write(message)

    prompt = st.chat_input(ui_text("chat_placeholder"))
    if prompt is not None:
        cleaned = prompt.strip()
        if cleaned:
            st.session_state["chat_history"].append(("user", cleaned))
            st.session_state["chat_history"].append(("assistant", answer_chat(cleaned)))
            st.rerun()
        st.warning("Please type a question.")

    if st.button(ui_text("clear_chat"), use_container_width=True):
        st.session_state["chat_history"] = []
        st.rerun()


# -----------------------------------------------------------------------------
# 9. Main router
# -----------------------------------------------------------------------------

def main() -> None:
    init_state()
    apply_css()
    if not st.session_state.get("logged_in"):
        login_page()
        return

    screen = st.session_state.get("screen", "language")
    if screen not in VALID_SCREENS:
        st.session_state["screen"] = "home"
        st.rerun()

    pages = {
        "language": language_page,
        "home": home_page,
        "upload": upload_page,
        "questions": questions_page,
        "result": result_page,
        "recovery": recovery_page,
        "chatbot": chatbot_page,
        "care": care_page,
    }
    pages[st.session_state["screen"]]()
    bottom_logout()


if __name__ == "__main__":
    main()
