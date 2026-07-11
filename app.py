import logging
import re
from datetime import datetime
from io import BytesIO
from zoneinfo import ZoneInfo

import streamlit as st
from PIL import Image, UnidentifiedImageError


# -----------------------------------------------------------------------------
# Imports, configuration, and logging
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="SkinSense",
    page_icon="🩺",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DEFAULT_GOOGLE_SHEET_ID = "1VCwoQWGVI-9y7m9WGlWQlM4nSZ4Hs0F6TqexuuMYbPU"
DEFAULT_WORKSHEET_NAME = "Sheet1"
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

MAX_NAME_LENGTH = 80
MAX_IMAGE_BYTES = 10 * 1024 * 1024
SUPPORTED_IMAGE_FORMATS = {"JPEG", "PNG"}

VALID_SCREENS = {
    "language",
    "home",
    "upload",
    "questions",
    "result",
    "recovery",
    "chat",
}


# -----------------------------------------------------------------------------
# Translation dictionaries
# -----------------------------------------------------------------------------

TRANSLATIONS = {
    "English": {
        "continue": "Continue",
        "home": "Home",
        "back": "Back",
        "logout": "Logout",
        "name_title": "Welcome to SkinSense",
        "name_description": "A simple screening aid for Koli fishing communities working in seawater, sun, and humid conditions.",
        "name_label": "Enter your name",
        "language_title": "Choose your language",
        "home_title": "What would you like to do?",
        "check_skin": "Check my skin",
        "check_skin_help": "Take or upload a clear photo.",
        "recovery": "Recovery tracking",
        "recovery_help": "View checks from this session.",
        "ask_question": "Ask a skin-care question",
        "ask_question_help": "Simple guidance about seawater, sun, itching, and rashes.",
        "upload_title": "Show us the skin problem",
        "upload_help": "Use a clear photo in good light, close to the affected skin.",
        "take_photo": "Take a photo",
        "choose_gallery": "Choose from gallery",
        "questions_title": "Two safety questions",
        "result_title": "Your result",
        "chat_title": "Ask about skin care",
    },
    "हिंदी": {
        "continue": "आगे बढ़ें",
        "home": "होम",
        "back": "पीछे",
        "logout": "लॉग आउट",
        "name_title": "SkinSense में स्वागत है",
        "name_description": "समुद्री पानी, धूप और नमी में काम करने वाले कोली मछुआरा समुदाय के लिए सरल स्क्रीनिंग सहायता.",
        "name_label": "अपना नाम लिखें",
        "language_title": "भाषा चुनें",
        "home_title": "आप क्या करना चाहेंगे?",
        "check_skin": "त्वचा जांचें",
        "check_skin_help": "साफ फोटो लें या अपलोड करें.",
        "recovery": "रिकवरी ट्रैकिंग",
        "recovery_help": "इस सत्र की जांचें देखें.",
        "ask_question": "त्वचा देखभाल सवाल पूछें",
        "ask_question_help": "समुद्री पानी, धूप, खुजली और रैश पर सरल सलाह.",
        "upload_title": "त्वचा की समस्या दिखाएं",
        "upload_help": "अच्छी रोशनी में प्रभावित त्वचा की साफ नजदीकी फोटो लें.",
        "take_photo": "फोटो लें",
        "choose_gallery": "गैलरी से चुनें",
        "questions_title": "दो सुरक्षा सवाल",
        "result_title": "आपका परिणाम",
        "chat_title": "त्वचा देखभाल के बारे में पूछें",
    },
    "मराठी": {
        "continue": "पुढे",
        "home": "होम",
        "back": "मागे",
        "logout": "लॉग आउट",
        "name_title": "SkinSense मध्ये स्वागत आहे",
        "name_description": "समुद्राचे पाणी, ऊन आणि दमट हवेत काम करणाऱ्या कोळी मच्छीमार समुदायासाठी सोपी स्क्रीनिंग मदत.",
        "name_label": "तुमचे नाव लिहा",
        "language_title": "भाषा निवडा",
        "home_title": "तुम्हाला काय करायचे आहे?",
        "check_skin": "त्वचा तपासा",
        "check_skin_help": "स्पष्ट फोटो घ्या किंवा अपलोड करा.",
        "recovery": "रिकव्हरी ट्रॅकिंग",
        "recovery_help": "या सत्रातील तपासण्या पहा.",
        "ask_question": "त्वचा काळजी प्रश्न विचारा",
        "ask_question_help": "समुद्राचे पाणी, ऊन, खाज आणि पुरळ याबद्दल सोपी मदत.",
        "upload_title": "त्वचेची समस्या दाखवा",
        "upload_help": "चांगल्या प्रकाशात प्रभावित त्वचेचा जवळचा स्पष्ट फोटो घ्या.",
        "take_photo": "फोटो घ्या",
        "choose_gallery": "गॅलरीतून निवडा",
        "questions_title": "दोन सुरक्षा प्रश्न",
        "result_title": "तुमचा निकाल",
        "chat_title": "त्वचा काळजीबद्दल विचारा",
    },
}


# -----------------------------------------------------------------------------
# Constants and metadata
# -----------------------------------------------------------------------------

URGENCY_HOME = "Manage at home"
URGENCY_DERM = "Visit a dermatologist soon"
URGENCY_URGENT = "Seek immediate medical attention"

URGENT_TERMS = (
    "fever",
    "pus",
    "major swelling",
    "severe pain",
    "rapidly spreading",
    "spreading redness",
    "facial swelling",
    "trouble breathing",
    "bad smell",
    "bleeding",
)


# -----------------------------------------------------------------------------
# State initialization
# -----------------------------------------------------------------------------

def init_state() -> None:
    defaults = {
        "logged_in": False,
        "user_name": "",
        "language": "English",
        "screen": "language",
        "login_tracking_attempted": False,
        "login_tracking_saved": False,
        "login_tracking_warning": "",
        "login_tracking_warning_shown": False,
        "image_bytes": None,
        "image_name": "",
        "image_format": "",
        "image_size": None,
        "inference_result": None,
        "safety_answers": {},
        "result": None,
        "recovery_history": [],
        "chat_history": [],
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def t(key: str) -> str:
    return TRANSLATIONS.get(st.session_state.get("language", "English"), TRANSLATIONS["English"]).get(key, key)


# -----------------------------------------------------------------------------
# Basic branding CSS
# -----------------------------------------------------------------------------

def apply_branding() -> None:
    st.markdown(
        """
        <style>
        :root {
            --skinsense-bg: #f6fbfd;
            --skinsense-navy: #08213d;
            --skinsense-blue: #0b6fa4;
            --skinsense-soft: #eaf7fc;
            --skinsense-muted: #566b7a;
        }
        .stApp {
            background: var(--skinsense-bg);
        }
        h1, h2, h3 {
            color: var(--skinsense-navy);
        }
        .skinsense-logo {
            width: 4.25rem;
            height: 4.25rem;
            border-radius: 50%;
            background: var(--skinsense-blue);
            color: white;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }
        .muted-copy {
            color: var(--skinsense-muted);
            line-height: 1.45;
        }
        .soft-note {
            background: var(--skinsense-soft);
            border-radius: 0.75rem;
            padding: 0.85rem 1rem;
        }
        .result-condition {
            color: var(--skinsense-navy);
            font-size: 1.35rem;
            font-weight: 700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# Secret validation and Google Sheets functions
# -----------------------------------------------------------------------------

def clean_name(value: str) -> str:
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", str(value or ""))
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def normalize_private_key(value: str) -> str:
    key = str(value or "").strip()
    key = key.replace("\\n", "\n").replace("\r\n", "\n").replace("\r", "\n")

    begin_marker = "-----BEGIN PRIVATE KEY-----"
    end_marker = "-----END PRIVATE KEY-----"
    if begin_marker not in key or end_marker not in key:
        raise ValueError("The Google service-account private key is malformed or incomplete.")

    start = key.index(begin_marker)
    end = key.index(end_marker) + len(end_marker)
    key = key[start:end]
    lines = [line.strip() for line in key.split("\n") if line.strip()]
    normalized = "\n".join(lines) + "\n"

    if not normalized.startswith(begin_marker) or not normalized.rstrip().endswith(end_marker):
        raise ValueError("The Google service-account private key is malformed or incomplete.")
    return normalized


def read_service_account_section() -> dict:
    for section_name in ("gcp_service_account", "google_service_account", "service_account"):
        if section_name in st.secrets:
            return dict(st.secrets[section_name])
    raise KeyError("No supported Google service-account section is configured.")


def read_google_sheet_config() -> tuple[str, str, dict]:
    sheet_id = str(st.secrets.get("google_sheet_id", DEFAULT_GOOGLE_SHEET_ID)).strip()
    worksheet_name = str(st.secrets.get("worksheet_name", "Sheet1")).strip() or "Sheet1"
    credentials_info = read_service_account_section()

    required = ("type", "project_id", "private_key", "client_email", "token_uri")
    missing = [field for field in required if not credentials_info.get(field)]
    if not sheet_id:
        missing.append("google_sheet_id")
    if missing:
        raise ValueError("Missing required Google Sheets configuration.")

    credentials_info["private_key"] = normalize_private_key(credentials_info["private_key"])
    return sheet_id, worksheet_name, credentials_info


def append_usage_tracking(cleaned_name: str) -> bool:
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except Exception:
        logger.exception("Google Sheets usage tracking failed")
        return False

    try:
        sheet_id, worksheet_name, credentials_info = read_google_sheet_config()
        credentials = Credentials.from_service_account_info(credentials_info, scopes=GOOGLE_SCOPES)
        client = gspread.authorize(credentials)
        spreadsheet = client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet(worksheet_name)
        timestamp = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(timespec="seconds")
        worksheet.append_row([timestamp, cleaned_name], value_input_option="RAW")
        return True
    except Exception:
        logger.exception("Google Sheets usage tracking failed")
        return False


def enter_app_with_name(name: str) -> tuple[bool, str]:
    cleaned_name = clean_name(name)
    if not cleaned_name:
        return False, "Please enter your name to continue."
    if len(cleaned_name) > MAX_NAME_LENGTH:
        return False, "Please enter a shorter name, up to 80 characters."

    st.session_state["logged_in"] = True
    st.session_state["user_name"] = cleaned_name
    st.session_state["screen"] = "language"

    if not st.session_state["login_tracking_attempted"]:
        st.session_state["login_tracking_attempted"] = True
        saved = append_usage_tracking(cleaned_name)
        st.session_state["login_tracking_saved"] = saved
        if not saved:
            st.session_state["login_tracking_warning"] = (
                "SkinSense opened successfully, but usage tracking could not be saved."
            )
    return True, "Welcome to SkinSense."


# -----------------------------------------------------------------------------
# Image validation
# -----------------------------------------------------------------------------

def validate_image(uploaded_file) -> tuple[bool, str, dict | None]:
    if uploaded_file is None:
        return False, "Please take or upload a photo first.", None

    raw = uploaded_file.getvalue()
    if not raw:
        return False, "The selected image is empty. Please try another photo.", None
    if len(raw) > MAX_IMAGE_BYTES:
        return False, "Please use an image under 10 MB.", None

    try:
        image = Image.open(BytesIO(raw))
        image.verify()
        image = Image.open(BytesIO(raw)).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError):
        return False, "This file could not be read as an image. Please use JPG or PNG.", None

    width, height = image.size
    image_format = (Image.open(BytesIO(raw)).format or "").upper()
    if image_format not in SUPPORTED_IMAGE_FORMATS:
        return False, "Please use a JPG, JPEG, or PNG image.", None
    if width < 1 or height < 1:
        return False, "This image has invalid dimensions. Please try another photo.", None

    metadata = {
        "bytes": raw,
        "name": getattr(uploaded_file, "name", "camera_photo.jpg"),
        "format": image_format,
        "size": (width, height),
    }
    return True, "Image ready.", metadata


# -----------------------------------------------------------------------------
# Model interface
# -----------------------------------------------------------------------------

def run_image_inference(image_bytes: bytes) -> dict:
    """
    Placeholder interface for future model integration.

    No trained model is currently bundled with this repository, so this function
    intentionally does not return a diagnosis or fake confidence score.
    """
    return {
        "mode": "demo",
        "model_available": False,
        "possible_condition": None,
        "confidence": None,
        "needs_followup": True,
        "message": "Demo mode: no trained SkinSense image model is connected yet.",
    }


def build_result_from_safety_answers(inference_result: dict, answers: dict) -> dict:
    urgent = answers.get("urgent_symptoms") == "Yes"
    breathing = answers.get("breathing_or_face") == "Yes"

    if breathing:
        urgency = URGENCY_URGENT
        next_steps = [
            "Seek urgent medical help now.",
            "If breathing is difficult, use local emergency care immediately.",
        ]
    elif urgent:
        urgency = URGENCY_URGENT
        next_steps = [
            "See a doctor urgently for fever, pus, major swelling, severe pain, or fast-spreading redness.",
            "Keep the area clean and avoid scratching.",
        ]
    else:
        urgency = URGENCY_DERM
        next_steps = [
            "Take a clear close-up photo again when possible.",
            "Keep the area clean and dry.",
            "Visit a dermatologist soon if it spreads, hurts, forms pus, or does not improve.",
        ]

    return {
        "mode": inference_result["mode"],
        "possible_condition": inference_result["possible_condition"],
        "confidence": inference_result["confidence"],
        "urgency": urgency,
        "summary": inference_result["message"],
        "next_steps": next_steps,
        "timestamp": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(timespec="seconds"),
    }


# -----------------------------------------------------------------------------
# Navigation
# -----------------------------------------------------------------------------

def navigate(screen: str) -> None:
    if screen not in VALID_SCREENS:
        logger.warning("Invalid screen requested: %s", screen)
        st.session_state["screen"] = "language"
    else:
        st.session_state["screen"] = screen
    st.rerun()


def logout() -> None:
    st.session_state.clear()
    st.rerun()


def top_navigation(show_back: bool = False, back_to: str = "home") -> None:
    cols = st.columns([1, 1, 1])
    with cols[0]:
        if show_back and st.button(t("back"), use_container_width=True):
            navigate(back_to)
    with cols[1]:
        if st.button(t("home"), use_container_width=True):
            navigate("home")
    with cols[2]:
        if st.button(t("logout"), use_container_width=True):
            logout()


def show_tracking_warning_once() -> None:
    if st.session_state.get("login_tracking_warning") and not st.session_state.get("login_tracking_warning_shown"):
        st.warning(st.session_state["login_tracking_warning"])
        st.session_state["login_tracking_warning_shown"] = True


# -----------------------------------------------------------------------------
# Page functions
# -----------------------------------------------------------------------------

def name_entry_page() -> None:
    st.markdown('<div class="skinsense-logo">🩺</div>', unsafe_allow_html=True)
    st.title(t("name_title"))
    st.write(t("name_description"))

    with st.container(border=True):
        with st.form("name_form", clear_on_submit=False):
            name = st.text_input(t("name_label"), max_chars=MAX_NAME_LENGTH)
            submitted = st.form_submit_button(t("continue"), use_container_width=True)

        if submitted:
            success, message = enter_app_with_name(name)
            if success:
                st.success(message)
                st.rerun()
            st.warning(message)

    st.info("SkinSense is a screening aid, not a medical diagnosis. For serious symptoms, please see a doctor.")


def language_page() -> None:
    st.title(t("language_title"))
    st.caption(f"{st.session_state['user_name']}")
    language = st.radio(
        "Language",
        ["English", "हिंदी", "मराठी"],
        index=["English", "हिंदी", "मराठी"].index(st.session_state.get("language", "English")),
        horizontal=True,
    )
    st.session_state["language"] = language
    if st.button(t("continue"), use_container_width=True):
        navigate("home")


def home_page() -> None:
    top_navigation()
    st.title(t("home_title"))
    st.write("Choose one action.")

    with st.container(border=True):
        st.subheader(t("check_skin"))
        st.write(t("check_skin_help"))
        if st.button(t("check_skin"), use_container_width=True):
            navigate("upload")

    with st.container(border=True):
        st.subheader(t("recovery"))
        st.write(t("recovery_help"))
        if st.button(t("recovery"), use_container_width=True):
            navigate("recovery")

    with st.container(border=True):
        st.subheader(t("ask_question"))
        st.write(t("ask_question_help"))
        if st.button(t("ask_question"), use_container_width=True):
            navigate("chat")


def upload_page() -> None:
    top_navigation(show_back=True, back_to="home")
    st.title(t("upload_title"))
    st.write(t("upload_help"))

    with st.form("image_form"):
        camera_image = st.camera_input(t("take_photo"))
        gallery_image = st.file_uploader(t("choose_gallery"), type=["jpg", "jpeg", "png"])
        submitted = st.form_submit_button(t("continue"), use_container_width=True)

    selected_file = camera_image or gallery_image
    if selected_file:
        valid, message, metadata = validate_image(selected_file)
        if valid and metadata:
            st.image(metadata["bytes"], caption=f"{metadata['format']} • {metadata['size'][0]}×{metadata['size'][1]}")
        else:
            st.warning(message)

    if submitted:
        valid, message, metadata = validate_image(selected_file)
        if not valid or metadata is None:
            st.warning(message)
            return

        st.session_state["image_bytes"] = metadata["bytes"]
        st.session_state["image_name"] = metadata["name"]
        st.session_state["image_format"] = metadata["format"]
        st.session_state["image_size"] = metadata["size"]

        with st.spinner("Preparing screening questions..."):
            st.session_state["inference_result"] = run_image_inference(metadata["bytes"])
        navigate("questions")


def questions_page() -> None:
    top_navigation(show_back=True, back_to="upload")
    inference_result = st.session_state.get("inference_result")
    if not inference_result:
        st.warning("Please upload an image first.")
        return

    st.title(t("questions_title"))
    st.info(inference_result["message"])

    with st.form("safety_questions_form"):
        urgent_symptoms = st.radio(
            "Do you have fever, pus, major swelling, severe pain, or rapidly spreading redness?",
            ["Yes", "No"],
            horizontal=True,
            index=None,
        )
        breathing_or_face = st.radio(
            "Do you have facial swelling or trouble breathing?",
            ["Yes", "No"],
            horizontal=True,
            index=None,
        )
        submitted = st.form_submit_button("See result", use_container_width=True)

    if submitted:
        if urgent_symptoms is None or breathing_or_face is None:
            st.warning("Please answer both questions before continuing.")
            return
        answers = {
            "urgent_symptoms": urgent_symptoms,
            "breathing_or_face": breathing_or_face,
        }
        st.session_state["safety_answers"] = answers
        result = build_result_from_safety_answers(inference_result, answers)
        st.session_state["result"] = result
        st.session_state["recovery_history"].append(
            {
                "timestamp": result["timestamp"],
                "image_bytes": st.session_state.get("image_bytes"),
                "summary": result["summary"],
                "urgency": result["urgency"],
                "status": "Not compared",
            }
        )
        navigate("result")


def result_page() -> None:
    top_navigation(show_back=True, back_to="questions")
    result = st.session_state.get("result")
    if not result:
        st.warning("No result yet. Please complete a skin check first.")
        return

    st.title(t("result_title"))
    image_bytes = st.session_state.get("image_bytes")
    if image_bytes:
        st.image(image_bytes, caption="Uploaded image", use_container_width=True)

    with st.container(border=True):
        st.subheader("Model status")
        st.write(result["summary"])
        if result["possible_condition"]:
            st.subheader(result["possible_condition"])
        else:
            st.info("No possible condition is shown because no trained image model is connected yet.")
        if result["confidence"] is not None:
            st.progress(float(result["confidence"]))

    with st.container(border=True):
        st.subheader("Urgency")
        if result["urgency"] == URGENCY_URGENT:
            st.error(result["urgency"])
        elif result["urgency"] == URGENCY_DERM:
            st.warning(result["urgency"])
        else:
            st.success(result["urgency"])

    with st.container(border=True):
        st.subheader("Next steps")
        for step in result["next_steps"]:
            st.write(f"• {step}")

    st.info("This is not a medical diagnosis. It is only a guide. If symptoms worsen, please see a doctor.")


def recovery_page() -> None:
    top_navigation(show_back=True, back_to="home")
    st.title(t("recovery"))
    history = st.session_state.get("recovery_history", [])
    if not history:
        st.info("No skin checks in this session yet.")
        return

    for index, item in enumerate(reversed(history), start=1):
        with st.container(border=True):
            st.subheader(f"Check {index}")
            st.write(item["timestamp"])
            if item.get("image_bytes"):
                st.image(item["image_bytes"], width=260)
            st.write(f"Urgency: {item['urgency']}")
            st.write(f"Status: {item['status']}")
    st.caption("SkinSense does not automatically compare medical images yet. Status is only stored when entered manually in a future version.")


def urgent_chat_needed(message: str) -> bool:
    lowered = message.lower()
    return any(term in lowered for term in URGENT_TERMS)


def answer_chat(message: str) -> str:
    if urgent_chat_needed(message):
        return (
            "Please seek urgent medical care if there is fever, pus, major swelling, severe pain, rapidly spreading redness, "
            "facial swelling, or trouble breathing."
        )
    lowered = message.lower()
    if "salt" in lowered or "sea" in lowered or "water" in lowered:
        return "After seawater work, rinse with clean water, dry well, change wet gloves or boots, and cover small cuts."
    if "itch" in lowered:
        return "Do not scratch. Wash gently, dry the skin, and avoid staying in wet gloves or boots for long periods."
    if "sun" in lowered:
        return "Cover exposed skin, rest in shade when possible, drink water, and seek care for blisters or severe pain."
    return "I can share general skin-care guidance, but I cannot diagnose through chat. Please see a dermatologist if it worsens or does not improve."


def chat_page() -> None:
    top_navigation(show_back=True, back_to="home")
    st.title(t("chat_title"))
    st.write("This helper gives general guidance only and does not diagnose.")

    for role, message in st.session_state["chat_history"]:
        with st.chat_message(role):
            st.write(message)

    prompt = st.chat_input("Type your question...")
    if prompt is not None:
        cleaned = prompt.strip()
        if cleaned:
            st.session_state["chat_history"].append(("user", cleaned))
            st.session_state["chat_history"].append(("assistant", answer_chat(cleaned)))
            st.rerun()
        st.warning("Please type a question.")

    cols = st.columns(2)
    with cols[0]:
        if st.button("Clear chat", use_container_width=True):
            st.session_state["chat_history"] = []
            st.rerun()
    with cols[1]:
        if st.button(t("home"), use_container_width=True):
            navigate("home")


# -----------------------------------------------------------------------------
# Main router
# -----------------------------------------------------------------------------

def main() -> None:
    init_state()
    apply_branding()

    if not st.session_state.get("logged_in"):
        name_entry_page()
        return

    show_tracking_warning_once()

    screen = st.session_state.get("screen", "language")
    if screen not in VALID_SCREENS:
        st.session_state["screen"] = "language"
        st.rerun()

    if screen == "language":
        language_page()
    elif screen == "home":
        home_page()
    elif screen == "upload":
        upload_page()
    elif screen == "questions":
        questions_page()
    elif screen == "result":
        result_page()
    elif screen == "recovery":
        recovery_page()
    elif screen == "chat":
        chat_page()


if __name__ == "__main__":
    main()

