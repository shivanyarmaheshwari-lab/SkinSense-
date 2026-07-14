from __future__ import annotations

import json
import logging
import math
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import base64
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
import streamlit.components.v1 as components
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
LOGO_PATH = BASE_DIR / "skinsense_logo.png"

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
VALID_PAGES = {"start", "care_choice", "dermatologist", "upload", "questions", "result"}


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
        "privacy": "Privacy: SkinSense only uses your uploaded photo during this session to create a screening result. Skin photos are not saved to Google Sheets. Your name and time of entry may be saved for basic usage tracking. Please avoid uploading photos that show your face, private body areas, Aadhaar, phone number, or other personal details.",
        "choice_title": "What would you like to do?",
        "choice_help": "Choose skin screening or find affordable skin care near you.",
        "check_skin": "Check my skin",
        "check_skin_help": "Upload or take a photo and answer a few questions.",
        "find_dermatologist": "Find a dermatologist near me",
        "find_dermatologist_help": "Search public clinics, government hospitals, and lower-cost skin care.",
        "derm_title": "Find affordable skin care nearby",
        "derm_help": "Enter your area, village, city, or a nearby landmark. SkinSense will show affordable skin care options around that place.",
        "location_label": "Your area, city, village, or landmark",
        "location_placeholder": "Example: Versova, Mumbai",
        "use_current_location": "Use my current location in Google Maps",
        "government_hospitals": "Government hospitals",
        "public_clinics": "Public health clinics",
        "low_cost_derm": "Lower-cost dermatologists",
        "open_maps": "Open in Google Maps",
        "map_note": "Call before visiting to confirm dermatologist availability, cost, timing, and required documents.",
        "nearby_results": "Nearby options from your typed location",
        "exact_location_map": "Nearby skin care map",
        "top_places": "Top 5 closest care options",
        "address": "Address",
        "contact": "Contact",
        "place_type": "Type",
        "address_not_listed": "Address not listed. Open Google Maps to view details.",
        "contact_not_listed": "Contact not listed",
        "distance": "Distance",
        "no_nearby_places": "Skin-specific public records were limited here, so these are the closest health-care options. Open Google Maps to confirm dermatology services.",
        "location_not_found": "I could not find that exact location. Please type a more complete address or landmark.",
        "back_options": "Back to options",
        "check_skin_instead": "Check skin instead",
        "find_derm_instead": "Find dermatologist instead",
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
        "privacy": "Privacy: SkinSense आपकी फोटो का उपयोग केवल इसी session में screening result बनाने के लिए करता है. Skin photos Google Sheets में save नहीं होतीं. आपका नाम और entry time basic usage tracking के लिए save हो सकता है. कृपया face, private body areas, Aadhaar, phone number, या personal details वाली photo upload न करें.",
        "choice_title": "आप क्या करना चाहेंगे?",
        "choice_help": "त्वचा स्क्रीनिंग करें या अपने पास सस्ती त्वचा देखभाल खोजें.",
        "check_skin": "मेरी त्वचा जांचें",
        "check_skin_help": "फोटो अपलोड/खींचें और कुछ सवालों के जवाब दें.",
        "find_dermatologist": "मेरे पास त्वचा डॉक्टर खोजें",
        "find_dermatologist_help": "सरकारी अस्पताल, public clinic और कम खर्च वाली skin care खोजें.",
        "derm_title": "पास में सस्ती त्वचा देखभाल खोजें",
        "derm_help": "अपना area, गांव, शहर या पास का landmark लिखें. SkinSense उस जगह के आसपास affordable skin care options दिखाएगा.",
        "location_label": "आपका area, शहर, गांव या landmark",
        "location_placeholder": "उदाहरण: Versova, Mumbai",
        "use_current_location": "Google Maps में मेरी current location इस्तेमाल करें",
        "government_hospitals": "सरकारी अस्पताल",
        "public_clinics": "Public health clinics",
        "low_cost_derm": "कम खर्च वाले dermatologists",
        "open_maps": "Google Maps में खोलें",
        "map_note": "जाने से पहले phone करके dermatologist availability, cost, timing और documents confirm करें.",
        "nearby_results": "आपके लिखे हुए location के पास के options",
        "exact_location_map": "पास के skin care का map",
        "top_places": "सबसे पास के 5 care options",
        "address": "पता",
        "contact": "Contact",
        "place_type": "Type",
        "address_not_listed": "पता listed नहीं है. Details देखने के लिए Google Maps खोलें.",
        "contact_not_listed": "Contact listed नहीं है",
        "distance": "दूरी",
        "no_nearby_places": "यहां skin-specific public records कम मिले, इसलिए ये सबसे पास के health-care options हैं. Dermatology services confirm करने के लिए Google Maps खोलें.",
        "location_not_found": "यह exact location नहीं मिली. कृपया पूरा address या landmark लिखें.",
        "back_options": "Options पर वापस जाएं",
        "check_skin_instead": "इसके बजाय त्वचा जांचें",
        "find_derm_instead": "इसके बजाय डॉक्टर खोजें",
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
        "privacy": "Privacy: SkinSense तुमचा फोटो फक्त या session मध्ये screening result बनवण्यासाठी वापरतो. Skin photos Google Sheets मध्ये save होत नाहीत. तुमचे नाव आणि entry time basic usage tracking साठी save होऊ शकते. कृपया face, private body areas, Aadhaar, phone number किंवा personal details असलेला फोटो upload करू नका.",
        "choice_title": "तुम्हाला काय करायचे आहे?",
        "choice_help": "त्वचा स्क्रीनिंग करा किंवा जवळची परवडणारी त्वचा सेवा शोधा.",
        "check_skin": "माझी त्वचा तपासा",
        "check_skin_help": "फोटो upload/घ्या आणि काही प्रश्नांची उत्तरे द्या.",
        "find_dermatologist": "जवळचा त्वचा डॉक्टर शोधा",
        "find_dermatologist_help": "सरकारी रुग्णालये, public clinics आणि कमी खर्चाची skin care शोधा.",
        "derm_title": "जवळची परवडणारी त्वचा सेवा शोधा",
        "derm_help": "तुमचा area, गाव, शहर किंवा जवळचा landmark लिहा. SkinSense त्या जागेजवळ affordable skin care options दाखवेल.",
        "location_label": "तुमचा area, शहर, गाव किंवा landmark",
        "location_placeholder": "उदाहरण: Versova, Mumbai",
        "use_current_location": "Google Maps मध्ये माझी current location वापरा",
        "government_hospitals": "सरकारी रुग्णालये",
        "public_clinics": "Public health clinics",
        "low_cost_derm": "कमी खर्चाचे dermatologists",
        "open_maps": "Google Maps मध्ये उघडा",
        "map_note": "जाण्यापूर्वी phone करून dermatologist availability, cost, timing आणि documents confirm करा.",
        "nearby_results": "तुम्ही लिहिलेल्या location जवळचे options",
        "exact_location_map": "जवळच्या skin care चा map",
        "top_places": "सर्वात जवळचे 5 care options",
        "address": "पत्ता",
        "contact": "Contact",
        "place_type": "Type",
        "address_not_listed": "पत्ता listed नाही. Details पाहण्यासाठी Google Maps उघडा.",
        "contact_not_listed": "Contact listed नाही",
        "distance": "अंतर",
        "no_nearby_places": "इथे skin-specific public records कमी मिळाले, म्हणून हे सर्वात जवळचे health-care options आहेत. Dermatology services confirm करण्यासाठी Google Maps उघडा.",
        "location_not_found": "हे exact location सापडले नाही. कृपया पूर्ण address किंवा landmark लिहा.",
        "back_options": "Options कडे परत जा",
        "check_skin_instead": "त्याऐवजी त्वचा तपासा",
        "find_derm_instead": "त्याऐवजी डॉक्टर शोधा",
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


SEVERITY_GUIDANCE = {
    "Irritant Contact Dermatitis": {
        "mild": {
            "do": "Rinse the area with clean water, pat dry, and apply a plain moisturiser after fishing work.",
            "avoid": "Avoid strong soaps, detergents, seawater staying on the skin, and scratching.",
            "derm": "See a dermatologist if it does not improve in a few days.",
        },
        "moderate": {
            "do": "Keep the area dry between work hours and moisturise several times a day.",
            "avoid": "Avoid repeated wet work without drying the skin and avoid perfumed creams.",
            "derm": "See a dermatologist if redness, cracks, or burning continues for more than a week.",
        },
        "serious": {
            "do": "Cover cracked areas lightly and reduce contact with seawater or irritants when possible.",
            "avoid": "Avoid rubbing, harsh home remedies, and working with open cracks exposed.",
            "derm": "Book a dermatologist visit soon, especially if the skin is painful or bleeding.",
        },
        "urgent": {
            "do": "Keep the skin clean and covered until a doctor checks it.",
            "avoid": "Avoid scratching, squeezing, or applying unknown creams.",
            "derm": "Seek medical care quickly if there is pus, swelling, fever, or spreading redness.",
        },
    },
    "Occupational Hand Eczema": {
        "mild": {
            "do": "Moisturise hands after washing and after seawater work.",
            "avoid": "Avoid frequent washing with harsh soap and avoid leaving hands wet.",
            "derm": "See a dermatologist if it keeps coming back.",
        },
        "moderate": {
            "do": "Use a thick moisturiser before sleep and dry hands carefully after work.",
            "avoid": "Avoid wet gloves for long periods and avoid scratching.",
            "derm": "See a dermatologist if cracks, itching, or burning lasts more than a week.",
        },
        "serious": {
            "do": "Protect open cracks and reduce direct irritant contact as much as possible.",
            "avoid": "Avoid detergent, fish fluids, and seawater on broken skin.",
            "derm": "Book a dermatologist visit soon if there is bleeding, pain, or repeated flare-ups.",
        },
        "urgent": {
            "do": "Keep painful cracks clean and covered.",
            "avoid": "Avoid continuing work with open infected-looking skin.",
            "derm": "Seek medical care quickly if pus, warmth, swelling, or fever appears.",
        },
    },
    "Athlete's Foot (Tinea pedis)": {
        "mild": {
            "do": "Wash feet, dry between toes, and change wet socks or footwear.",
            "avoid": "Avoid staying in damp shoes for long hours.",
            "derm": "See a dermatologist if it does not improve or spreads.",
        },
        "moderate": {
            "do": "Keep feet dry and use clean, dry footwear whenever possible.",
            "avoid": "Avoid sharing towels and avoid scratching between toes.",
            "derm": "See a dermatologist if peeling, itching, or cracks continue.",
        },
        "serious": {
            "do": "Keep cracked areas clean and dry, and avoid walking barefoot in shared wet areas.",
            "avoid": "Avoid wet closed shoes and avoid applying steroid creams without advice.",
            "derm": "Book a dermatologist visit soon if cracks are painful or spreading.",
        },
        "urgent": {
            "do": "Cover open cracks and keep the foot clean.",
            "avoid": "Avoid seawater or dirty water touching broken skin.",
            "derm": "Seek care quickly if there is swelling, pus, redness spreading up the foot, or fever.",
        },
    },
    "Ringworm (Tinea corporis)": {
        "mild": {
            "do": "Keep the patch dry and use separate towels.",
            "avoid": "Avoid scratching and avoid sharing clothes or towels.",
            "derm": "See a dermatologist if it spreads.",
        },
        "moderate": {
            "do": "Keep the area clean, dry, and covered loosely if it rubs on clothing.",
            "avoid": "Avoid tight wet clothing and avoid steroid creams unless prescribed.",
            "derm": "See a dermatologist if the ring grows or new patches appear.",
        },
        "serious": {
            "do": "Wash clothes and towels regularly and keep the area dry.",
            "avoid": "Avoid close skin contact that may spread it to others.",
            "derm": "Book a dermatologist visit soon if it is spreading quickly or covers many areas.",
        },
        "urgent": {
            "do": "Keep the area covered and avoid spreading it to others.",
            "avoid": "Avoid home mixtures or unknown creams on irritated skin.",
            "derm": "Seek medical care quickly if there is pus, severe pain, fever, or major swelling.",
        },
    },
    "Cutaneous Candidiasis": {
        "mild": {
            "do": "Keep skin folds dry and change out of wet clothes quickly.",
            "avoid": "Avoid tight damp clothing.",
            "derm": "See a dermatologist if it keeps returning.",
        },
        "moderate": {
            "do": "Dry the area gently and wear loose, breathable clothing.",
            "avoid": "Avoid friction, scratching, and perfumed products.",
            "derm": "See a dermatologist if redness or soreness lasts more than a few days.",
        },
        "serious": {
            "do": "Keep the area clean and reduce moisture as much as possible.",
            "avoid": "Avoid working in wet clothes for long periods.",
            "derm": "Book a dermatologist visit soon if the rash is painful or spreading.",
        },
        "urgent": {
            "do": "Keep the area clean, dry, and covered loosely.",
            "avoid": "Avoid scratching or applying unknown creams.",
            "derm": "Seek medical care quickly if there is pus, fever, severe pain, or fast spreading redness.",
        },
    },
    "Paronychia": {
        "mild": {
            "do": "Keep the nail area clean and dry after work.",
            "avoid": "Avoid biting nails or cutting nails too short.",
            "derm": "See a dermatologist if swelling increases.",
        },
        "moderate": {
            "do": "Protect the finger or toe from seawater and friction.",
            "avoid": "Avoid squeezing the nail fold.",
            "derm": "See a dermatologist if pain or swelling lasts more than two days.",
        },
        "serious": {
            "do": "Keep the nail area covered with clean dressing.",
            "avoid": "Avoid draining pus yourself.",
            "derm": "Book a dermatologist or doctor visit soon if there is pus or strong pain.",
        },
        "urgent": {
            "do": "Keep the finger or toe clean and protected.",
            "avoid": "Avoid squeezing, cutting, or poking the swollen area.",
            "derm": "Seek urgent care if swelling spreads, pain is severe, or fever appears.",
        },
    },
    "Folliculitis": {
        "mild": {
            "do": "Keep the area clean and avoid friction.",
            "avoid": "Avoid scratching or picking bumps.",
            "derm": "See a dermatologist if it spreads.",
        },
        "moderate": {
            "do": "Wash gently and wear loose clothing over the area.",
            "avoid": "Avoid shaving, rubbing, or tight wet clothing over the bumps.",
            "derm": "See a dermatologist if bumps become painful or filled with pus.",
        },
        "serious": {
            "do": "Keep the area clean and covered if bumps are open.",
            "avoid": "Avoid squeezing or popping bumps.",
            "derm": "Book a dermatologist visit soon if many bumps appear or pain increases.",
        },
        "urgent": {
            "do": "Keep the area clean and do not touch it repeatedly.",
            "avoid": "Avoid dirty water, scratching, and squeezing.",
            "derm": "Seek medical care quickly if there is fever, spreading redness, or severe swelling.",
        },
    },
    "Cellulitis": {
        "mild": {
            "do": "Mark the edge of redness and monitor if it spreads.",
            "avoid": "Avoid scratching or rubbing the area.",
            "derm": "Cellulitis can become serious, so see a doctor if redness grows.",
        },
        "moderate": {
            "do": "Keep the area raised if swollen and keep skin clean.",
            "avoid": "Avoid seawater or dirty water touching broken skin.",
            "derm": "See a doctor or dermatologist soon.",
        },
        "serious": {
            "do": "Get medical advice quickly and monitor fever, pain, and spreading redness.",
            "avoid": "Avoid delaying care or treating it only with home remedies.",
            "derm": "See a doctor urgently, especially if skin is warm, painful, or spreading.",
        },
        "urgent": {
            "do": "Go for medical care as soon as possible.",
            "avoid": "Avoid waiting, squeezing, massaging, or applying unknown creams.",
            "derm": "Urgent care is needed if there is fever, severe pain, fast spreading redness, or swelling.",
        },
    },
    "Impetigo": {
        "mild": {
            "do": "Keep sores clean and wash hands after touching the area.",
            "avoid": "Avoid sharing towels or touching other people with the affected area.",
            "derm": "See a dermatologist if sores spread.",
        },
        "moderate": {
            "do": "Cover the area lightly and keep nails short.",
            "avoid": "Avoid scratching crusts or sharing bedding/towels.",
            "derm": "See a dermatologist soon because it can spread to others.",
        },
        "serious": {
            "do": "Keep sores covered and reduce close contact until checked.",
            "avoid": "Avoid picking yellow crusts or letting fluid touch others.",
            "derm": "Book a dermatologist or doctor visit soon.",
        },
        "urgent": {
            "do": "Seek care quickly and keep the area covered.",
            "avoid": "Avoid school/work close contact if sores are leaking.",
            "derm": "Urgent care is needed if fever, swelling, pain, or rapid spread appears.",
        },
    },
    "Sunburn": {
        "mild": {
            "do": "Cool the skin with clean cool water and drink fluids.",
            "avoid": "Avoid more sun exposure on the area.",
            "derm": "See a doctor if pain becomes severe.",
        },
        "moderate": {
            "do": "Use cool compresses and protect the area from sun.",
            "avoid": "Avoid popping blisters or applying harsh products.",
            "derm": "See a doctor if blistering or strong pain appears.",
        },
        "serious": {
            "do": "Rest, hydrate, and protect the burned skin.",
            "avoid": "Avoid sun, heat, and breaking blisters.",
            "derm": "See a doctor soon if there are large blisters, chills, or dizziness.",
        },
        "urgent": {
            "do": "Get medical help quickly if you feel very unwell.",
            "avoid": "Avoid returning to sun or ignoring dehydration symptoms.",
            "derm": "Urgent care is needed for fever, confusion, severe pain, dehydration, or widespread blistering.",
        },
    },
    "Actinic Keratosis": {
        "mild": {
            "do": "Protect the patch from sun and watch for changes.",
            "avoid": "Avoid picking or scraping the rough patch.",
            "derm": "Book a dermatologist check when possible.",
        },
        "moderate": {
            "do": "Use sun protection daily and photograph the patch to monitor changes.",
            "avoid": "Avoid repeated direct sun on the area.",
            "derm": "See a dermatologist soon for confirmation.",
        },
        "serious": {
            "do": "Keep the area protected and note any bleeding, pain, or growth.",
            "avoid": "Avoid delaying assessment if the patch changes.",
            "derm": "Book a dermatologist visit soon.",
        },
        "urgent": {
            "do": "Arrange medical review quickly if it bleeds, grows, or becomes painful.",
            "avoid": "Avoid ignoring a changing sun-damaged patch.",
            "derm": "Seek prompt dermatologist care for rapid growth, bleeding, or a non-healing sore.",
        },
    },
}


@dataclass
class Prediction:
    condition: str
    image_confidence: float
    final_score: float
    accuracy_percentage: int
    severity_percentage: int
    severity_band: str
    top_predictions: list[tuple[str, float]]
    what_to_do: str
    what_to_avoid: str
    dermatologist: str
    explanation: str


def css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #edf8fc;
            --navy: #071f3d;
            --blue: #1d6fd6;
            --blue-soft: #e8f2ff;
            --deep-blue: #0f4f9f;
            --muted: #50647a;
            --line: #c9dceb;
            --soft-blue: #e8f2ff;
            --white: #ffffff;
            --green-soft: #d7fae8;
            --yellow-soft: #fff8bf;
        }
        .stApp { background: var(--bg); }
        .block-container {
            max-width: 1120px;
            padding-top: 1.25rem;
            padding-bottom: 3rem;
        }
        h1, h2, h3 { color: var(--navy) !important; }
        h1 {
            font-size: 2.45rem;
            line-height: 1.12;
            margin-bottom: .7rem;
            letter-spacing: 0;
            text-align: center;
        }
        h2 { font-size: 1.75rem; }
        h3 { font-size: 1.15rem; }
        .topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 14px;
            padding: 0 0 14px 0;
            margin-bottom: 26px;
            border-bottom: 1px solid var(--line);
        }
        .brand-left {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .brand-icon {
            width: 44px;
            height: 44px;
            border-radius: 50%;
            background: #ffffff;
            display: flex;
            align-items: center;
            justify-content: center;
            flex: 0 0 auto;
            overflow: hidden;
            border: 1px solid var(--line);
        }
        .brand-icon img { width: 100%; height: 100%; object-fit: cover; }
        .brand-name {
            color: var(--navy) !important;
            font-size: 1rem;
            font-weight: 900;
            line-height: 1.1;
        }
        .brand-subtitle {
            color: var(--muted);
            font-size: .9rem;
            font-weight: 500;
            margin-top: 4px;
        }
        .language-pill {
            color: var(--muted);
            font-size: .92rem;
            font-weight: 700;
            white-space: nowrap;
        }
        .lead-blue {
            color: var(--muted);
            font-size: 1.08rem;
            font-weight: 650;
            margin-bottom: .8rem;
            text-align: center;
        }
        .body-copy {
            color: var(--muted);
            font-size: 1rem;
            line-height: 1.45;
            margin: 0 auto 1.6rem auto;
            text-align: center;
            max-width: 640px;
        }
        .block-container,
        .block-container p,
        .block-container span,
        .block-container label,
        .stMarkdown,
        .stMarkdown p,
        .stCaptionContainer,
        .stAlert,
        .stAlert p,
        .stAlert span {
            color: var(--navy) !important;
        }
        .disclaimer-box {
            background: var(--soft-blue);
            color: var(--navy);
            border: 1px solid var(--line);
            border-radius: 10px;
            padding: 14px 18px;
            font-size: .92rem;
            line-height: 1.5;
            margin-top: 20px;
        }
        .privacy-box {
            background: #ffffff;
            color: var(--navy);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 18px 22px;
            font-size: .95rem;
            line-height: 1.5;
            margin-top: 18px;
        }
        .result-panel {
            background: var(--white);
            border: 1px solid var(--line);
            border-radius: 10px;
            padding: 20px;
            margin: 12px 0;
            box-shadow: 0 8px 22px rgba(7, 31, 61, 0.04);
        }
        .result-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 16px;
            margin-top: 18px;
        }
        .advice-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 14px;
            margin-top: 16px;
        }
        .advice-title {
            color: var(--navy);
            font-size: 1rem;
            font-weight: 900;
            margin-bottom: 10px;
        }
        .clinic-card {
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 11px 13px;
            margin-bottom: 8px;
            box-shadow: 0 6px 16px rgba(7, 31, 61, 0.045);
        }
        .clinic-name {
            color: var(--navy);
            font-size: .98rem;
            font-weight: 900;
            margin-bottom: 5px;
            line-height: 1.22;
        }
        .clinic-detail {
            color: var(--muted);
            font-size: .86rem;
            line-height: 1.25;
            margin: 2px 0;
        }
        .clinic-detail strong {
            color: var(--navy);
            font-weight: 850;
        }
        .clinic-actions {
            margin-top: 8px;
        }
        .map-frame {
            border: 1px solid var(--line);
            border-radius: 18px;
            overflow: hidden;
            background: #ffffff;
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
            font-size: 1.45rem;
            font-weight: 950;
            line-height: 1.08;
        }
        .accuracy-big {
            color: var(--blue);
            font-size: 2.35rem;
            font-weight: 950;
            line-height: 1;
        }
        .severity-pill {
            display: inline-block;
            background: var(--soft-blue);
            color: var(--navy);
            border-radius: 999px;
            padding: 8px 14px;
            font-size: .95rem;
            font-weight: 900;
            margin-top: 12px;
        }
        .soft-green {
            background: var(--green-soft);
            color: var(--navy);
            border: 1px solid #a9dfbb;
            border-radius: 10px;
            padding: 16px 18px;
            font-size: .96rem;
            line-height: 1.5;
        }
        .soft-red {
            background: #fff0ef;
            color: var(--navy);
            border: 1px solid #efb9b5;
            border-radius: 10px;
            padding: 16px 18px;
            font-size: .96rem;
            line-height: 1.5;
        }
        .soft-yellow {
            background: var(--yellow-soft);
            color: var(--navy);
            border: 1px solid #efd891;
            border-radius: 10px;
            padding: 16px 18px;
            font-size: .96rem;
            line-height: 1.5;
        }
        input, textarea {
            background: #ffffff !important;
            color: var(--navy) !important;
        }
        input::placeholder, textarea::placeholder {
            color: #7b8ca0 !important;
            opacity: 1 !important;
        }
        label, label span, label p,
        .stTextInput label,
        .stRadio label,
        .stFileUploader label,
        .stCameraInput label {
            color: var(--navy) !important;
            font-weight: 800 !important;
        }
        .stTextInput p,
        .stRadio p,
        .stFileUploader p,
        .stCameraInput p {
            color: var(--navy) !important;
        }
        .stTextInput div,
        .stTextInput span {
            color: var(--navy) !important;
        }
        .stButton > button, .stFormSubmitButton > button {
            min-height: 48px;
            border-radius: 7px;
            font-weight: 850;
            font-size: .98rem;
            background: var(--blue) !important;
            border: 1px solid var(--blue) !important;
            color: #ffffff !important;
        }
        .stButton > button p,
        .stButton > button span,
        .stFormSubmitButton > button p,
        .stFormSubmitButton > button span {
            color: #ffffff !important;
            font-weight: 850 !important;
        }
        .stButton > button[kind="secondary"], .stFormSubmitButton > button[kind="secondary"] {
            background: #ffffff !important;
            border: 1px solid var(--blue) !important;
            color: var(--navy) !important;
        }
        .stButton > button[kind="secondary"] p,
        .stButton > button[kind="secondary"] span,
        .stFormSubmitButton > button[kind="secondary"] p,
        .stFormSubmitButton > button[kind="secondary"] span {
            color: var(--navy) !important;
            font-weight: 850 !important;
        }
        .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
            background: var(--blue) !important;
            border-color: var(--blue) !important;
            color: #ffffff !important;
        }
        .stButton > button[kind="primary"] p,
        .stButton > button[kind="primary"] span,
        .stFormSubmitButton > button[kind="primary"] p,
        .stFormSubmitButton > button[kind="primary"] span {
            color: #ffffff !important;
        }
        .stFileUploader button,
        .stCameraInput button {
            background: var(--blue) !important;
            border: 1px solid var(--blue) !important;
            color: #ffffff !important;
        }
        .stFileUploader button p,
        .stFileUploader button span,
        .stCameraInput button p,
        .stCameraInput button span {
            color: #ffffff !important;
            font-weight: 850 !important;
        }
        .stLinkButton a {
            min-height: 48px;
            border-radius: 7px;
            font-weight: 850;
            font-size: .98rem;
            background: var(--blue) !important;
            border: 1px solid var(--blue) !important;
            color: #ffffff !important;
        }
        .stLinkButton a p,
        .stLinkButton a span {
            color: #ffffff !important;
            font-weight: 850 !important;
        }
        div[role="radiogroup"] label p {
            color: var(--navy) !important;
            font-size: 1.05rem;
        }
        div[role="radiogroup"] label span {
            color: var(--navy) !important;
        }
        .footer-space {
            height: 22px;
        }
        @media (max-width: 760px) {
            .block-container {
                padding-top: .8rem;
            }
            .result-grid,
            .advice-grid {
                grid-template-columns: 1fr;
            }
            h1 {
                font-size: 2rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def brand_header() -> None:
    logo_html = "🩺"
    if LOGO_PATH.exists():
        encoded_logo = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
        logo_html = f'<img src="data:image/png;base64,{encoded_logo}" alt="SkinSense logo" />'
    st.markdown(
        f"""
        <div class="topbar">
            <div class="brand-left">
                <div class="brand-icon">{logo_html}</div>
                <div class="brand-name">SkinSense</div>
            </div>
            <div class="language-pill">◎ {escape(t("language"))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def logout_button() -> None:
    st.markdown("<div class='footer-space'></div>", unsafe_allow_html=True)
    if st.button("Logout", type="secondary", use_container_width=True, key=f"logout_{st.session_state.get('page', 'page')}"):
        st.session_state.clear()
        st.rerun()


def privacy_disclaimer() -> None:
    st.markdown(f"<div class='privacy-box'>{escape(t('privacy'))}</div>", unsafe_allow_html=True)


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
        "care_location": "",
        "care_location_input": "",
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


def severity_band(score: int) -> str:
    if score < 25:
        return "mild"
    if score < 50:
        return "moderate"
    if score < 75:
        return "serious"
    return "urgent"


def image_severity_score(condition: str, answers: dict[str, str]) -> tuple[int, str]:
    """Estimate how serious the visible case may be for choosing care guidance."""
    base_severity = {
        "Irritant Contact Dermatitis": 22,
        "Occupational Hand Eczema": 26,
        "Athlete's Foot (Tinea pedis)": 24,
        "Ringworm (Tinea corporis)": 30,
        "Cutaneous Candidiasis": 32,
        "Paronychia": 48,
        "Folliculitis": 38,
        "Cellulitis": 76,
        "Impetigo": 58,
        "Sunburn": 24,
        "Actinic Keratosis": 45,
    }

    severity = base_severity.get(condition, 35)

    for question, answer in answers.items():
        answer_weight = {"Yes": 1.0, "Sometimes": 0.55, "I don't know": 0.15, "No": 0.0}.get(answer, 0.0)
        question_text = question.lower()

        if any(word in question_text for word in ("pus", "bleeding", "bad smell", "fluid", "ooze", "discharge")):
            severity += 22 * answer_weight
        elif any(word in question_text for word in ("fever", "swelling", "warm", "redness")):
            severity += 20 * answer_weight
        elif any(word in question_text for word in ("spreading", "getting bigger", "spread", "worse", "worsening")):
            severity += 16 * answer_weight
        elif any(word in question_text for word in ("pain", "hurt", "burn")):
            severity += 12 * answer_weight
        elif any(word in question_text for word in ("more than", "week", "2 weeks", "long")):
            severity += 8 * answer_weight
        elif any(word in question_text for word in ("sea water", "seawater", "wet work", "fishing")):
            severity += 5 * answer_weight
        elif "itch" in question_text:
            severity += 4 * answer_weight

    severity_percentage = int(round(max(0, min(100, severity))))
    return severity_percentage, severity_band(severity_percentage)


def guidance_for(condition: str, band: str) -> dict[str, str]:
    condition_guidance = SEVERITY_GUIDANCE.get(condition, {})
    return condition_guidance.get(
        band,
        {
            "do": "Keep the area clean and dry, and monitor whether it changes.",
            "avoid": "Avoid scratching, squeezing, or applying unknown creams.",
            "derm": "See a dermatologist if it spreads, hurts, forms pus, or does not improve.",
        },
    )


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
    severity_percentage, band = image_severity_score(condition, answers)
    guidance = guidance_for(condition, band)
    accuracy_percentage = int(round(max(0, min(1, image_confidence)) * 100))

    return Prediction(
        condition=condition,
        image_confidence=image_confidence,
        final_score=final_score,
        accuracy_percentage=accuracy_percentage,
        severity_percentage=severity_percentage,
        severity_band=band,
        top_predictions=top_predictions,
        what_to_do=guidance["do"],
        what_to_avoid=guidance["avoid"],
        dermatologist=guidance["derm"],
        explanation=DISEASE_INFO.get(condition, "This result is based on the image model and your answers."),
    )


def start_page() -> None:
    brand_header()
    st.title("SkinSense")
    st.markdown(f"<div class='lead-blue'>{t('tagline')}</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='body-copy'>A simple screening tool for Koli fisherwomen and fishermen exposed to seawater, sun, and wet work.</div>",
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
        go("care_choice")

    if st.session_state.get("sheet_warning"):
        st.warning(st.session_state["sheet_warning"])
    st.markdown(f"<div class='disclaimer-box'>{t('disclaimer')}</div>", unsafe_allow_html=True)
    privacy_disclaimer()


def maps_search_url(query: str) -> str:
    params = urllib.parse.urlencode({"api": "1", "query": query})
    return f"https://www.google.com/maps/search/?{params}"


def maps_embed_url(query: str) -> str:
    return "https://www.google.com/maps?q=" + urllib.parse.quote_plus(query) + "&output=embed"


def care_query(care_type: str, location: str) -> str:
    clean_location = re.sub(r"\s+", " ", location).strip()
    return f"{care_type} near {clean_location}"


def maps_place_url(name: str, lat: float, lon: float) -> str:
    query = f"{name} @{lat},{lon}"
    params = urllib.parse.urlencode({"api": "1", "query": query})
    return f"https://www.google.com/maps/search/?{params}"


def exact_location_embed_url(lat: float, lon: float) -> str:
    return f"https://maps.google.com/maps?q={lat},{lon}&z=16&output=embed"


def km_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def fetch_json(url: str, timeout: int = 15) -> dict[str, Any] | list[Any]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "SkinSense student health screening app"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


@st.cache_data(show_spinner=False, ttl=3600)
def geocode_location(location: str) -> dict[str, Any] | None:
    query = urllib.parse.urlencode(
        {
            "format": "json",
            "limit": "1",
            "addressdetails": "1",
            "q": location,
        }
    )
    results = fetch_json(f"https://nominatim.openstreetmap.org/search?{query}")
    if not isinstance(results, list) or not results:
        return None

    first = results[0]
    return {
        "lat": float(first["lat"]),
        "lon": float(first["lon"]),
        "display_name": str(first.get("display_name", location)),
    }


@st.cache_data(show_spinner=False, ttl=3600)
def nominatim_skin_places(location: str, center_lat: float, center_lon: float) -> list[dict[str, Any]]:
    """Search public map records for dermatologist/skin-care places near the typed location."""
    search_terms = [
        f"dermatologist near {location}",
        f"skin clinic near {location}",
        f"dermatology hospital near {location}",
        f"skin doctor near {location}",
    ]
    places: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()

    for term in search_terms:
        query = urllib.parse.urlencode(
            {
                "format": "json",
                "limit": "8",
                "addressdetails": "1",
                "extratags": "1",
                "namedetails": "1",
                "q": term,
            }
        )
        results = fetch_json(f"https://nominatim.openstreetmap.org/search?{query}")
        if not isinstance(results, list):
            continue

        for item in results:
            try:
                place_lat = float(item["lat"])
                place_lon = float(item["lon"])
            except (KeyError, TypeError, ValueError):
                continue

            distance = km_distance(center_lat, center_lon, place_lat, place_lon)
            if distance > 25:
                continue

            namedetails = item.get("namedetails", {}) if isinstance(item.get("namedetails"), dict) else {}
            extratags = item.get("extratags", {}) if isinstance(item.get("extratags"), dict) else {}
            display_name = str(item.get("display_name", "Skin care location"))
            name = (
                namedetails.get("name")
                or item.get("name")
                or display_name.split(",")[0]
                or "Skin care location"
            )
            key = (str(name).lower(), round(place_lat, 4), round(place_lon, 4))
            if key in seen:
                continue
            seen.add(key)

            tags = {
                **extratags,
                "display_name": display_name,
                "search_term": term,
            }
            if item.get("type"):
                tags["osm_type"] = item.get("type")
            if item.get("class"):
                tags["osm_class"] = item.get("class")

            places.append(
                {
                    "name": str(name),
                    "kind": "skin clinic / dermatology",
                    "lat": place_lat,
                    "lon": place_lon,
                    "distance_km": distance,
                    "tags": tags,
                }
            )

    return sorted(places, key=lambda place: place["distance_km"])


@st.cache_data(show_spinner=False, ttl=3600)
def overpass_nearby_healthcare(lat: float, lon: float, radius_m: int) -> list[dict[str, Any]]:
    query = f"""
    [out:json][timeout:20];
    (
      node(around:{radius_m},{lat},{lon})["amenity"~"hospital|clinic|doctors"];
      way(around:{radius_m},{lat},{lon})["amenity"~"hospital|clinic|doctors"];
      relation(around:{radius_m},{lat},{lon})["amenity"~"hospital|clinic|doctors"];
      node(around:{radius_m},{lat},{lon})["healthcare"~"hospital|clinic|doctor"];
      way(around:{radius_m},{lat},{lon})["healthcare"~"hospital|clinic|doctor"];
      relation(around:{radius_m},{lat},{lon})["healthcare"~"hospital|clinic|doctor"];
    );
    out center tags 50;
    """
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    request = urllib.request.Request(
        "https://overpass-api.de/api/interpreter",
        data=data,
        headers={"User-Agent": "SkinSense student health screening app"},
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        payload = json.loads(response.read().decode("utf-8"))

    places: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()
    for element in payload.get("elements", []):
        tags = element.get("tags", {})
        name = tags.get("name") or tags.get("operator") or "Health care location"
        place_lat = element.get("lat") or element.get("center", {}).get("lat")
        place_lon = element.get("lon") or element.get("center", {}).get("lon")
        if place_lat is None or place_lon is None:
            continue

        place_lat = float(place_lat)
        place_lon = float(place_lon)
        key = (str(name).lower(), round(place_lat, 4), round(place_lon, 4))
        if key in seen:
            continue
        seen.add(key)

        kind = tags.get("amenity") or tags.get("healthcare") or "clinic"
        places.append(
            {
                "name": str(name),
                "kind": str(kind),
                "lat": place_lat,
                "lon": place_lon,
                "distance_km": km_distance(lat, lon, place_lat, place_lon),
                "tags": tags,
            }
        )

    return sorted(places, key=lambda item: item["distance_km"])


def place_score(place: dict[str, Any], category: str) -> tuple[int, float]:
    text_blob = " ".join(
        str(value).lower()
        for value in [
            place.get("name", ""),
            place.get("kind", ""),
            " ".join(str(v) for v in place.get("tags", {}).values()),
        ]
    )
    public_words = ("government", "municipal", "public", "civil", "bmc", "esi", "esic", "dispensary", "primary health")
    cheap_words = ("charitable", "trust", "mission", "free", "low cost", "subsidised", "subsidized")
    skin_words = ("skin", "derma", "dermatology", "dermatologist")

    score = 0
    if category == "government" and any(word in text_blob for word in public_words):
        score += 5
    if category == "clinic" and any(word in text_blob for word in ("clinic", "dispensary", "health post", "primary health")):
        score += 5
    if category == "low_cost" and any(word in text_blob for word in cheap_words):
        score += 5
    if any(word in text_blob for word in skin_words):
        score += 3
    if "hospital" in text_blob:
        score += 1

    return (-score, place["distance_km"])


def nearby_places_for_category(places: list[dict[str, Any]], category: str) -> list[dict[str, Any]]:
    ranked = sorted(places, key=lambda place: place_score(place, category))
    return ranked[:5]


def place_overall_score(place: dict[str, Any]) -> int:
    tags = place.get("tags", {})
    text_blob = " ".join(
        str(value).lower()
        for value in [
            place.get("name", ""),
            place.get("kind", ""),
            " ".join(str(v) for v in tags.values()),
        ]
    )
    score = 0
    for word in ("skin", "derma", "dermatology", "dermatologist"):
        if word in text_blob:
            score += 4
    for word in ("government", "municipal", "public", "civil", "bmc", "esi", "esic", "dispensary"):
        if word in text_blob:
            score += 3
    for word in ("charitable", "trust", "free", "low cost", "subsidised", "subsidized"):
        if word in text_blob:
            score += 2
    if "hospital" in text_blob:
        score += 1
    return score


def top_nearby_places(places: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(places, key=lambda place: (place["distance_km"], -place_overall_score(place)))[:5]


def is_skin_related_place(place: dict[str, Any]) -> bool:
    tags = place.get("tags", {})
    text_blob = " ".join(
        str(value).lower()
        for value in [
            place.get("name", ""),
            place.get("kind", ""),
            " ".join(str(v) for v in tags.values()),
        ]
    )
    return any(word in text_blob for word in ("skin", "derma", "dermatology", "dermatologist"))


def merge_unique_places(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()
    for group in groups:
        for place in group:
            key = (str(place.get("name", "")).lower(), round(float(place["lat"]), 4), round(float(place["lon"]), 4))
            if key in seen:
                continue
            seen.add(key)
            merged.append(place)
    return merged


def top_skin_related_places(location: str, lat: float, lon: float, nearby_healthcare: list[dict[str, Any]]) -> list[dict[str, Any]]:
    searched_places = nominatim_skin_places(location, lat, lon)
    tagged_skin_places = [place for place in nearby_healthcare if is_skin_related_place(place)]
    merged = merge_unique_places(searched_places, tagged_skin_places)
    return sorted(merged, key=lambda place: (place["distance_km"], -place_overall_score(place)))[:5]


def place_address(place: dict[str, Any]) -> str:
    tags = place.get("tags", {})
    if tags.get("addr:full"):
        return str(tags["addr:full"])
    if tags.get("display_name"):
        return str(tags["display_name"])

    parts = [
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:neighbourhood"),
        tags.get("addr:suburb"),
        tags.get("addr:city"),
        tags.get("addr:postcode"),
    ]
    address = ", ".join(str(part) for part in parts if part)
    return address


def place_contact(place: dict[str, Any]) -> str:
    tags = place.get("tags", {})
    for key in ("phone", "contact:phone", "contact:mobile", "mobile", "contact:telephone"):
        if tags.get(key):
            return str(tags[key])
    return ""


def compact_text(value: str, max_length: int = 130) -> str:
    value = re.sub(r"\s+", " ", value or "").strip()
    if len(value) <= max_length:
        return value
    return value[: max_length - 3].rstrip() + "..."


def care_choice_page() -> None:
    brand_header()
    st.title(t("choice_title"))
    st.write(t("choice_help"))

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader(t("check_skin"))
            st.write(t("check_skin_help"))
            if st.button(t("check_skin"), type="primary", use_container_width=True, key="choose_check_skin"):
                go("upload")

    with col2:
        with st.container(border=True):
            st.subheader(t("find_dermatologist"))
            st.write(t("find_dermatologist_help"))
            if st.button(t("find_dermatologist"), type="primary", use_container_width=True, key="choose_dermatologist"):
                go("dermatologist")

    privacy_disclaimer()
    logout_button()


def dermatologist_page() -> None:
    brand_header()
    st.title(t("derm_title"))
    st.write(t("derm_help"))

    if st.session_state.get("care_location") and not st.session_state.get("care_location_input"):
        st.session_state["care_location_input"] = st.session_state["care_location"]

    st.text_input(
        t("location_label"),
        placeholder=t("location_placeholder"),
        key="care_location_input",
    )
    location = st.session_state.get("care_location_input", "").strip()
    st.session_state["care_location"] = location

    current_location_query = "government hospital dermatologist near me OR public skin clinic near me"
    st.link_button(
        t("use_current_location"),
        maps_search_url(current_location_query),
        type="primary",
        use_container_width=True,
    )

    if not location:
        st.info(t("map_note"))
    else:
        broad_map_query = care_query("dermatologist skin clinic", location)
        map_col, list_col = st.columns([1.15, 0.85])
        with map_col:
            st.subheader(t("exact_location_map"))
            components.iframe(maps_embed_url(broad_map_query), height=520, scrolling=False)
            st.link_button(t("open_maps"), maps_search_url(broad_map_query), type="primary", use_container_width=True)

        display_places: list[dict[str, Any]] = []
        used_general_fallback = False
        try:
            with st.spinner("Finding nearby care options..."):
                geocoded = geocode_location(location)

            if geocoded is None:
                st.warning(t("location_not_found"))
            else:
                lat = geocoded["lat"]
                lon = geocoded["lon"]
                st.caption(geocoded["display_name"])

                places = overpass_nearby_healthcare(lat, lon, 3000)
                if len(places) < 2:
                    places = overpass_nearby_healthcare(lat, lon, 8000)
                skin_places = top_skin_related_places(location, lat, lon, places)
                if skin_places:
                    display_places = skin_places
                else:
                    display_places = top_nearby_places(places)
                    used_general_fallback = bool(display_places)
        except Exception:
            logger.exception("Nearby care lookup failed")

        with list_col:
            st.subheader(t("top_places"))
            if used_general_fallback:
                st.info(t("no_nearby_places"))
            if not display_places:
                st.info(t("map_note"))
            for index, place in enumerate(display_places, start=1):
                address = compact_text(place_address(place) or t("address_not_listed"))
                contact = compact_text(place_contact(place) or t("contact_not_listed"), max_length=60)
                st.markdown(
                    f"""
                    <div class="clinic-card">
                        <div class="clinic-name">{index}. {escape(place['name'])}</div>
                        <div class="clinic-detail"><strong>{escape(t('distance'))}:</strong> {place['distance_km']:.1f} km</div>
                        <div class="clinic-detail"><strong>{escape(t('place_type'))}:</strong> {escape(place['kind'].title())}</div>
                        <div class="clinic-detail"><strong>{escape(t('address'))}:</strong> {escape(address)}</div>
                        <div class="clinic-detail"><strong>{escape(t('contact'))}:</strong> {escape(contact)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.link_button(
                    t("open_maps"),
                    maps_place_url(place["name"], place["lat"], place["lon"]),
                    type="primary",
                    use_container_width=True,
                )

        st.markdown(f"<div class='soft-yellow'>{escape(t('map_note'))}</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button(t("back_options"), type="primary", use_container_width=True, key="derm_back_options"):
            go("care_choice")
    with col2:
        if st.button(t("check_skin_instead"), type="primary", use_container_width=True, key="derm_check_skin"):
            go("upload")

    privacy_disclaimer()
    logout_button()


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

    col1, col2 = st.columns(2)
    with col1:
        if st.button(t("back_options"), type="primary", use_container_width=True, key="upload_back_options"):
            go("care_choice")
    with col2:
        if st.button(t("find_derm_instead"), type="primary", use_container_width=True, key="upload_find_derm"):
            go("dermatologist")

    privacy_disclaimer()
    logout_button()


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

    if st.button("Back to upload", type="primary", use_container_width=True):
        go("upload")

    privacy_disclaimer()
    logout_button()


def result_page() -> None:
    prediction: Prediction | None = st.session_state.get("final_prediction")
    if prediction is None:
        go("questions")

    brand_header()
    st.title(t("result_title"))
    if st.session_state.get("image_bytes"):
        st.image(st.session_state["image_bytes"], caption=st.session_state.get("image_name", "Uploaded image"), use_container_width=True)

    severity_label = {
        "mild": "Mild care level",
        "moderate": "Moderate care level",
        "serious": "Dermatologist soon",
        "urgent": "Urgent medical care",
    }.get(prediction.severity_band, "Care guidance")

    st.markdown(
        f"""
        <div class="result-grid">
            <div class="result-panel">
                <div class="result-kicker">Possible condition</div>
                <div class="result-disease">{escape(prediction.condition)}</div>
                <p>{escape(prediction.explanation)}</p>
                <div class="severity-pill">{escape(severity_label)}</div>
            </div>
            <div class="result-panel">
                <div class="result-kicker">AI match accuracy</div>
                <div class="accuracy-big">{prediction.accuracy_percentage}%</div>
                <p>This is how strongly the model matched the photo to this disease. It is not a medical diagnosis.</p>
            </div>
        </div>
        <div class="advice-grid">
            <div class="soft-green">
                <div class="advice-title">What you can do</div>
                {escape(prediction.what_to_do)}
            </div>
            <div class="soft-red">
                <div class="advice-title">What to avoid</div>
                {escape(prediction.what_to_avoid)}
            </div>
            <div class="soft-yellow">
                <div class="advice-title">When to see a dermatologist</div>
                {escape(prediction.dermatologist)}
            </div>
        </div>
        <div class="disclaimer-box">{escape(t("disclaimer"))}</div>
        """,
        unsafe_allow_html=True,
    )

    privacy_disclaimer()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Check another image", type="primary", use_container_width=True):
            st.session_state["image_bytes"] = None
            st.session_state["image_prediction"] = None
            st.session_state["final_prediction"] = None
            go("upload")
    with col2:
        if st.button("Start over", type="primary", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    logout_button()


def main() -> None:
    init_state()
    css()
    page = st.session_state.get("page", "start")
    if page not in VALID_PAGES:
        page = "start"

    if page == "start":
        start_page()
    elif page == "care_choice":
        care_choice_page()
    elif page == "dermatologist":
        dermatologist_page()
    elif page == "upload":
        upload_page()
    elif page == "questions":
        questions_page()
    elif page == "result":
        result_page()


if __name__ == "__main__":
    main()
