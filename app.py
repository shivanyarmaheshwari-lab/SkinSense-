from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import streamlit as st
from PIL import Image, UnidentifiedImageError
from tensorflow.keras.models import load_model


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
        "upload_help": "Use a JPG or PNG photo under 10 MB. Take the photo close to the skin in good light.",
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
        "upload_help": "10 MB से कम JPG या PNG फोटो डालें. फोटो अच्छी रोशनी में त्वचा के पास से लें.",
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
        "upload_help": "10 MB पेक्षा कमी JPG किंवा PNG फोटो वापरा. चांगल्या प्रकाशात जवळून फोटो घ्या.",
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


@dataclass
class Prediction:
    condition: str
    image_confidence: float
    final_score: float
    top_predictions: list[tuple[str, float]]
    urgency: str
    advice: str
    explanation: str


def css() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: #eef9fc; }
        h1, h2, h3 { color: #08213d; }
        p, label, li { color: #08213d; }
        .block-container { max-width: 760px; padding-top: 2rem; }
        .brand {
            width: 74px; height: 74px; border-radius: 50%;
            background: #075985; color: white; display: flex;
            align-items: center; justify-content: center;
            font-size: 36px; margin-bottom: 12px;
        }
        .small-muted { color: #5c6f7d; font-size: 0.95rem; }
        .stButton > button {
            min-height: 48px; border-radius: 12px; font-weight: 700;
            border: 1px solid #0b6fa4;
        }
        .stButton > button[kind="primary"] {
            background: #0b6fa4; color: white;
        }
        </style>
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
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def go(page: str) -> None:
    st.session_state["page"] = page if page in VALID_PAGES else "start"
    st.rerun()


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
    urgent_words = " ".join(f"{question} {answer}" for question, answer in answers.items()).lower()

    if condition == "Cellulitis" or ("painful" in urgent_words and "yes" in urgent_words and "getting worse" in urgent_words):
        urgency = "Visit a dermatologist soon"
        advice = "Please get this checked soon, especially if redness spreads, skin feels warm, pain increases, or fever appears."
    elif condition in {"Impetigo", "Paronychia"}:
        urgency = "See a doctor if it spreads or forms pus"
        advice = "Keep the area clean and covered. Avoid sharing towels. See a doctor if fluid, pus, fever, or spreading redness appears."
    else:
        urgency = "Monitor and care at home, but see a dermatologist if it worsens"
        advice = "Keep the area clean and dry. Avoid scratching. Seek care if it spreads, hurts, forms pus, or does not improve."

    return Prediction(
        condition=condition,
        image_confidence=image_confidence,
        final_score=final_score,
        top_predictions=top_predictions,
        urgency=urgency,
        advice=advice,
        explanation=DISEASE_INFO.get(condition, "This result is based on the image model and your answers."),
    )


def start_page() -> None:
    st.markdown("<div class='brand'>🩺</div>", unsafe_allow_html=True)
    st.title("SkinSense")
    st.write(t("tagline"))

    with st.form("start_form"):
        name = st.text_input(t("name"), max_chars=80)
        language = st.radio(t("language"), ["English", "हिंदी", "मराठी"], horizontal=True)
        submitted = st.form_submit_button(t("continue"), use_container_width=True)

    if submitted:
        cleaned = clean_name(name)
        if not cleaned:
            st.warning("Please enter your name.")
            return
        st.session_state["name"] = cleaned
        st.session_state["language"] = language
        go("upload")

    st.info(t("disclaimer"))


def upload_page() -> None:
    st.title(t("upload_title"))
    st.write(t("upload_help"))
    st.caption("No camera page is used. Upload from your gallery/files only.")

    uploaded_file = st.file_uploader("Upload image", type=["jpg", "jpeg", "png"], accept_multiple_files=False)
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

    st.title(t("result_title"))
    if st.session_state.get("image_bytes"):
        st.image(st.session_state["image_bytes"], caption=st.session_state.get("image_name", "Uploaded image"), use_container_width=True)

    st.subheader(prediction.condition)
    st.write(prediction.explanation)
    st.metric("Image model confidence", f"{prediction.image_confidence * 100:.0f}%")
    st.metric("Final screening score", f"{prediction.final_score * 100:.0f}%")

    st.warning(f"{prediction.urgency}: {prediction.advice}")

    st.write("Top image matches:")
    for condition, confidence in prediction.top_predictions:
        st.write(f"- {condition}: {confidence * 100:.0f}%")

    st.info(t("disclaimer"))

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
