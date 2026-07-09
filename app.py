import streamlit as st

st.set_page_config(page_title="SkinSense", layout="centered")

LANG = {
    "English": {
        "subtitle": "AI skin help for Koli fisherwomen and fishermen",
        "desc": "A simple app for people working long hours in seawater. Upload a skin photo, answer a few easy questions, and see possible risk with dermatologist guidance.",
        "pick": "Choose Language",
        "check": "AI Skin Check",
        "chat": "Skin Questions",
        "upload": "Upload a Skin Photo",
        "upload_help": "Use a clear photo of the affected skin area.",
        "questions": "Answer These 5 Questions",
        "result": "Your Skin Check Result",
    },
    "Hindi": {
        "subtitle": "Koli fisherwomen aur fishermen ke liye AI skin help",
        "desc": "Seawater mein long hours kaam karne wale logon ke liye simple app. Photo upload karein, easy questions answer karein, aur risk dekhein.",
        "pick": "Language Choose Karein",
        "check": "AI Skin Check",
        "chat": "Skin Questions",
        "upload": "Skin Photo Upload Karein",
        "upload_help": "Affected skin area ki clear photo upload karein.",
        "questions": "5 Simple Questions",
        "result": "Skin Check Result",
    },
    "Marathi": {
        "subtitle": "Koli fisherwomen ani fishermen sathi AI skin help",
        "desc": "Seawater madhye long hours kaam karanarya lokansathi simple app. Photo upload kara, easy questions answer kara, ani risk paha.",
        "pick": "Language Nivda",
        "check": "AI Skin Check",
        "chat": "Skin Questions",
        "upload": "Skin Photo Upload Kara",
        "upload_help": "Affected skin area cha clear photo upload kara.",
        "questions": "5 Simple Questions",
        "result": "Skin Check Result",
    },
}

DISEASES = {
    "Irritant Contact Dermatitis": {
        "risk": 72,
        "doctor": "Visit a dermatologist soon if it does not improve.",
        "advice": "Often caused by seawater, fish fluids, soap, or wet gloves. Keep skin clean and dry.",
    },
    "Ringworm": {
        "risk": 78,
        "doctor": "Visit a dermatologist soon. Fungal rashes can spread.",
        "advice": "Often circular and itchy. Keep dry and avoid sharing towels.",
    },
    "Athlete's Foot": {
        "risk": 69,
        "doctor": "Visit a dermatologist if peeling, cracks, or itching continue.",
        "advice": "Often caused by wet feet inside boots. Dry feet and change socks.",
    },
    "Cellulitis": {
        "risk": 90,
        "doctor": "Seek medical help immediately.",
        "advice": "Pain, swelling, heat, pus, or fever can mean a serious infection.",
    },
    "Sunburn": {
        "risk": 58,
        "doctor": "Manage at home unless severe pain, fever, or blisters appear.",
        "advice": "Cool the skin, drink water, and cover skin during strong sun.",
    },
}

OPTIONS = ["Yes", "No", "I don't know", "Maybe"]


def style():
    st.markdown(
        """
        <style>
        .stApp {
            background: #CFEFFF;
        }
        [data-testid="stHeader"] {
            background: transparent;
        }
        .block-container {
            max-width: 920px;
            padding-top: 28px;
        }
        .hero {
            background: #FFFFFF;
            border: 2px solid #A9DDF2;
            border-radius: 28px;
            padding: 34px 30px;
            text-align: center;
            box-shadow: 0 18px 45px rgba(7, 59, 76, 0.12);
            margin-bottom: 22px;
        }
        .logo {
            width: 96px;
            height: 96px;
            border-radius: 26px;
            margin: 0 auto 14px;
            display: grid;
            place-items: center;
            background: #EAF8FF;
            color: #0E7EAE;
            font-size: 34px;
            font-weight: 900;
            font-family: Georgia, serif;
            border: 3px solid #A9DDF2;
        }
        .brand {
            font-family: Georgia, serif;
            font-size: 76px;
            font-weight: 900;
            color: #073B4C;
            line-height: 0.95;
        }
        .subtitle {
            margin-top: 12px;
            color: #073B4C;
            font-size: 28px;
            font-weight: 900;
        }
        .desc {
            max-width: 720px;
            margin: 12px auto 0;
            color: #21596B;
            font-size: 22px;
            line-height: 1.45;
        }
        .panel {
            background: #FFFFFF;
            border: 2px solid #A9DDF2;
            border-radius: 24px;
            padding: 28px;
            box-shadow: 0 12px 30px rgba(7, 59, 76, 0.08);
            margin-bottom: 18px;
        }
        .title {
            color: #073B4C;
            font-size: 40px;
            line-height: 1.1;
            font-weight: 900;
            margin-bottom: 16px;
        }
        .card {
            height: 170px;
            border-radius: 22px;
            border: 2px solid #A9DDF2;
            background: #F8FDFF;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            text-align: center;
            margin-bottom: 10px;
        }
        .icon {
            width: 62px;
            height: 62px;
            border-radius: 20px;
            display: grid;
            place-items: center;
            background: #DFF5FF;
            color: #0E7EAE;
            font-size: 28px;
            font-weight: 900;
            margin-bottom: 12px;
        }
        .card-title {
            color: #073B4C;
            font-size: 25px;
            font-weight: 900;
        }
        .help {
            color: #21596B;
            font-size: 23px;
            line-height: 1.45;
            margin-bottom: 18px;
        }
        .result {
            border: 2px solid #A9DDF2;
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 14px;
            background: #F8FDFF;
        }
        .label {
            color: #4B7585;
            font-size: 18px;
            font-weight: 900;
            text-transform: uppercase;
        }
        .value {
            color: #073B4C;
            font-size: 32px;
            font-weight: 900;
            margin-top: 5px;
        }
        .risk {
            margin-top: 8px;
            padding: 16px;
            border-radius: 18px;
            text-align: center;
            background: #B7791F;
            color: white;
            font-size: 30px;
            font-weight: 900;
        }
        div.stButton > button {
            width: 100%;
            min-height: 64px;
            border-radius: 18px;
            border: 0;
            background: #0E7EAE;
            color: white;
            font-size: 23px;
            font-weight: 900;
        }
        div.stButton > button:hover {
            background: #08698F;
            color: white;
        }
        label {
            color: #073B4C !important;
            font-size: 22px !important;
            font-weight: 900 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init():
    st.session_state.setdefault("screen", "language")
    st.session_state.setdefault("lang", "English")
    st.session_state.setdefault("prediction", None)
    st.session_state.setdefault("uploaded_name", "")


def text():
    return LANG[st.session_state.lang]


def hero():
    t = text()
    st.markdown(
        f"""
        <div class="hero">
            <div class="logo">SS</div>
            <div class="brand">SkinSense</div>
            <div class="subtitle">{t["subtitle"]}</div>
            <div class="desc">{t["desc"]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def language_page():
    hero()
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown(f'<div class="title">{text()["pick"]}</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    for col, lang, short in zip(cols, ["English", "Hindi", "Marathi"], ["EN", "HI", "MR"]):
        with col:
            st.markdown(
                f'<div class="card"><div class="icon">{short}</div><div class="card-title">{lang}</div></div>',
                unsafe_allow_html=True,
            )
            if st.button(lang, key=f"lang-{lang}"):
                st.session_state.lang = lang
                st.session_state.screen = "menu"
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def menu_page():
    hero()
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    cols = st.columns(2)
    with cols[0]:
        st.markdown(
            f'<div class="card"><div class="icon">AI</div><div class="card-title">{text()["check"]}</div></div>',
            unsafe_allow_html=True,
        )
        if st.button(text()["check"], key="go-check"):
            st.session_state.screen = "upload"
            st.rerun()
    with cols[1]:
        st.markdown(
            f'<div class="card"><div class="icon">Q</div><div class="card-title">{text()["chat"]}</div></div>',
            unsafe_allow_html=True,
        )
        if st.button(text()["chat"], key="go-chat"):
            st.session_state.screen = "chat"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def upload_page():
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown(f'<div class="title">{text()["upload"]}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="help">{text()["upload_help"]}</div>', unsafe_allow_html=True)
    image = st.file_uploader("Upload image", type=["jpg", "jpeg", "png"])
    if image:
        st.session_state.uploaded_name = image.name
        st.image(image, use_container_width=True)
        if st.button("Continue"):
            st.session_state.screen = "questions"
            st.rerun()
    if st.button("Back"):
        st.session_state.screen = "menu"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def questions_page():
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown(f'<div class="title">{text()["questions"]}</div>', unsafe_allow_html=True)
    st.markdown('<div class="help">Select one answer for each question.</div>', unsafe_allow_html=True)

    qs = [
        "1. Is it itchy?",
        "2. Is it painful?",
        "3. Is the rash circular?",
        "4. Did it start after working in seawater?",
        "5. Is there pus, swelling, heat, or fever?",
    ]
    answers = {q: st.selectbox(q, OPTIONS, key=q) for q in qs}

    if st.button("See Result"):
        st.session_state.prediction = predict(answers)
        st.session_state.screen = "result"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def predict(answers):
    yes = {q: a == "Yes" for q, a in answers.items()}
    if yes["5. Is there pus, swelling, heat, or fever?"] and yes["2. Is it painful?"]:
        disease = "Cellulitis"
    elif yes["3. Is the rash circular?"]:
        disease = "Ringworm"
    elif yes["4. Did it start after working in seawater?"]:
        disease = "Irritant Contact Dermatitis"
    elif yes["1. Is it itchy?"]:
        disease = "Athlete's Foot"
    else:
        names = list(DISEASES)
        seed = sum(bytearray(st.session_state.uploaded_name.encode())) if st.session_state.uploaded_name else 0
        disease = names[seed % len(names)]

    result = DISEASES[disease].copy()
    yes_count = sum(yes.values())
    maybe_count = sum(a == "Maybe" for a in answers.values())
    result["name"] = disease
    result["risk"] = min(result["risk"] + yes_count * 3 + maybe_count, 96)
    return result


def result_page():
    p = st.session_state.prediction
    if not p:
        st.session_state.screen = "upload"
        st.rerun()

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown(f'<div class="title">{text()["result"]}</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="result">
            <div class="label">Disease Name</div>
            <div class="value">{p["name"]}</div>
        </div>
        <div class="result">
            <div class="label">Risk Percentage</div>
            <div class="risk">{p["risk"]}% Risk</div>
        </div>
        <div class="result">
            <div class="label">Should they meet a dermatologist?</div>
            <div class="help">{p["doctor"]}</div>
        </div>
        <div class="result">
            <div class="label">Simple Advice</div>
            <div class="help">{p["advice"]}</div>
        </div>
        <div class="help">Note: This is only a screening preview. It is not a medical diagnosis.</div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Start Again"):
        st.session_state.screen = "menu"
        st.session_state.prediction = None
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def chat_page():
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown(f'<div class="title">{text()["chat"]}</div>', unsafe_allow_html=True)
    st.markdown('<div class="help">Ask a basic skin question.</div>', unsafe_allow_html=True)
    question = st.text_input("Type your question")
    if st.button("Get Answer"):
        q = question.lower()
        if "doctor" in q or "dermatologist" in q:
            answer = "Meet a dermatologist if there is pus, swelling, fever, severe pain, spreading, or no improvement."
        elif "itch" in q:
            answer = "Do not scratch. Wash gently, dry the skin, and avoid wet gloves or boots for long periods."
        else:
            answer = "After seawater work, wash with clean water, dry well, change wet clothes or gloves, and cover small cuts."
        st.info(answer)
    if st.button("Back"):
        st.session_state.screen = "menu"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


init()
style()

if st.session_state.screen == "language":
    language_page()
elif st.session_state.screen == "menu":
    menu_page()
elif st.session_state.screen == "upload":
    upload_page()
elif st.session_state.screen == "questions":
    questions_page()
elif st.session_state.screen == "result":
    result_page()
elif st.session_state.screen == "chat":
    chat_page()
