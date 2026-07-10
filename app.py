import streamlit as st


st.set_page_config(page_title="SkinSense", layout="wide", initial_sidebar_state="collapsed")


OPTIONS = ["Choose one", "Yes", "No", "I don't know", "Maybe"]


DISEASES = {
    "Irritant Contact Dermatitis": {
        "risk": 72,
        "level": "Medium",
        "doctor": "Visit a dermatologist soon if it does not improve or keeps coming back.",
        "advice": [
            "Rinse skin with clean water after fishing work.",
            "Keep the affected area dry when possible.",
            "Use clean dry gloves when handling fish or wet nets.",
        ],
    },
    "Ringworm": {
        "risk": 78,
        "level": "Medium",
        "doctor": "Visit a dermatologist soon because fungal rashes can spread.",
        "advice": [
            "Keep the rash dry.",
            "Do not share towels or gloves.",
            "Avoid scratching the area.",
        ],
    },
    "Athlete's Foot": {
        "risk": 66,
        "level": "Medium",
        "doctor": "Visit a dermatologist if itching, peeling, or cracks continue.",
        "advice": [
            "Dry between your toes after work.",
            "Change wet socks quickly.",
            "Keep boots dry when possible.",
        ],
    },
    "Cellulitis": {
        "risk": 91,
        "level": "High",
        "doctor": "Seek medical help immediately, especially with fever, swelling, heat, pus, or severe pain.",
        "advice": [
            "Do not wait if the area is hot, swollen, or very painful.",
            "Keep the area clean.",
            "Avoid squeezing or scratching the skin.",
        ],
    },
    "Sunburn": {
        "risk": 58,
        "level": "Low",
        "doctor": "Manage at home unless there are blisters, fever, or severe pain.",
        "advice": [
            "Cool the skin with clean water.",
            "Drink water.",
            "Cover skin during strong sun.",
        ],
    },
}


def init_state():
    st.session_state.setdefault("screen", "language")
    st.session_state.setdefault("language", "English")
    st.session_state.setdefault("user_name", "")
    st.session_state.setdefault("uploaded_name", "")
    st.session_state.setdefault("prediction", None)
    st.session_state.setdefault("chat_answer", "")


def app_css():
    st.markdown(
        """
        <style>
        :root {
            --bg: #eef8fb;
            --navy: #071f3d;
            --muted: #5c6f8d;
            --blue: #126fa2;
            --teal: #0d7f8b;
            --deep: #00324a;
            --line: #dbe8f2;
            --soft-line: #c8dde6;
            --card: #ffffff;
            --green: #38a05a;
        }

        .stApp {
            background: var(--bg);
            color: var(--navy);
        }

        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        #MainMenu,
        footer {
            display: none;
        }

        .block-container {
            max-width: 1500px;
            padding: 0 0 60px;
        }

        .topbar {
            height: 78px;
            background: #fff;
            border-bottom: 1px solid var(--line);
            display: flex;
            align-items: center;
            padding: 0 13%;
            gap: 18px;
        }

        .mini-logo {
            width: 58px;
            height: 58px;
            border-radius: 50%;
            background: #0b4f75;
            color: white;
            display: grid;
            place-items: center;
            font-size: 30px;
            font-weight: 900;
        }

        .top-title {
            font-size: 25px;
            line-height: 1.05;
            font-weight: 900;
            color: var(--navy);
        }

        .top-subtitle {
            color: var(--muted);
            font-size: 21px;
            margin-top: 6px;
        }

        .page {
            max-width: 1200px;
            margin: 0 auto;
            padding: 72px 24px 30px;
        }

        .mobile-page {
            max-width: 640px;
            margin: 0 auto;
            padding: 110px 24px 40px;
        }

        .chat-page {
            max-width: 760px;
            margin: 0 auto;
            padding: 170px 24px 40px;
            text-align: center;
        }

        .hero-title {
            font-size: 76px;
            line-height: .92;
            font-weight: 950;
            letter-spacing: -2px;
            color: var(--navy);
            margin: 0 0 26px;
        }

        .hero-subtitle {
            font-size: 31px;
            font-weight: 900;
            color: var(--blue);
            margin-bottom: 28px;
        }

        .name-box-wrap {
            max-width: 520px;
            margin: 0 0 58px;
        }

        .name-label {
            color: var(--muted);
            font-size: 18px;
            font-weight: 900;
            letter-spacing: 4px;
            text-transform: uppercase;
            margin-bottom: 12px;
        }

        .language-label {
            font-size: 20px;
            font-weight: 900;
            color: var(--muted);
            letter-spacing: 6px;
            text-transform: uppercase;
            margin-bottom: 28px;
        }

        .language-card {
            height: 175px;
            border: 1.5px solid var(--line);
            border-radius: 28px;
            background: white;
            padding: 30px;
            box-shadow: 0 12px 30px rgba(7, 31, 61, .05);
            margin-bottom: 14px;
        }

        .language-card .eyebrow {
            color: var(--muted);
            letter-spacing: 6px;
            font-size: 18px;
            font-weight: 900;
            text-transform: uppercase;
            margin-bottom: 12px;
        }

        .language-card .big {
            color: var(--navy);
            font-size: 45px;
            line-height: 1.05;
            font-weight: 950;
            margin-bottom: 20px;
        }

        .continue {
            color: var(--blue);
            font-size: 19px;
            font-weight: 800;
        }

        .disclaimer {
            color: var(--muted);
            font-size: 19px;
            line-height: 1.45;
            max-width: 760px;
            margin-top: 58px;
        }

        .app-header {
            position: fixed;
            top: 22px;
            left: 28px;
            right: 28px;
            display: flex;
            align-items: center;
            gap: 16px;
            z-index: 1;
        }

        .back-circle {
            width: 56px;
            height: 56px;
            border-radius: 50%;
            background: white;
            display: grid;
            place-items: center;
            color: var(--navy);
            font-size: 36px;
            font-weight: 800;
        }

        .brand-row-logo {
            color: #0b8d86;
            font-size: 35px;
            line-height: 1;
        }

        .brand-row-title {
            font-size: 28px;
            font-weight: 950;
            color: var(--navy);
        }

        .screen-title {
            color: var(--navy);
            font-size: 41px;
            line-height: 1.1;
            font-weight: 950;
            text-align: center;
            margin-bottom: 34px;
        }

        .screen-title.left {
            text-align: left;
            margin-bottom: 10px;
        }

        .screen-help {
            color: #486174;
            font-size: 23px;
            line-height: 1.35;
            margin-bottom: 46px;
        }

        .action-card {
            border: 0;
            border-radius: 38px;
            min-height: 300px;
            padding: 52px 42px;
            text-align: center;
            box-shadow: 0 28px 55px rgba(7, 31, 61, .09);
            margin-bottom: 32px;
        }

        .action-card.primary {
            background: linear-gradient(140deg, #002b45 0%, #0a8791 100%);
            color: white;
        }

        .action-card.secondary {
            background: white;
            color: var(--navy);
        }

        .card-icon {
            width: 110px;
            height: 110px;
            border-radius: 50%;
            margin: 0 auto 26px;
            display: grid;
            place-items: center;
            font-size: 58px;
            font-weight: 900;
        }

        .primary .card-icon {
            background: rgba(255,255,255,.22);
            color: white;
        }

        .secondary .card-icon {
            background: #cff6ff;
            color: var(--navy);
        }

        .action-title {
            font-size: 33px;
            font-weight: 950;
            margin-bottom: 18px;
        }

        .action-copy {
            font-size: 23px;
            line-height: 1.35;
            color: rgba(255,255,255,.86);
        }

        .secondary .action-copy {
            color: #486174;
        }

        .upload-option {
            border-radius: 38px;
            min-height: 230px;
            display: grid;
            place-items: center;
            text-align: center;
            padding: 30px;
            margin-bottom: 24px;
            box-shadow: 0 28px 55px rgba(7, 31, 61, .09);
        }

        .upload-option.primary {
            background: linear-gradient(140deg, #002b45 0%, #0a8791 100%);
            color: white;
        }

        .upload-option.secondary {
            background: white;
            color: var(--navy);
        }

        .upload-icon {
            font-size: 55px;
            margin-bottom: 18px;
            line-height: 1;
        }

        .upload-label {
            font-size: 29px;
            font-weight: 950;
        }

        .preview-frame {
            border-radius: 36px;
            overflow: hidden;
            background: white;
            box-shadow: 0 20px 50px rgba(7, 31, 61, .10);
            margin-bottom: 26px;
        }

        .question-wrap {
            max-width: 620px;
            margin: 0 auto;
            padding: 70px 0 20px;
        }

        .question-title {
            font-size: 37px;
            font-weight: 950;
            color: var(--navy);
            margin-bottom: 16px;
        }

        .question-subtitle {
            color: #486174;
            font-size: 21px;
            margin-bottom: 78px;
        }

        .q-block {
            border-bottom: 1.5px solid var(--soft-line);
            padding: 0 0 34px;
            margin-bottom: 40px;
        }

        .q-text {
            color: var(--navy);
            font-size: 25px;
            line-height: 1.35;
            font-weight: 950;
            margin-bottom: 28px;
        }

        .answer-label {
            color: #486174;
            font-size: 20px;
            font-weight: 900;
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-bottom: 58px;
        }

        .result-wrap {
            max-width: 620px;
            margin: 0 auto;
            padding: 28px 0 40px;
        }

        .result-kicker {
            text-align: center;
            color: #486174;
            font-size: 20px;
            font-weight: 900;
            letter-spacing: 4px;
            text-transform: uppercase;
            margin-bottom: 34px;
        }

        .condition-card {
            background: linear-gradient(145deg, #14364f 0%, #031a32 100%);
            color: white;
            border-radius: 38px;
            padding: 42px;
            margin-bottom: 30px;
        }

        .condition-label {
            color: rgba(255,255,255,.78);
            font-size: 18px;
            letter-spacing: 3px;
            text-transform: uppercase;
            font-weight: 900;
            margin-bottom: 16px;
        }

        .condition-title {
            font-size: 39px;
            line-height: 1.18;
            font-weight: 950;
            margin-bottom: 24px;
        }

        .condition-copy {
            font-size: 23px;
            line-height: 1.45;
            color: rgba(255,255,255,.93);
        }

        .risk-card,
        .todo-card {
            background: white;
            border-radius: 38px;
            padding: 36px;
            box-shadow: 0 20px 45px rgba(7, 31, 61, .06);
            margin-bottom: 30px;
        }

        .risk-row {
            display: flex;
            align-items: center;
            gap: 18px;
            margin: 20px 0 26px;
        }

        .risk-pill {
            border-radius: 28px;
            background: var(--green);
            color: white;
            padding: 14px 28px;
            font-size: 25px;
            font-weight: 950;
        }

        .risk-percent {
            color: var(--navy);
            font-size: 36px;
            font-weight: 950;
        }

        .risk-bar {
            height: 16px;
            border-radius: 999px;
            background: #c9f5ff;
            overflow: hidden;
            margin-bottom: 14px;
        }

        .risk-fill {
            height: 100%;
            border-radius: 999px;
            background: var(--green);
        }

        .doctor-card {
            background: var(--green);
            color: white;
            border-radius: 38px;
            padding: 34px 38px;
            display: flex;
            gap: 22px;
            align-items: flex-start;
            margin-bottom: 30px;
        }

        .check-icon {
            width: 34px;
            height: 34px;
            border: 3px solid white;
            border-radius: 50%;
            display: grid;
            place-items: center;
            flex: 0 0 auto;
            font-weight: 900;
        }

        .doctor-title,
        .todo-title {
            font-size: 20px;
            letter-spacing: 2px;
            text-transform: uppercase;
            font-weight: 950;
            margin-bottom: 12px;
        }

        .doctor-copy {
            font-size: 26px;
            line-height: 1.48;
            font-weight: 900;
        }

        .todo-title {
            color: #486174;
        }

        .todo-item {
            display: flex;
            gap: 16px;
            color: var(--navy);
            font-size: 24px;
            line-height: 1.35;
            margin: 18px 0;
        }

        .green-check {
            color: var(--green);
            font-weight: 950;
        }

        .note {
            text-align: center;
            color: #486174;
            font-size: 20px;
            line-height: 1.35;
            margin-bottom: 28px;
        }

        .chat-logo {
            color: #0b8d86;
            font-size: 84px;
            line-height: 1;
            margin-bottom: 54px;
        }

        .chat-heading {
            color: var(--navy);
            font-size: 29px;
            line-height: 1.35;
            font-weight: 900;
            max-width: 760px;
            margin: 0 auto 42px;
        }

        .prompt-card {
            background: white;
            border-radius: 34px;
            padding: 28px;
            color: var(--navy);
            font-size: 25px;
            font-weight: 900;
            margin: 18px auto;
            box-shadow: 0 20px 45px rgba(7, 31, 61, .05);
            max-width: 700px;
        }

        .chat-input-space {
            margin-top: 250px;
        }

        div.stButton > button {
            min-height: 62px;
            border-radius: 999px;
            border: 0;
            background: linear-gradient(140deg, #00324a 0%, #0a8791 100%);
            color: white;
            font-size: 25px;
            font-weight: 950;
            box-shadow: 0 18px 35px rgba(7, 31, 61, .08);
        }

        div.stButton > button:hover {
            color: white;
            border: 0;
            filter: brightness(.98);
        }

        div[data-testid="stFileUploader"] {
            background: white;
            border-radius: 28px;
            padding: 24px;
            border: 1.5px dashed var(--soft-line);
            margin-bottom: 24px;
        }

        div[data-baseweb="select"] > div {
            min-height: 62px;
            border-radius: 28px;
            border: 3px solid var(--soft-line);
            background: transparent;
            color: var(--navy);
            font-size: 22px;
            font-weight: 900;
        }

        label {
            color: var(--navy) !important;
            font-size: 18px !important;
            font-weight: 900 !important;
        }

        .stTextInput input {
            min-height: 74px;
            border-radius: 18px;
            border: 2px solid var(--soft-line);
            font-size: 22px;
        }

        .name-box-wrap .stTextInput input {
            border-radius: 28px;
            background: white;
            border: 2px solid var(--line);
            box-shadow: 0 12px 30px rgba(7, 31, 61, .05);
            color: var(--navy);
            font-size: 22px;
            font-weight: 800;
        }

        @media (max-width: 900px) {
            .topbar { padding: 0 24px; }
            .hero-title { font-size: 54px; }
            .hero-subtitle { font-size: 25px; margin-bottom: 54px; }
            .language-card { height: auto; }
            .mobile-page { padding-top: 95px; }
            .chat-page { padding-top: 130px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def topbar():
    st.markdown(
        """
        <div class="topbar">
            <div class="mini-logo">✋</div>
            <div>
                <div class="top-title">SkinSense</div>
                <div class="top-subtitle">Coastal Skin Care Workspace</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def app_header(title="SkinSense", back_target="menu"):
    st.markdown(
        f"""
        <div class="app-header">
            <div class="back-circle">←</div>
            <div class="brand-row-logo">✋</div>
            <div class="brand-row-title">{title}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def language_page():
    topbar()
    st.markdown(
        """
        <div class="page">
            <div class="hero-title">SkinSense</div>
            <div class="hero-subtitle">AI Skin Screening for Fishing Communities</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="page" style="padding-top:0;padding-bottom:0;">', unsafe_allow_html=True)
    st.markdown('<div class="name-box-wrap"><div class="name-label">Your Name</div>', unsafe_allow_html=True)
    st.session_state.user_name = st.text_input(
        "Your Name",
        value=st.session_state.user_name,
        placeholder="Type your name here",
        label_visibility="collapsed",
    )
    st.markdown("</div></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class="page" style="padding-top:0;">
            <div class="language-label">भाषा निवडा · भाषा चुनें · Choose your language</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cols = st.columns(3)
    languages = [
        ("Marathi", "MARATHI", "मराठी"),
        ("Hindi", "HINDI", "हिंदी"),
        ("English", "ENGLISH", "English"),
    ]
    for col, (key, eyebrow, big) in zip(cols, languages):
        with col:
            st.markdown(
                f"""
                <div class="language-card">
                    <div class="eyebrow">{eyebrow}</div>
                    <div class="big">{big}</div>
                    <div class="continue">Continue →</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(f"Continue {key}", key=f"language-{key}"):
                st.session_state.language = key
                st.session_state.screen = "menu"
                st.rerun()
    st.markdown(
        """
        <div class="page" style="padding-top:20px;">
            <div class="disclaimer">
                SkinSense is a screening aid, not a medical diagnosis. For serious or worsening symptoms, please<br>
                visit a dermatologist.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def menu_page():
    app_header("SkinSense", "language")
    st.markdown('<div class="mobile-page">', unsafe_allow_html=True)
    st.markdown('<div class="screen-title">What would you like to do?</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="action-card primary">
            <div class="card-icon">📷</div>
            <div class="action-title">Check my skin</div>
            <div class="action-copy">Take a photo of the skin problem and get a quick check</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Check my skin", key="go-check"):
        st.session_state.screen = "upload"
        st.rerun()
    st.markdown(
        """
        <div class="action-card secondary">
            <div class="card-icon">?</div>
            <div class="action-title">Ask a question</div>
            <div class="action-copy">Chat and ask simple questions about skin care</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Ask a question", key="go-chat"):
        st.session_state.screen = "chat"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def upload_page():
    app_header("SkinSense", "menu")
    st.markdown('<div class="mobile-page">', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="screen-title left">Show us the skin problem</div>
        <div class="screen-help">Take a clear photo in good light, close to the skin</div>
        <div class="upload-option primary">
            <div>
                <div class="upload-icon">📷</div>
                <div class="upload-label">Take a photo</div>
            </div>
        </div>
        <div class="upload-option secondary">
            <div>
                <div class="upload-icon">▧</div>
                <div class="upload-label">Choose from gallery</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    image = st.file_uploader("Choose from gallery", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
    if image:
        st.session_state.uploaded_name = image.name
        st.markdown('<div class="preview-frame">', unsafe_allow_html=True)
        st.image(image, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        if st.button("Continue →", key="continue-after-upload"):
            st.session_state.screen = "questions"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def questions_page():
    app_header("SkinSense", "upload")
    st.markdown('<div class="question-wrap">', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="question-title">A few simple questions</div>
        <div class="question-subtitle">Write a short answer and pick one option for each question.</div>
        """,
        unsafe_allow_html=True,
    )
    questions = [
        "Q1. Does the skin problem itch, burn or hurt?",
        "Q2. Is it spreading or getting bigger?",
        "Q3. Are your hands or feet in sea water for many hours every day?",
        "Q4. Have you had this problem for more than 2 weeks?",
        "Q5. Do you see pus, bleeding, or a bad smell?",
    ]
    answers = {}
    for i, question in enumerate(questions, 1):
        st.markdown(
            f"""
            <div class="q-block">
                <div class="q-text">{question}</div>
                <div class="answer-label">Your answer</div>
            """,
            unsafe_allow_html=True,
        )
        answers[question] = st.selectbox("Choose one", OPTIONS, key=f"q-{i}", label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)
    if st.button("See result →", key="see-result"):
        st.session_state.prediction = predict(answers)
        st.session_state.screen = "result"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def predict(answers):
    yes = {key: value == "Yes" for key, value in answers.items()}
    if yes["Q5. Do you see pus, bleeding, or a bad smell?"] and yes["Q1. Does the skin problem itch, burn or hurt?"]:
        name = "Cellulitis"
    elif yes["Q2. Is it spreading or getting bigger?"]:
        name = "Ringworm"
    elif yes["Q3. Are your hands or feet in sea water for many hours every day?"]:
        name = "Irritant Contact Dermatitis"
    elif yes["Q4. Have you had this problem for more than 2 weeks?"]:
        name = "Athlete's Foot"
    else:
        name = "Sunburn"

    result = DISEASES[name].copy()
    result["name"] = name
    maybe_count = sum(value == "Maybe" for value in answers.values())
    yes_count = sum(yes.values())
    result["risk"] = min(result["risk"] + yes_count * 2 + maybe_count, 96)
    if result["risk"] >= 80:
        result["level"] = "High"
    elif result["risk"] >= 60:
        result["level"] = "Medium"
    else:
        result["level"] = "Low"
    return result


def result_page():
    app_header("SkinSense", "questions")
    prediction = st.session_state.prediction or {
        "name": "I could not see a skin problem in this photo.",
        "risk": 0,
        "level": "Low",
        "doctor": "Only if you have a skin concern and can take a clear photo of it.",
        "advice": [
            "Please take a clear, close-up photo of the affected skin area.",
            "Make sure there is plenty of light when you take the photo.",
            "Keep the skin area clean and dry until you can show it to a doctor.",
        ],
    }
    fill = max(prediction["risk"], 4)
    st.markdown('<div class="result-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="result-kicker">Your Result</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="condition-card">
            <div class="condition-label">Possible Condition</div>
            <div class="condition-title">{prediction["name"]}</div>
            <div class="condition-copy">This is an early screening result based on the photo and your answers.</div>
        </div>
        <div class="risk-card">
            <div class="condition-label" style="color:#486174;">Risk Level</div>
            <div class="risk-row">
                <div class="risk-pill">{prediction["level"]}</div>
                <div class="risk-percent">{prediction["risk"]}%</div>
            </div>
            <div class="risk-bar"><div class="risk-fill" style="width:{fill}%;"></div></div>
            <div class="condition-label" style="color:#486174;">Risk Score</div>
        </div>
        <div class="doctor-card">
            <div class="check-icon">✓</div>
            <div>
                <div class="doctor-title">When to see a dermatologist</div>
                <div class="doctor-copy">{prediction["doctor"]}</div>
            </div>
        </div>
        <div class="todo-card">
            <div class="todo-title">What you can do</div>
        """,
        unsafe_allow_html=True,
    )
    for item in prediction["advice"]:
        st.markdown(f'<div class="todo-item"><span class="green-check">✓</span><span>{item}</span></div>', unsafe_allow_html=True)
    st.markdown(
        """
        </div>
        <div class="note">This is not a medical diagnosis. It is only a guide. If it gets worse, please see a doctor.</div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Check another", key="check-another"):
        st.session_state.screen = "upload"
        st.session_state.prediction = None
        st.rerun()
    if st.button("Home", key="home"):
        st.session_state.screen = "menu"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def chat_page():
    app_header("Ask about skin care", "menu")
    st.markdown('<div class="chat-page">', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="chat-logo">✋</div>
        <div class="chat-heading">Hello! Ask me anything about skin problems from<br>sea water, sun, or fishing work.</div>
        """,
        unsafe_allow_html=True,
    )
    prompts = [
        "My hands itch after fishing",
        "How to protect skin from salt water?",
        "White patches between my toes",
    ]
    for prompt in prompts:
        st.markdown(f'<div class="prompt-card">{prompt}</div>', unsafe_allow_html=True)
        if st.button(prompt, key=f"prompt-{prompt}"):
            st.session_state.chat_answer = chat_answer(prompt)
            st.rerun()
    st.markdown('<div class="chat-input-space"></div>', unsafe_allow_html=True)
    question = st.text_input("Type your question...", label_visibility="collapsed", placeholder="Type your question...")
    if st.button("↵", key="send-chat"):
        st.session_state.chat_answer = chat_answer(question)
        st.rerun()
    if st.session_state.chat_answer:
        st.info(st.session_state.chat_answer)
    if st.button("Home", key="chat-home"):
        st.session_state.screen = "menu"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def chat_answer(question):
    q = question.lower()
    if "toe" in q or "white" in q:
        return "White patches between toes can happen when feet stay wet. Dry between toes and see a dermatologist if it spreads."
    if "salt" in q or "water" in q:
        return "Rinse with clean water after work, dry well, change wet gloves or boots, and cover small cuts."
    if "itch" in q:
        return "Do not scratch. Wash gently, dry the skin, and avoid wet gloves for long periods."
    return "Keep the skin clean and dry. See a dermatologist if there is pain, pus, swelling, fever, or spreading."


init_state()
app_css()

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
