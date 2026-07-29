import streamlit as st
from openai import OpenAI
import re

# ── CONFIG ──────────────────────────────────────────────────
st.set_page_config(page_title="MedHelix", page_icon="💊", layout="wide")

# ── APPLE CSS ───────────────────────────────────────────────
APPLE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
html,body,[class*="css"]{font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif!important;-webkit-font-smoothing:antialiased}
.stApp{background:#f5f5f7!important}
#MainMenu,footer,header{visibility:hidden}
.block-container{padding-top:1.5rem!important;max-width:880px!important}
.stButton>button{font-family:'Inter',sans-serif!important;font-weight:500;border-radius:10px!important;transition:all .15s ease!important}
.stButton>button[kind="primary"]{background:#0071e3!important;color:#fff!important;border:none!important;box-shadow:0 1px 4px rgba(0,113,227,.35)!important}
.stButton>button[kind="primary"]:hover{background:#0077ed!important;box-shadow:0 3px 12px rgba(0,113,227,.4)!important}
.stButton>button[kind="secondary"]{background:rgba(0,0,0,.05)!important;color:#1d1d1f!important;border:.5px solid rgba(0,0,0,.13)!important}
.stTextInput>div>div>input,.stTextArea>div>div>textarea,.stNumberInput>div>div>input{font-family:'Inter',sans-serif!important;border-radius:10px!important;border:.5px solid rgba(0,0,0,.15)!important;background:rgba(255,255,255,.78)!important;font-size:15px!important}
.stTextInput>div>div>input:focus,.stTextArea>div>div>textarea:focus{border-color:#0071e3!important;box-shadow:0 0 0 3px rgba(0,113,227,.08)!important}
.stSelectbox>div>div{border-radius:10px!important;border:.5px solid rgba(0,0,0,.15)!important;background:rgba(255,255,255,.78)!important}
.stMultiSelect>div>div{border-radius:10px!important;border:.5px solid rgba(0,0,0,.15)!important;background:rgba(255,255,255,.78)!important}
div[data-testid="metric-container"]{background:rgba(255,255,255,.8)!important;border:.5px solid rgba(0,0,0,.08)!important;border-radius:12px!important;padding:14px 16px!important}
section[data-testid="stSidebar"]{background:rgba(245,245,247,.95)!important;border-right:.5px solid rgba(0,0,0,.08)!important}
div[data-testid="stExpander"]{border-radius:14px!important;border:.5px solid rgba(0,0,0,.08)!important}
hr{border-color:rgba(0,0,0,.08)!important}
.stCaption{color:#6e6e73!important}
.stRadio>div{gap:8px}
</style>
"""
st.markdown(APPLE_CSS, unsafe_allow_html=True)

# ── API CLIENT ──────────────────────────────────────────────
@st.cache_resource
def get_client():
    api_key = "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"
    if not api_key:
        return None
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

client = get_client()

# ── SESSION STATE ───────────────────────────────────────────
_defaults = {
    "page": "login",
    "logged_in": False,
    "user_id": "",
    "profile": {},
    "profile_complete": False,
    "health_history": [],
    "int_meds": [],
}
for _k, _v in _defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

drug_info = {

    # ── ANALGESICS / ANTIPYRETICS ──────────────────────────────
    "paracetamol":       {"use": "Fever, mild-moderate pain",               "side_effects": "Liver damage (overdose)",                     "warning": "Max 4g/day; avoid alcohol",                          "dosage": "500mg–1g every 4–6 hrs"},
    "ibuprofen":         {"use": "Pain, inflammation, fever",               "side_effects": "Stomach irritation, GI bleed",                "warning": "Take with food; avoid in kidney disease",            "dosage": "200–400mg every 6–8 hrs"},
    "aspirin":           {"use": "Pain, fever, blood thinning",             "side_effects": "Bleeding, stomach irritation",                "warning": "Avoid in children under 16",                         "dosage": "300–600mg every 4–6 hrs"},
    "diclofenac":        {"use": "Pain, inflammation, arthritis",           "side_effects": "GI irritation, fluid retention",              "warning": "Avoid in heart/kidney disease; take with food",      "dosage": "50mg 2–3 times daily"},
    "naproxen":          {"use": "Pain, arthritis, menstrual cramps",       "side_effects": "GI upset, cardiovascular risk",               "warning": "Avoid long-term without medical supervision",        "dosage": "250–500mg twice daily"},
    "tramadol":          {"use": "Moderate to severe pain",                 "side_effects": "Nausea, dizziness, dependence",               "warning": "Risk of dependence; avoid alcohol; seizure risk",    "dosage": "50–100mg every 4–6 hrs (max 400mg/day)"},
    "codeine":           {"use": "Mild-moderate pain, cough suppression",   "side_effects": "Constipation, drowsiness, dependence",        "warning": "Avoid in children; dependence risk; CYP2D6 variability", "dosage": "15–60mg every 4–6 hrs"},
    "morphine":          {"use": "Severe pain, palliative care",            "side_effects": "Respiratory depression, constipation",        "warning": "Strictly controlled; high dependence risk",          "dosage": "As prescribed — titrated to effect"},
    "oxycodone":         {"use": "Severe pain",                             "side_effects": "Respiratory depression, constipation",        "warning": "High abuse potential; controlled substance",         "dosage": "5–15mg every 4–6 hrs (immediate release)"},
    "fentanyl":          {"use": "Severe/chronic pain, anaesthesia",        "side_effects": "Respiratory depression, sedation",            "warning": "Extremely potent; patch disposal is hazardous",      "dosage": "As prescribed — patch or IV"},
    "celecoxib":         {"use": "Arthritis, pain (COX-2 inhibitor)",       "side_effects": "Cardiovascular risk, hypertension",           "warning": "Avoid in sulfa allergy; cardiovascular caution",     "dosage": "100–200mg once or twice daily"},
    "meloxicam":         {"use": "Osteoarthritis, rheumatoid arthritis",    "side_effects": "GI upset, cardiovascular risk",               "warning": "Lowest effective dose; avoid in renal disease",      "dosage": "7.5–15mg once daily"},
    "indomethacin":      {"use": "Gout, arthritis, bursitis",              "side_effects": "Headache, severe GI upset",                   "warning": "Avoid in elderly; GI protective agent recommended",  "dosage": "25–50mg 2–3 times daily"},
    "ketorolac":         {"use": "Short-term moderate-severe pain",         "side_effects": "GI bleed, renal impairment",                  "warning": "Max 5 days only; avoid in renal disease",           "dosage": "10mg every 4–6 hrs (max 5 days)"},
    "mefenamic acid":    {"use": "Menstrual pain, mild pain",               "side_effects": "GI upset, diarrhoea",                         "warning": "Short-term use only; avoid in IBD",                  "dosage": "500mg then 250mg every 6 hrs"},

    # ── ANTIBIOTICS ────────────────────────────────────────────
    "amoxicillin":       {"use": "Bacterial infections",                    "side_effects": "Diarrhoea, rash, nausea",                     "warning": "Complete full course",                               "dosage": "250–500mg every 8 hrs"},
    "amoxicillin-clavulanate": {"use": "Resistant bacterial infections",    "side_effects": "Diarrhoea, hepatotoxicity",                   "warning": "Monitor liver function; complete course",            "dosage": "625mg every 8 hrs or 1g every 12 hrs"},
    "azithromycin":      {"use": "Respiratory, skin, STI infections",       "side_effects": "Nausea, diarrhoea, cardiac arrhythmia",       "warning": "Cardiac risk (QT prolongation); avoid in liver disease", "dosage": "500mg day 1, then 250mg days 2–5"},
    "clarithromycin":    {"use": "Respiratory infections, H. pylori",       "side_effects": "GI upset, metallic taste, QT prolongation",   "warning": "Many drug interactions; avoid in liver disease",     "dosage": "250–500mg twice daily"},
    "ciprofloxacin":     {"use": "UTI, respiratory, GI infections",         "side_effects": "Tendon damage, nausea, QT prolongation",      "warning": "Avoid in children; take with water; tendon risk",    "dosage": "250–750mg every 12 hrs"},
    "levofloxacin":      {"use": "Respiratory, UTI, skin infections",       "side_effects": "QT prolongation, tendon rupture",             "warning": "Tendon risk especially in elderly; QT monitoring",  "dosage": "500mg once daily"},
    "doxycycline":       {"use": "Bacterial infections, malaria prevention","side_effects": "Photosensitivity, nausea, oesophageal irritation", "warning": "Avoid sun; take with full glass of water upright",  "dosage": "100mg every 12 hrs"},
    "metronidazole":     {"use": "Anaerobic bacterial/parasitic infections", "side_effects": "Metallic taste, nausea, peripheral neuropathy", "warning": "Strictly avoid alcohol during and 48 hrs after use", "dosage": "200–500mg every 8 hrs"},
    "trimethoprim":      {"use": "UTI, respiratory infections",             "side_effects": "Rash, GI upset, high potassium",              "warning": "Avoid in first trimester pregnancy; monitor potassium", "dosage": "200mg twice daily"},
    "nitrofurantoin":    {"use": "Urinary tract infections",                "side_effects": "Nausea, pulmonary toxicity (long-term)",       "warning": "Avoid in renal failure; not for upper UTI",          "dosage": "50–100mg 4 times daily (5 days)"},
    "cephalexin":        {"use": "Skin, respiratory, UTI infections",       "side_effects": "GI upset, rash",                              "warning": "Caution in penicillin allergy (cross-reactivity)",   "dosage": "250–500mg every 6 hrs"},
    "cefuroxime":        {"use": "Respiratory, skin, UTI infections",       "side_effects": "GI upset, headache",                          "warning": "Cross-reactivity with penicillin allergy possible",  "dosage": "250–500mg twice daily"},
    "flucloxacillin":    {"use": "Staphylococcal skin infections",          "side_effects": "GI upset, hepatotoxicity",                    "warning": "Take on empty stomach; monitor liver function",       "dosage": "250–500mg every 6 hrs"},
    "erythromycin":      {"use": "Respiratory, skin infections (penicillin alternative)", "side_effects": "GI upset, QT prolongation",    "warning": "Many drug interactions; QT risk",                    "dosage": "250–500mg every 6 hrs"},
    "vancomycin":        {"use": "Serious Gram-positive infections, MRSA",  "side_effects": "Nephrotoxicity, ototoxicity, red-man syndrome", "warning": "IV only (mostly); therapeutic drug monitoring required", "dosage": "As prescribed — weight/renal adjusted"},
    "clindamycin":       {"use": "Skin, bone, anaerobic infections",        "side_effects": "C. diff colitis, GI upset",                   "warning": "Stop immediately if diarrhoea develops",             "dosage": "150–300mg every 6 hrs"},
    "rifampicin":        {"use": "Tuberculosis, leprosy, meningitis prophylaxis", "side_effects": "Orange body fluids, hepatotoxicity",   "warning": "Powerful enzyme inducer — reduces many drug levels", "dosage": "600mg once daily (TB)"},
    "isoniazid":         {"use": "Tuberculosis treatment/prevention",       "side_effects": "Peripheral neuropathy, hepatotoxicity",       "warning": "Take pyridoxine (B6) to prevent neuropathy",         "dosage": "300mg once daily"},
    "ethambutol":        {"use": "Tuberculosis (combination therapy)",      "side_effects": "Optic neuritis, reduced colour vision",        "warning": "Regular eye tests required; avoid in optic neuritis","dosage": "15mg/kg once daily"},
    "meropenem":         {"use": "Severe hospital-acquired infections",     "side_effects": "Seizures (high doses), GI upset",             "warning": "IV only; reserve for resistant infections",          "dosage": "As prescribed — IV"},
    "linezolid":         {"use": "MRSA, VRE, resistant Gram-positive infections", "side_effects": "Serotonin syndrome, bone marrow suppression", "warning": "Avoid with SSRIs/MAOIs; monitor FBC",             "dosage": "600mg every 12 hrs"},

    # ── ANTIFUNGALS ────────────────────────────────────────────
    "fluconazole":       {"use": "Candida, cryptococcal infections",        "side_effects": "Headache, nausea, QT prolongation",           "warning": "Many drug interactions; QT monitoring in cardiac patients", "dosage": "50–400mg once daily (condition-dependent)"},
    "itraconazole":      {"use": "Systemic fungal infections, onychomycosis", "side_effects": "Heart failure, hepatotoxicity",             "warning": "Avoid in heart failure; many drug interactions",     "dosage": "100–200mg once or twice daily"},
    "terbinafine":       {"use": "Fungal nail and skin infections",         "side_effects": "Hepatotoxicity, taste disturbance",           "warning": "Monitor liver function; avoid in liver disease",     "dosage": "250mg once daily"},
    "clotrimazole":      {"use": "Topical fungal/yeast infections",         "side_effects": "Local irritation, burning",                   "warning": "Topical use only; avoid eyes",                        "dosage": "Apply 2–3 times daily"},
    "nystatin":          {"use": "Oral/intestinal candidiasis",             "side_effects": "GI upset (oral form)",                        "warning": "Not absorbed systemically; topical/local action only","dosage": "100,000 units 4 times daily"},

    # ── ANTIVIRALS ─────────────────────────────────────────────
    "aciclovir":         {"use": "Herpes simplex, varicella-zoster",        "side_effects": "Headache, nausea, renal impairment (IV)",      "warning": "Maintain adequate hydration, especially IV",         "dosage": "200–800mg 5 times daily (oral)"},
    "oseltamivir":       {"use": "Influenza treatment and prevention",      "side_effects": "Nausea, vomiting, headache",                  "warning": "Start within 48 hrs of symptoms for maximum effect", "dosage": "75mg twice daily for 5 days"},
    "tenofovir":         {"use": "HIV, Hepatitis B",                        "side_effects": "Renal impairment, bone density loss",         "warning": "Monitor kidney function and bone density",           "dosage": "300mg once daily"},
    "lamivudine":        {"use": "HIV, Hepatitis B",                        "side_effects": "Headache, nausea, fatigue",                   "warning": "Resistance develops rapidly if used as HIV monotherapy", "dosage": "150mg twice daily (HIV) or 100mg daily (HBV)"},
    "ritonavir":         {"use": "HIV (booster/pharmacoenhancer)",          "side_effects": "GI upset, lipid abnormalities, hepatotoxicity","warning": "Potent CYP3A4 inhibitor — massive drug interactions","dosage": "As booster: 100mg twice daily"},

    # ── ANTIHYPERTENSIVES / CARDIOVASCULAR ────────────────────
    "lisinopril":        {"use": "Hypertension, heart failure, diabetic nephropathy", "side_effects": "Dry cough, dizziness, hyperkalaemia", "warning": "Avoid in pregnancy; monitor potassium and renal function", "dosage": "5–40mg once daily"},
    "ramipril":          {"use": "Hypertension, heart failure, post-MI cardioprotection", "side_effects": "Dry cough, hyperkalaemia, angioedema", "warning": "Avoid in pregnancy; angioedema risk",            "dosage": "2.5–10mg once or twice daily"},
    "enalapril":         {"use": "Hypertension, heart failure",             "side_effects": "Dry cough, hypotension, hyperkalaemia",        "warning": "Avoid in pregnancy; monitor potassium",              "dosage": "5–40mg once or twice daily"},
    "losartan":          {"use": "Hypertension, diabetic nephropathy, heart failure", "side_effects": "Dizziness, hyperkalaemia",           "warning": "Avoid in pregnancy; monitor potassium and renal function", "dosage": "25–100mg once daily"},
    "valsartan":         {"use": "Hypertension, heart failure, post-MI",    "side_effects": "Dizziness, hyperkalaemia",                    "warning": "Avoid in pregnancy; monitor renal function",         "dosage": "80–320mg once daily"},
    "amlodipine":        {"use": "Hypertension, angina",                    "side_effects": "Ankle oedema, flushing, dizziness",           "warning": "Do not stop abruptly; ankle swelling is common",     "dosage": "5–10mg once daily"},
    "nifedipine":        {"use": "Hypertension, angina, Raynaud's",         "side_effects": "Headache, flushing, ankle oedema",            "warning": "Avoid short-acting in acute MI; use modified-release","dosage": "30–90mg once daily (modified-release)"},
    "diltiazem":         {"use": "Hypertension, angina, atrial fibrillation", "side_effects": "Bradycardia, oedema, constipation",         "warning": "Avoid with beta-blockers (bradycardia risk); monitor HR", "dosage": "60–120mg 3 times daily"},
    "verapamil":         {"use": "Hypertension, angina, SVT",               "side_effects": "Constipation, bradycardia, heart block",       "warning": "Never with beta-blockers; strong CYP3A4 inhibitor",  "dosage": "40–120mg 3 times daily"},
    "atenolol":          {"use": "Hypertension, angina, post-MI",           "side_effects": "Fatigue, cold extremities, bradycardia",       "warning": "Do not stop abruptly; avoid in asthma",             "dosage": "25–100mg once daily"},
    "metoprolol":        {"use": "Hypertension, angina, heart failure",     "side_effects": "Fatigue, cold hands, slow heart rate",        "warning": "Do not stop abruptly; avoid in asthma; monitor pulse","dosage": "25–200mg once or twice daily"},
    "bisoprolol":        {"use": "Hypertension, heart failure, angina",     "side_effects": "Fatigue, bradycardia, cold extremities",       "warning": "Do not stop abruptly; caution in asthma",           "dosage": "1.25–10mg once daily"},
    "carvedilol":        {"use": "Heart failure, hypertension, post-MI",    "side_effects": "Dizziness, fatigue, hypotension",             "warning": "Do not stop abruptly; take with food",               "dosage": "3.125–25mg twice daily"},
    "propranolol":       {"use": "Hypertension, anxiety, tremor, migraine prevention", "side_effects": "Fatigue, cold extremities, bronchospasm", "warning": "Avoid in asthma/COPD; do not stop abruptly",   "dosage": "10–40mg 2–4 times daily"},
    "furosemide":        {"use": "Oedema, heart failure, hypertension",     "side_effects": "Hypokalaemia, dehydration, ototoxicity",       "warning": "Monitor electrolytes; take in the morning",          "dosage": "20–80mg once or twice daily"},
    "spironolactone":    {"use": "Heart failure, oedema, hyperaldosteronism", "side_effects": "Hyperkalaemia, gynaecomastia, menstrual irregularity", "warning": "Avoid with ACE inhibitors/ARBs (hyperkalaemia risk)", "dosage": "25–200mg once daily"},
    "hydrochlorothiazide": {"use": "Hypertension, oedema",                 "side_effects": "Hypokalaemia, hyperuricaemia, glucose intolerance", "warning": "Monitor electrolytes; avoid in gout",            "dosage": "12.5–50mg once daily"},
    "indapamide":        {"use": "Hypertension, oedema",                    "side_effects": "Hypokalaemia, hyponatraemia",                  "warning": "Monitor electrolytes; avoid in severe renal failure","dosage": "1.5–2.5mg once daily"},
    "doxazosin":         {"use": "Hypertension, benign prostatic hyperplasia", "side_effects": "Postural hypotension, dizziness, oedema",  "warning": "First-dose hypotension — take at bedtime initially", "dosage": "1–16mg once daily"},
    "clonidine":         {"use": "Hypertension, ADHD (off-label), opioid withdrawal", "side_effects": "Dry mouth, sedation, rebound hypertension", "warning": "Do not stop abruptly — dangerous rebound HTN", "dosage": "50–300mcg 2–3 times daily"},

    # ── ANTICOAGULANTS / ANTIPLATELETS ────────────────────────
    "warfarin":          {"use": "VTE, atrial fibrillation, mechanical heart valves", "side_effects": "Bleeding, bruising, skin necrosis",  "warning": "Monitor INR regularly; extensive food/drug interactions", "dosage": "Individualised — INR-guided"},
    "apixaban":          {"use": "Stroke prevention (AF), VTE treatment",   "side_effects": "Bleeding, anaemia",                           "warning": "No routine monitoring; avoid in severe renal failure","dosage": "5mg twice daily (2.5mg if ≥2 risk factors)"},
    "rivaroxaban":       {"use": "Stroke prevention (AF), VTE treatment/prevention", "side_effects": "Bleeding, nausea",                  "warning": "Take with evening meal; avoid in severe renal failure","dosage": "20mg once daily with evening meal (AF)"},
    "dabigatran":        {"use": "Stroke prevention (AF), VTE",             "side_effects": "Bleeding, dyspepsia",                         "warning": "Avoid in severe renal failure; capsule must not be crushed", "dosage": "150mg twice daily (or 110mg if risk factors)"},
    "clopidogrel":       {"use": "Stroke/MI prevention, acute coronary syndromes", "side_effects": "Bleeding, bruising",                  "warning": "Do not stop without doctor advice; check CYP2C19 status", "dosage": "75mg once daily"},
    "ticagrelor":        {"use": "Acute coronary syndromes, post-MI",       "side_effects": "Dyspnoea, bleeding, bradycardia",             "warning": "Do not use with high-dose aspirin; dyspnoea is common", "dosage": "90mg twice daily"},
    "heparin":           {"use": "VTE treatment/prevention, acute coronary syndromes", "side_effects": "Bleeding, heparin-induced thrombocytopenia (HIT)", "warning": "Monitor APTT and platelets; HIT risk", "dosage": "As prescribed — weight-based IV/SC"},
    "enoxaparin":        {"use": "VTE prevention and treatment, ACS",       "side_effects": "Bleeding, HIT (rare)",                        "warning": "Dose-adjust in renal failure; monitor anti-Xa",      "dosage": "1mg/kg SC twice daily (treatment)"},
    "alteplase":         {"use": "Acute ischaemic stroke, PE, STEMI (thrombolysis)", "side_effects": "Serious haemorrhage, cerebral oedema", "warning": "Absolute contraindications include recent surgery/trauma", "dosage": "As prescribed — hospital use only"},

    # ── STATINS / LIPID-LOWERING ───────────────────────────────
    "atorvastatin":      {"use": "High cholesterol, cardiovascular risk reduction", "side_effects": "Myopathy, liver enzyme elevation",    "warning": "Avoid grapefruit; report muscle pain immediately",   "dosage": "10–80mg once daily"},
    "simvastatin":       {"use": "High cholesterol",                        "side_effects": "Myopathy, liver enzyme elevation",            "warning": "Avoid grapefruit; many interactions; max 40mg if on amlodipine", "dosage": "10–40mg once daily at night"},
    "rosuvastatin":      {"use": "High cholesterol, cardiovascular risk",   "side_effects": "Myopathy, proteinuria at high doses",         "warning": "Dose-reduce in Asian patients; avoid high doses in renal disease", "dosage": "5–40mg once daily"},
    "pravastatin":       {"use": "High cholesterol (fewer interactions)",   "side_effects": "Myopathy (lower risk), GI upset",             "warning": "Fewer CYP interactions than other statins",          "dosage": "10–40mg once daily at night"},
    "ezetimibe":         {"use": "High cholesterol (adjunct to statins)",   "side_effects": "GI upset, headache, myopathy (with statin)",  "warning": "Not as monotherapy in most cases",                   "dosage": "10mg once daily"},
    "fenofibrate":       {"use": "High triglycerides, mixed dyslipidaemia", "side_effects": "GI upset, myopathy, renal impairment",        "warning": "Avoid in severe renal failure; myopathy risk with statins", "dosage": "67–200mg once daily"},

    # ── DIABETES MEDICATIONS ───────────────────────────────────
    "metformin":         {"use": "Type 2 diabetes (first-line)",            "side_effects": "GI upset, nausea, lactic acidosis (rare)",    "warning": "Avoid alcohol; hold before contrast/surgery; monitor kidneys", "dosage": "500mg–1g twice daily with meals"},
    "glibenclamide":     {"use": "Type 2 diabetes (sulphonylurea)",         "side_effects": "Hypoglycaemia, weight gain",                  "warning": "Hypoglycaemia risk especially in elderly; avoid skipping meals", "dosage": "2.5–15mg daily with breakfast"},
    "gliclazide":        {"use": "Type 2 diabetes (sulphonylurea)",         "side_effects": "Hypoglycaemia, weight gain",                  "warning": "Hypoglycaemia risk; take with food",                  "dosage": "40–320mg daily in divided doses"},
    "glimepiride":       {"use": "Type 2 diabetes",                         "side_effects": "Hypoglycaemia, weight gain",                  "warning": "Hypoglycaemia risk; caution in renal failure",       "dosage": "1–4mg once daily with breakfast"},
    "sitagliptin":       {"use": "Type 2 diabetes (DPP-4 inhibitor)",       "side_effects": "Nasopharyngitis, pancreatitis (rare)",         "warning": "Dose-reduce in renal failure; pancreatitis risk",    "dosage": "100mg once daily"},
    "empagliflozin":     {"use": "Type 2 diabetes, heart failure, CKD",     "side_effects": "UTI, genital infections, DKA (rare)",         "warning": "Stop before surgery; urogenital infection risk",     "dosage": "10–25mg once daily"},
    "dapagliflozin":     {"use": "Type 2 diabetes, heart failure, CKD",     "side_effects": "UTI, genital infections, DKA (rare)",         "warning": "Stop before surgery; adequate hydration important",  "dosage": "10mg once daily"},
    "liraglutide":       {"use": "Type 2 diabetes, obesity (GLP-1 agonist)","side_effects": "Nausea, vomiting, pancreatitis risk",         "warning": "Inject subcutaneously; pancreatitis/thyroid risk",   "dosage": "0.6–1.8mg SC once daily"},
    "semaglutide":       {"use": "Type 2 diabetes, obesity (GLP-1 agonist)","side_effects": "Nausea, vomiting, diarrhoea",                 "warning": "Thyroid C-cell risk; pancreatitis; contraception needed", "dosage": "0.25–1mg SC once weekly"},
    "pioglitazone":      {"use": "Type 2 diabetes (thiazolidinedione)",     "side_effects": "Weight gain, oedema, bladder cancer risk",    "warning": "Avoid in heart failure and bladder cancer history",  "dosage": "15–45mg once daily"},
    "insulin glargine":  {"use": "Diabetes (basal insulin)",                "side_effects": "Hypoglycaemia, injection-site lipohypertrophy","warning": "Do not mix with other insulins; inject SC only",     "dosage": "Individualised — once daily SC"},
    "insulin aspart":    {"use": "Diabetes (rapid-acting insulin)",         "side_effects": "Hypoglycaemia, weight gain",                  "warning": "Inject immediately before meals; monitor glucose",   "dosage": "Individualised — with meals SC"},
    "acarbose":          {"use": "Type 2 diabetes (alpha-glucosidase inhibitor)", "side_effects": "Flatulence, diarrhoea, abdominal pain",  "warning": "Take with first bite of each meal; GI side effects common", "dosage": "50–100mg 3 times daily with meals"},

    # ── THYROID ────────────────────────────────────────────────
    "levothyroxine":     {"use": "Hypothyroidism, thyroid cancer suppression","side_effects": "Palpitations, weight loss, insomnia (overdose)","warning": "Take on empty stomach 30–60 min before food; many interactions", "dosage": "25–200mcg once daily (fasting)"},
    "carbimazole":       {"use": "Hyperthyroidism, Graves' disease",         "side_effects": "Agranulocytosis (rare but serious), rash",    "warning": "Report sore throat/fever immediately — agranulocytosis risk", "dosage": "20–60mg daily in divided doses"},
    "propylthiouracil":  {"use": "Hyperthyroidism (especially pregnancy)",   "side_effects": "Hepatotoxicity, agranulocytosis",             "warning": "Monitor LFTs; agranulocytosis risk; preferred in 1st trimester", "dosage": "200–400mg daily in divided doses"},

    # ── GI / ACID SUPPRESSION ──────────────────────────────────
    "omeprazole":        {"use": "GORD, peptic ulcers, H. pylori (triple therapy)","side_effects": "Headache, nausea, magnesium deficiency (long-term)","warning": "Short-term use preferred; C. diff risk; may affect clopidogrel", "dosage": "20–40mg once daily before breakfast"},
    "pantoprazole":      {"use": "GORD, peptic ulcers, Zollinger-Ellison",   "side_effects": "Headache, diarrhoea, hypomagnesaemia",         "warning": "Short-term preferred; check magnesium on long-term use","dosage": "40mg once daily before breakfast"},
    "lansoprazole":      {"use": "GORD, peptic ulcers, H. pylori",           "side_effects": "Headache, nausea, diarrhoea",                  "warning": "Short-term preferred; bone density loss with long-term use", "dosage": "15–30mg once daily"},
    "esomeprazole":      {"use": "GORD, peptic ulcers",                      "side_effects": "Headache, nausea, dry mouth",                  "warning": "As with all PPIs — use minimum effective dose",      "dosage": "20–40mg once daily"},
    "ranitidine":        {"use": "Acid reflux, peptic ulcers (H2 blocker)",  "side_effects": "Headache, constipation",                       "warning": "Ranitidine was recalled in many countries — check local status", "dosage": "150mg twice daily or 300mg at night"},
    "famotidine":        {"use": "GORD, peptic ulcers (H2 blocker)",         "side_effects": "Headache, dizziness, constipation",            "warning": "Safer alternative to ranitidine; dose-reduce in renal failure", "dosage": "20–40mg once or twice daily"},
    "domperidone":       {"use": "Nausea, vomiting, gastroparesis",          "side_effects": "QT prolongation, galactorrhoea",               "warning": "Cardiac risk; avoid doses >10mg and age >60 if possible","dosage": "10mg up to 3 times daily before meals"},
    "metoclopramide":    {"use": "Nausea, vomiting, gastroparesis",          "side_effects": "Extrapyramidal effects, tardive dyskinesia",    "warning": "Max 5 days; avoid in Parkinson's; extrapyramidal risk","dosage": "10mg up to 3 times daily"},
    "ondansetron":       {"use": "Chemotherapy-induced nausea/vomiting, post-op nausea","side_effects": "Constipation, headache, QT prolongation","warning": "QT monitoring in at-risk patients; constipation",    "dosage": "4–8mg up to 3 times daily"},
    "loperamide":        {"use": "Acute/chronic diarrhoea",                  "side_effects": "Constipation, abdominal cramps",               "warning": "Do not use in bloody diarrhoea or bacterial colitis","dosage": "4mg initially, then 2mg after each loose stool (max 16mg/day)"},
    "bisacodyl":         {"use": "Constipation, bowel preparation",          "side_effects": "Abdominal cramps, electrolyte disturbance",    "warning": "Short-term use only; do not crush tablets",          "dosage": "5–10mg once daily at night"},
    "lactulose":         {"use": "Constipation, hepatic encephalopathy",     "side_effects": "Flatulence, bloating, diarrhoea",              "warning": "Takes 48 hrs to work; adjust dose to achieve 2–3 soft stools/day", "dosage": "15–30ml twice daily"},
    "mesalazine":        {"use": "Ulcerative colitis, Crohn's disease maintenance","side_effects": "Headache, nausea, interstitial nephritis","warning": "Monitor renal function; not same as sulphasalazine","dosage": "400mg–4.8g daily in divided doses"},
    "sulfasalazine":     {"use": "Inflammatory bowel disease, rheumatoid arthritis","side_effects": "GI upset, haematological toxicity, orange urine","warning": "Avoid in sulfa allergy; regular FBC monitoring",  "dosage": "1–4g daily in divided doses"},

    # ── RESPIRATORY ────────────────────────────────────────────
    "salbutamol":        {"use": "Asthma, COPD bronchospasm (reliever)",    "side_effects": "Tremor, tachycardia, hypokalaemia",            "warning": "Reliever only — overuse masks poor control; use spacer","dosage": "1–2 puffs (100mcg) as needed"},
    "formoterol":        {"use": "Asthma/COPD maintenance (LABA)",          "side_effects": "Tremor, tachycardia, hypokalaemia",            "warning": "Never use as sole agent in asthma — always with ICS","dosage": "6–12mcg twice daily (inhaled)"},
    "salmeterol":        {"use": "Asthma/COPD maintenance (LABA)",          "side_effects": "Tremor, headache, paradoxical bronchospasm",   "warning": "Never use as sole agent in asthma; always with ICS","dosage": "50mcg twice daily (inhaled)"},
    "beclometasone":     {"use": "Asthma preventer (inhaled corticosteroid)","side_effects": "Oral candidiasis, dysphonia",                  "warning": "Rinse mouth after use; systemic effects at high doses","dosage": "100–400mcg twice daily (inhaled)"},
    "fluticasone":       {"use": "Asthma/COPD preventer (ICS)",             "side_effects": "Oral candidiasis, adrenal suppression (high dose)","warning": "Rinse mouth after use; do not stop abruptly",      "dosage": "100–500mcg twice daily (inhaled)"},
    "budesonide":        {"use": "Asthma/COPD preventer, Crohn's, rhinitis","side_effects": "Oral candidiasis, nasal irritation (nasal)",   "warning": "Rinse mouth after use; minimal systemic absorption","dosage": "100–800mcg twice daily (inhaled)"},
    "tiotropium":        {"use": "COPD maintenance (long-acting anticholinergic)","side_effects": "Dry mouth, urinary retention, constipation","warning": "Avoid in angle-closure glaucoma; urinary retention risk","dosage": "18mcg once daily (inhaled)"},
    "ipratropium":       {"use": "COPD/asthma (short-acting anticholinergic)","side_effects": "Dry mouth, blurred vision, urinary retention","warning": "Avoid in angle-closure glaucoma",                   "dosage": "20–40mcg up to 4 times daily"},
    "montelukast":       {"use": "Asthma preventer, allergic rhinitis",     "side_effects": "Headache, neuropsychiatric effects",           "warning": "Neuropsychiatric effects — suicidal ideation reported (rare)","dosage": "10mg once daily at night"},
    "prednisolone":      {"use": "Inflammation, autoimmune, asthma, COPD exacerbations","side_effects": "Weight gain, osteoporosis, blood sugar rise","warning": "Do not stop abruptly; adrenal suppression risk",  "dosage": "5–60mg daily as prescribed"},
    "dexamethasone":     {"use": "Severe inflammation, cerebral oedema, COVID-19","side_effects": "Hyperglycaemia, immunosuppression, psychosis","warning": "Do not stop abruptly; infection risk",            "dosage": "0.5–24mg daily (condition-dependent)"},

    # ── PSYCHIATRY / NEUROLOGY ─────────────────────────────────
    "sertraline":        {"use": "Depression, anxiety, OCD, PTSD, panic disorder","side_effects": "Nausea, insomnia, sexual dysfunction, hyponatraemia","warning": "Takes 2–4 weeks; do not stop abruptly; serotonin syndrome risk","dosage": "50–200mg once daily"},
    "fluoxetine":        {"use": "Depression, OCD, bulimia, panic disorder","side_effects": "Insomnia, nausea, sexual dysfunction",         "warning": "Longest half-life SSRI; many drug interactions; 5-week washout before MAOIs","dosage": "20–60mg once daily"},
    "escitalopram":      {"use": "Depression, generalised anxiety disorder","side_effects": "Nausea, insomnia, QT prolongation",             "warning": "QT risk at higher doses; avoid in cardiac patients", "dosage": "10–20mg once daily"},
    "citalopram":        {"use": "Depression",                              "side_effects": "QT prolongation, nausea, insomnia",             "warning": "QT monitoring; max 20mg in elderly/liver disease",  "dosage": "20–40mg once daily"},
    "paroxetine":        {"use": "Depression, anxiety, OCD, PTSD",         "side_effects": "Worst SSRI for discontinuation syndrome; weight gain","warning": "Do not stop abruptly; significant withdrawal syndrome","dosage": "20–60mg once daily"},
    "venlafaxine":       {"use": "Depression, anxiety, panic disorder (SNRI)","side_effects": "Hypertension, nausea, sexual dysfunction, discontinuation syndrome","warning": "Monitor BP; do not stop abruptly; hypertension risk","dosage": "75–375mg daily"},
    "duloxetine":        {"use": "Depression, anxiety, diabetic neuropathy, fibromyalgia (SNRI)","side_effects": "Nausea, dizziness, hypertension","warning": "Avoid in liver disease; taper slowly",             "dosage": "30–120mg daily"},
    "amitriptyline":     {"use": "Depression, neuropathic pain, migraine prevention (TCA)","side_effects": "Anticholinergic effects, weight gain, cardiac arrhythmia","warning": "Overdose is dangerous (cardiac); avoid in elderly if possible","dosage": "10–150mg at night"},
    "mirtazapine":       {"use": "Depression, anxiety, insomnia, appetite stimulation","side_effects": "Sedation, weight gain, dry mouth",          "warning": "Fewer sexual side effects; useful in underweight depressed patients","dosage": "15–45mg at night"},
    "lithium":           {"use": "Bipolar disorder, recurrent depression prophylaxis","side_effects": "Tremor, polyuria, hypothyroidism, renal impairment","warning": "Narrow therapeutic index; regular levels, TFT, renal monitoring","dosage": "400–1200mg daily in divided doses (level-guided)"},
    "quetiapine":        {"use": "Schizophrenia, bipolar disorder, depression augmentation","side_effects": "Sedation, weight gain, metabolic syndrome, QT prolongation","warning": "Metabolic monitoring; QT risk; driving caution",  "dosage": "25–800mg daily (condition-dependent)"},
    "olanzapine":        {"use": "Schizophrenia, bipolar disorder, nausea (low dose)","side_effects": "Weight gain, metabolic syndrome, sedation",  "warning": "Significant metabolic risk; glucose/lipid monitoring","dosage": "5–20mg once daily"},
    "risperidone":       {"use": "Schizophrenia, bipolar disorder, autism agitation","side_effects": "EPS, hyperprolactinaemia, metabolic effects","warning": "EPS risk especially at high doses; prolactin monitoring","dosage": "2–16mg daily"},
    "haloperidol":       {"use": "Schizophrenia, acute agitation, delirium","side_effects": "Severe EPS, tardive dyskinesia, QT prolongation","warning": "High EPS risk; ECG monitoring; use lowest effective dose","dosage": "0.5–20mg daily"},
    "clozapine":         {"use": "Treatment-resistant schizophrenia",       "side_effects": "Agranulocytosis, metabolic syndrome, myocarditis","warning": "MANDATORY weekly/fortnightly FBC monitoring; registered patients only","dosage": "12.5–900mg daily (level-guided)"},
    "diazepam":          {"use": "Anxiety, alcohol withdrawal, muscle spasm, seizures","side_effects": "Sedation, dependence, respiratory depression","warning": "High dependence risk; avoid long-term; respiratory caution","dosage": "2–10mg 2–4 times daily"},
    "lorazepam":         {"use": "Anxiety, status epilepticus, sedation",   "side_effects": "Sedation, respiratory depression, dependence",  "warning": "High dependence risk; IV for emergency seizures",    "dosage": "0.5–4mg as needed"},
    "clonazepam":        {"use": "Epilepsy, panic disorder, anxiety",       "side_effects": "Sedation, dependence, coordination problems",   "warning": "Dependence risk; avoid alcohol; do not stop abruptly","dosage": "0.25–2mg as prescribed"},
    "zolpidem":          {"use": "Short-term insomnia",                     "side_effects": "Complex sleep behaviours, dependence, amnesia", "warning": "Max 4 weeks; avoid alcohol; sleep-driving risk",    "dosage": "5–10mg at bedtime"},
    "zopiclone":         {"use": "Short-term insomnia",                     "side_effects": "Metallic taste, dependence, amnesia",           "warning": "Max 4 weeks; avoid alcohol; dependence risk",       "dosage": "3.75–7.5mg at bedtime"},
    "phenytoin":         {"use": "Epilepsy, status epilepticus",            "side_effects": "Gum hyperplasia, ataxia, diplopia, teratogenicity","warning": "Narrow therapeutic index; many drug interactions; monitor levels","dosage": "150–300mg daily (level-guided)"},
    "carbamazepine":     {"use": "Epilepsy, trigeminal neuralgia, bipolar","side_effects": "Hyponatraemia, rash (Stevens-Johnson risk), diplopia","warning": "HLA-B*1502 testing before use in Asian patients; many interactions","dosage": "200–1600mg daily in divided doses"},
    "valproate":         {"use": "Epilepsy, bipolar disorder, migraine prevention","side_effects": "Hepatotoxicity, teratogenicity, weight gain, tremor","warning": "ABSOLUTE contraindication in pregnancy; monthly LFTs initially","dosage": "500mg–2.5g daily in divided doses"},
    "lamotrigine":       {"use": "Epilepsy, bipolar disorder",              "side_effects": "Rash (Stevens-Johnson risk), headache, diplopia","warning": "Titrate slowly to prevent rash; adjust dose with valproate","dosage": "25–400mg daily (titrated)"},
    "levetiracetam":     {"use": "Epilepsy (adjunct)",                      "side_effects": "Irritability, mood changes, headache",          "warning": "Behavioural side effects — monitor closely; renal dose adjustment","dosage": "500mg–3g daily in 2 divided doses"},
    "pregabalin":        {"use": "Neuropathic pain, epilepsy, generalised anxiety","side_effects": "Sedation, weight gain, dizziness, dependence","warning": "Abuse potential; renal dose reduction; avoid abrupt stop","dosage": "75–600mg daily in 2–3 divided doses"},
    "gabapentin":        {"use": "Neuropathic pain, epilepsy",              "side_effects": "Sedation, dizziness, weight gain, abuse risk",  "warning": "Abuse/misuse potential; renal dose reduction required","dosage": "300mg–3.6g daily in 3 divided doses"},
    "donepezil":         {"use": "Alzheimer's disease",                     "side_effects": "Nausea, diarrhoea, vivid dreams, bradycardia", "warning": "Cholinergic effects; syncope risk; nightmares — take in morning if problematic","dosage": "5–10mg once daily"},
    "memantine":         {"use": "Moderate-severe Alzheimer's disease",     "side_effects": "Dizziness, headache, constipation",            "warning": "Adjust in renal impairment; titrate slowly",         "dosage": "5–20mg once daily"},
    "levodopa/carbidopa":{"use": "Parkinson's disease",                     "side_effects": "Dyskinesia, nausea, orthostatic hypotension, psychosis","warning": "Never stop abruptly (neuroleptic malignant-like syndrome); dietary protein timing","dosage": "As prescribed — titrated to effect"},

    # ── ALLERGY / IMMUNE ───────────────────────────────────────
    "cetirizine":        {"use": "Allergic rhinitis, urticaria, hay fever", "side_effects": "Mild sedation, dry mouth",                     "warning": "Less sedating than older antihistamines; caution driving","dosage": "10mg once daily"},
    "loratadine":        {"use": "Allergic rhinitis, urticaria (non-sedating)","side_effects": "Headache, dry mouth (minimal sedation)",     "warning": "Non-sedating; safe in most situations",              "dosage": "10mg once daily"},
    "fexofenadine":      {"use": "Allergic rhinitis, urticaria (non-sedating)","side_effects": "Headache, nausea",                          "warning": "Non-sedating; no significant interactions",          "dosage": "120–180mg once daily"},
    "chlorphenamine":    {"use": "Allergy, anaphylaxis (adjunct), pruritus","side_effects": "Significant sedation, dry mouth, urinary retention","warning": "Sedating — do not drive; avoid in elderly",         "dosage": "4mg every 4–6 hrs"},
    "hydroxyzine":       {"use": "Anxiety, pruritus, allergy, pre-operative sedation","side_effects": "Sedation, dry mouth, QT prolongation","warning": "QT monitoring; sedating; avoid in elderly",          "dosage": "25–100mg up to 4 times daily"},
    "prednisolone":      {"use": "Severe allergic reactions, asthma, autoimmune","side_effects": "See respiratory section",                  "warning": "See respiratory section",                            "dosage": "See respiratory section"},
    "adrenaline (epinephrine)": {"use": "Anaphylaxis, cardiac arrest, severe asthma","side_effects": "Tachycardia, hypertension, anxiety",   "warning": "IM for anaphylaxis; life-saving — use immediately; store correctly","dosage": "0.5mg IM (500mcg, 1:1000) for anaphylaxis"},
    "methotrexate":      {"use": "RA, psoriasis, some cancers, ectopic pregnancy","side_effects": "Hepatotoxicity, bone marrow suppression, pulmonary fibrosis","warning": "WEEKLY dose — daily dosing is fatal; folic acid required; contraception mandatory","dosage": "7.5–25mg ONCE WEEKLY (RA/psoriasis)"},
    "hydroxychloroquine":{"use": "RA, SLE, malaria prevention",             "side_effects": "Retinopathy, GI upset, QT prolongation",       "warning": "Annual eye screening; QT monitoring; safe in pregnancy for SLE","dosage": "200–400mg once daily"},
    "azathioprine":      {"use": "Organ transplant rejection, autoimmune disease","side_effects": "Bone marrow suppression, hepatotoxicity, lymphoma risk","warning": "TPMT testing before use; avoid with allopurinol",  "dosage": "1–3mg/kg daily"},

    # ── GOUT / URIC ACID ──────────────────────────────────────
    "allopurinol":       {"use": "Gout prevention, hyperuricaemia",         "side_effects": "Rash (Stevens-Johnson risk), hepatotoxicity",  "warning": "HLA-B*5801 test in South-East Asians; never start during acute gout", "dosage": "100–300mg once daily"},
    "colchicine":        {"use": "Acute gout, FMF, pericarditis",           "side_effects": "GI upset, bone marrow suppression",           "warning": "Narrow therapeutic index; reduce dose in renal failure; CYP3A4 interactions", "dosage": "500mcg 2–3 times daily"},
    "febuxostat":        {"use": "Gout prevention (xanthine oxidase inhibitor)","side_effects": "Liver enzyme elevation, cardiovascular risk","warning": "Cardiovascular risk — avoid in ischaemic heart disease if possible","dosage": "80–120mg once daily"},

    # ── OPHTHALMOLOGY ──────────────────────────────────────────
    "latanoprost":       {"use": "Glaucoma, ocular hypertension",           "side_effects": "Iris colour change, eyelash growth, redness",  "warning": "Apply at night; may change eye colour permanently",  "dosage": "1 drop once daily (evening)"},
    "timolol (eye drops)":{"use": "Glaucoma (beta-blocker eye drop)",       "side_effects": "Bradycardia, bronchospasm (systemic absorption)","warning": "Systemic absorption — avoid in asthma/heart block","dosage": "1 drop twice daily"},

    # ── OSTEOPOROSIS / BONE ────────────────────────────────────
    "alendronate":       {"use": "Osteoporosis prevention/treatment",       "side_effects": "Oesophageal irritation, atypical femoral fracture","warning": "Take fasting with full glass water; remain upright 30 min; dental check before starting","dosage": "10mg daily or 70mg once weekly"},
    "calcium + vitamin D":{"use": "Osteoporosis adjunct, vitamin D deficiency","side_effects": "Constipation, hypercalcaemia",              "warning": "Monitor calcium; separate from other medications by 2 hrs","dosage": "1000–1200mg calcium + 400–1000IU vit D daily"},

    # ── HORMONES / CONTRACEPTION ───────────────────────────────
    "combined oral contraceptive": {"use": "Contraception, endometriosis, acne","side_effects": "VTE, hypertension, nausea, breast tenderness","warning": "VTE risk especially with factor V Leiden; avoid in migraines with aura; smokers >35","dosage": "1 tablet daily for 21 days, 7-day break"},
    "progesterone-only pill": {"use": "Contraception (progestogen-only)",   "side_effects": "Irregular bleeding, breast tenderness",         "warning": "Take at same time daily (within 3-hr window for some); no oestrogen-related VTE risk","dosage": "1 tablet daily continuously"},
    "medroxyprogesterone": {"use": "Contraception, HRT, endometriosis",     "side_effects": "Irregular bleeding, weight gain, bone density loss","warning": "Bone density loss with long-term use; return to fertility may be delayed","dosage": "150mg IM every 12 weeks (contraception)"},
    "tamoxifen":         {"use": "Oestrogen receptor-positive breast cancer","side_effects": "Hot flushes, VTE, endometrial cancer risk, mood changes","warning": "VTE risk; endometrial monitoring; avoid in pregnancy","dosage": "20mg once daily"},
    "testosterone":      {"use": "Hypogonadism, gender-affirming therapy",  "side_effects": "Polycythaemia, acne, prostate growth, cardiovascular risk","warning": "Monitor haematocrit, PSA; cardiovascular monitoring","dosage": "As prescribed (gel, injection, or patch)"},

    # ── MISCELLANEOUS ──────────────────────────────────────────
    "folic acid":        {"use": "Megaloblastic anaemia, pregnancy (neural tube defect prevention)","side_effects": "Rarely: GI upset",         "warning": "5mg dose required with methotrexate; 400mcg for pregnancy","dosage": "400mcg daily (pregnancy), 5mg daily (deficiency/MTX)"},
    "ferrous sulfate":   {"use": "Iron deficiency anaemia",                 "side_effects": "GI upset, black stools, constipation",         "warning": "Take on empty stomach if tolerated; keep away from children (lethal in overdose)","dosage": "200mg 2–3 times daily"},
    "vitamin B12":       {"use": "B12 deficiency, pernicious anaemia",      "side_effects": "Minimal — acne with high doses",               "warning": "IM injection needed in pernicious anaemia (not absorbed orally)","dosage": "1mg IM every 3 months (maintenance)"},
    "allopurinol":       {"use": "Gout prevention",                         "side_effects": "Rash",                                         "warning": "HLA-B*5801 screening in at-risk populations",        "dosage": "100–300mg once daily"},
    "sildenafil":        {"use": "Erectile dysfunction, pulmonary arterial hypertension","side_effects": "Flushing, headache, visual disturbance, hypotension","warning": "NEVER with nitrates — fatal hypotension; caution in cardiovascular disease","dosage": "25–100mg 1 hr before sexual activity"},
    "finasteride":       {"use": "Benign prostatic hyperplasia, male pattern baldness","side_effects": "Sexual dysfunction, gynaecomastia, depression risk","warning": "Teratogenic to male foetuses — pregnant women must not handle crushed tablets","dosage": "5mg once daily (BPH); 1mg daily (baldness)"},
    "tamsulosin":        {"use": "Benign prostatic hyperplasia",            "side_effects": "Postural hypotension, retrograde ejaculation, rhinitis","warning": "First-dose hypotension; caution before cataract surgery (IFIS)","dosage": "400mcg once daily after breakfast"},
    "zoledronic acid":   {"use": "Osteoporosis, bone metastases, Paget's disease","side_effects": "Flu-like symptoms, osteonecrosis of jaw, hypocalcaemia","warning": "Adequate calcium/vit D before infusion; dental check; renal monitoring","dosage": "4–5mg IV once yearly (osteoporosis)"},
    "desmopressin":      {"use": "Diabetes insipidus, nocturnal enuresis, von Willebrand disease","side_effects": "Hyponatraemia, headache",           "warning": "Restrict fluid intake to prevent dilutional hyponatraemia","dosage": "0.1–0.4mg daily (DI)"},
    "methylphenidate":   {"use": "ADHD, narcolepsy",                        "side_effects": "Appetite suppression, insomnia, tachycardia, hypertension","warning": "Monitor growth in children; cardiovascular monitoring; controlled substance","dosage": "5–60mg daily in divided doses"},
    "atomoxetine":       {"use": "ADHD (non-stimulant)",                    "side_effects": "Appetite suppression, hepatotoxicity, suicidal ideation (children)","warning": "Monitor LFTs; behavioural monitoring in children/adolescents","dosage": "40–100mg daily"},
    "melatonin":         {"use": "Insomnia, jet lag, delayed sleep phase",  "side_effects": "Drowsiness, headache, dizziness",              "warning": "Short-term use; caution in autoimmune conditions",   "dosage": "0.5–5mg 30–60 min before bedtime"},
    "caffeine":          {"use": "Apnoea of prematurity, migraine adjunct, alertness","side_effects": "Tachycardia, anxiety, insomnia",             "warning": "High intake worsens anxiety and arrhythmia; withdrawal headache","dosage": "Variable"},
    "naloxone":          {"use": "Opioid overdose reversal",                "side_effects": "Acute opioid withdrawal, tachycardia, hypertension","warning": "Short duration — repeat dosing may be needed; monitor carefully","dosage": "0.4–2mg IV/IM/SC; repeat every 2–3 min"},
    "naltrexone":        {"use": "Alcohol/opioid dependence",               "side_effects": "Nausea, hepatotoxicity, withdrawal symptoms if opioid-dependent","warning": "Patient must be opioid-free for ≥7 days before starting","dosage": "25–50mg once daily (alcohol); 50mg daily (opioid)"},
    "disulfiram":        {"use": "Alcohol dependence (aversion therapy)",   "side_effects": "Disulfiram-alcohol reaction (severe), hepatotoxicity","warning": "Patient must avoid ALL alcohol sources including mouthwash and sauces","dosage": "200–500mg once daily"},
    "ivermectin":        {"use": "Parasitic infections (scabies, onchocerciasis, strongyloides)","side_effects": "Dizziness, rash, Mazzotti reaction","warning": "Mazzotti reaction in onchocerciasis; avoid in meningitis-risk patients","dosage": "200mcg/kg single dose (scabies)"},
    "chloroquine":       {"use": "Malaria prevention/treatment, SLE, RA",  "side_effects": "Retinopathy, QT prolongation, GI upset",       "warning": "Annual eye screening; QT monitoring; resistance common in many regions","dosage": "250–500mg weekly (prophylaxis)"},
    "quinine":           {"use": "Malaria treatment, nocturnal leg cramps","side_effects": "Cinchonism (tinnitus, dizziness), QT prolongation","warning": "QT risk; avoid in G6PD deficiency; hypoglycaemia risk","dosage": "600mg every 8 hrs for 7 days (malaria)"},
}

medicine_list = sorted(drug_info.keys())

drug_interactions = {
    # ── BLEEDING RISKS ────────────────────────────────────────
    ("aspirin", "ibuprofen"):             ("danger",  "Combined NSAIDs: greatly increased GI bleeding and cardiovascular risk."),
    ("aspirin", "naproxen"):              ("danger",  "Combined NSAIDs: greatly increased GI bleeding risk."),
    ("aspirin", "diclofenac"):            ("danger",  "Combined NSAIDs: greatly increased GI and cardiovascular risk."),
    ("aspirin", "warfarin"):              ("danger",  "Very high bleeding risk — serious haemorrhage possible."),
    ("aspirin", "clopidogrel"):           ("warning", "Dual antiplatelet: increased bleeding risk; sometimes intentional in ACS — confirm with prescriber."),
    ("aspirin", "ticagrelor"):            ("warning", "Dual antiplatelet: use only low-dose aspirin (≤100mg); high-dose aspirin reduces ticagrelor efficacy."),
    ("aspirin", "apixaban"):              ("warning", "Increased bleeding risk — avoid unless clearly indicated."),
    ("aspirin", "rivaroxaban"):           ("warning", "Increased bleeding risk — avoid unless clearly indicated."),
    ("aspirin", "enoxaparin"):            ("warning", "Increased bleeding risk — monitor closely."),
    ("warfarin", "ibuprofen"):            ("danger",  "Significantly increased bleeding risk — NSAIDs displace warfarin and irritate GI mucosa."),
    ("warfarin", "naproxen"):             ("danger",  "Significantly increased bleeding risk — avoid combination."),
    ("warfarin", "diclofenac"):           ("danger",  "High bleeding risk — NSAIDs and warfarin are a dangerous combination."),
    ("warfarin", "aspirin"):              ("danger",  "Very high bleeding risk — avoid unless absolutely necessary with close INR monitoring."),
    ("warfarin", "ciprofloxacin"):        ("danger",  "Ciprofloxacin markedly increases warfarin effect — monitor INR closely."),
    ("warfarin", "clarithromycin"):       ("danger",  "Clarithromycin inhibits warfarin metabolism — significant INR rise."),
    ("warfarin", "metronidazole"):        ("danger",  "Metronidazole doubles warfarin effect — INR can become dangerously high."),
    ("warfarin", "fluconazole"):          ("danger",  "Fluconazole markedly potentiates warfarin — serious bleeding risk."),
    ("warfarin", "amiodarone"):           ("danger",  "Amiodarone dramatically potentiates warfarin effect — may persist weeks after stopping."),
    ("warfarin", "rifampicin"):           ("danger",  "Rifampicin is a potent enzyme inducer — dramatically reduces warfarin levels."),
    ("warfarin", "carbamazepine"):        ("danger",  "Carbamazepine induces warfarin metabolism — reduced anticoagulant effect."),
    ("warfarin", "phenytoin"):            ("warning", "Complex bidirectional interaction — unpredictable INR changes; monitor closely."),
    ("warfarin", "clopidogrel"):          ("danger",  "Triple risk: anticoagulant + antiplatelet — high haemorrhage risk."),
    ("warfarin", "omeprazole"):           ("warning", "Omeprazole can slightly increase warfarin levels — monitor INR."),
    ("warfarin", "sertraline"):           ("warning", "SSRIs inhibit platelet aggregation — increased bleeding with anticoagulants."),
    ("warfarin", "simvastatin"):          ("warning", "Simvastatin can increase warfarin effect at higher doses — monitor INR."),
    ("clopidogrel", "omeprazole"):        ("warning", "Omeprazole reduces clopidogrel activation (CYP2C19 inhibition) — reduced antiplatelet effect. Use pantoprazole instead."),
    ("apixaban", "ibuprofen"):            ("warning", "Increased bleeding risk — avoid NSAIDs with DOACs."),
    ("rivaroxaban", "ibuprofen"):         ("warning", "Increased bleeding risk — avoid NSAIDs with DOACs."),
    ("dabigatran", "ibuprofen"):          ("warning", "Increased bleeding risk — avoid NSAIDs with DOACs."),

    # ── SEROTONIN SYNDROME ────────────────────────────────────
    ("sertraline", "tramadol"):           ("danger",  "Serotonin syndrome risk — potentially life-threatening; agitation, hyperthermia, tachycardia."),
    ("fluoxetine", "tramadol"):           ("danger",  "Serotonin syndrome risk — avoid combination."),
    ("venlafaxine", "tramadol"):          ("danger",  "Serotonin syndrome risk — avoid combination."),
    ("duloxetine", "tramadol"):           ("danger",  "Serotonin syndrome risk — avoid combination."),
    ("sertraline", "linezolid"):          ("danger",  "Linezolid is a MAOI — serotonin syndrome risk is severe; avoid."),
    ("fluoxetine", "linezolid"):          ("danger",  "Linezolid is a MAOI — serotonin syndrome risk; contraindicated."),
    ("venlafaxine", "linezolid"):         ("danger",  "Linezolid is a MAOI — serotonin syndrome risk; contraindicated."),
    ("sertraline", "morphine"):           ("warning", "Additive serotonin activity — monitor for serotonin syndrome symptoms."),
    ("tramadol", "codeine"):              ("warning", "Combined opioid effects — increased sedation and respiratory depression risk."),

    # ── QT PROLONGATION ───────────────────────────────────────
    ("azithromycin", "clarithromycin"):   ("danger",  "Combined QT prolongation — avoid; high arrhythmia risk."),
    ("azithromycin", "domperidone"):      ("danger",  "Combined QT prolongation — avoid."),
    ("azithromycin", "haloperidol"):      ("danger",  "Combined QT prolongation — avoid."),
    ("azithromycin", "ondansetron"):      ("warning", "Both prolong QT — use with caution; ECG monitoring."),
    ("clarithromycin", "domperidone"):    ("danger",  "Combined QT prolongation — contraindicated."),
    ("clarithromycin", "simvastatin"):    ("danger",  "Clarithromycin inhibits CYP3A4 — simvastatin levels rise dramatically — rhabdomyolysis risk."),
    ("clarithromycin", "atorvastatin"):   ("warning", "Clarithromycin raises atorvastatin levels — myopathy risk; use minimum statin dose."),
    ("escitalopram", "domperidone"):      ("warning", "Combined QT prolongation — avoid in cardiac patients."),
    ("citalopram", "domperidone"):        ("warning", "Combined QT prolongation — avoid."),
    ("haloperidol", "metoclopramide"):    ("warning", "Combined QT prolongation and additive dopamine blockade."),
    ("ondansetron", "domperidone"):       ("warning", "Combined QT prolongation — avoid concurrent use."),
    ("ciprofloxacin", "domperidone"):     ("danger",  "Combined QT prolongation — avoid."),
    ("levofloxacin", "domperidone"):      ("danger",  "Combined QT prolongation — avoid."),
    ("sildenafil", "nitrate"):            ("danger",  "Fatal hypotension — absolute contraindication; never combine."),

    # ── CNS / SEDATION ────────────────────────────────────────
    ("diazepam", "codeine"):              ("danger",  "Profound respiratory depression — benzodiazepine + opioid is a fatal combination risk."),
    ("lorazepam", "codeine"):             ("danger",  "Profound respiratory depression — benzodiazepine + opioid is a fatal combination risk."),
    ("clonazepam", "codeine"):            ("danger",  "Profound respiratory depression — benzodiazepine + opioid is a fatal combination risk."),
    ("diazepam", "tramadol"):             ("danger",  "Combined CNS depression — respiratory depression risk."),
    ("zolpidem", "codeine"):              ("danger",  "Combined CNS/respiratory depression — avoid."),
    ("zopiclone", "codeine"):             ("danger",  "Combined CNS/respiratory depression — avoid."),
    ("diazepam", "alcohol"):              ("danger",  "Severe CNS and respiratory depression — potentially fatal."),
    ("lorazepam", "alcohol"):             ("danger",  "Severe CNS and respiratory depression — potentially fatal."),
    ("zolpidem", "alcohol"):              ("danger",  "Severe CNS depression — increased complex sleep behaviour risk."),
    ("clonazepam", "metoprolol"):         ("warning", "Additive BP lowering and sedation — monitor closely."),
    ("quetiapine", "codeine"):            ("warning", "Additive CNS depression and QT risk — monitor."),
    ("haloperidol", "codeine"):           ("warning", "Additive CNS depression — monitor."),
    ("mirtazapine", "tramadol"):          ("warning", "Serotonin syndrome risk and additive sedation."),
    ("amitriptyline", "tramadol"):        ("warning", "Serotonin syndrome risk and additive CNS depression."),
    ("gabapentin", "codeine"):            ("danger",  "Gabapentin dramatically potentiates opioid respiratory depression — avoid or monitor very closely."),
    ("pregabalin", "codeine"):            ("danger",  "Pregabalin dramatically potentiates opioid respiratory depression — avoid or monitor very closely."),
    ("gabapentin", "morphine"):           ("danger",  "Combined respiratory depression — serious safety concern."),

    # ── CARDIOVASCULAR / BP ───────────────────────────────────
    ("metoprolol", "verapamil"):          ("danger",  "Combined beta-blocker + calcium channel blocker — severe bradycardia and heart block risk; contraindicated."),
    ("atenolol", "verapamil"):            ("danger",  "Combined beta-blocker + calcium channel blocker — severe bradycardia and heart block; avoid."),
    ("metoprolol", "diltiazem"):          ("warning", "Bradycardia and heart block risk — monitor ECG and heart rate closely."),
    ("bisoprolol", "verapamil"):          ("danger",  "Severe bradycardia and heart block risk — contraindicated."),
    ("lisinopril", "spironolactone"):     ("warning", "Severe hyperkalaemia risk — monitor potassium closely."),
    ("ramipril", "spironolactone"):       ("warning", "Severe hyperkalaemia risk — monitor potassium closely."),
    ("lisinopril", "potassium"):          ("warning", "Hyperkalaemia risk — ACE inhibitors raise potassium."),
    ("losartan", "spironolactone"):       ("warning", "Severe hyperkalaemia risk — monitor potassium."),
    ("furosemide", "gentamicin"):         ("danger",  "Combined ototoxicity and nephrotoxicity — avoid if possible."),
    ("furosemide", "metformin"):          ("warning", "Dehydration increases lactic acidosis risk with metformin."),
    ("simvastatin", "amlodipine"):        ("warning", "Amlodipine raises simvastatin levels — max 20mg simvastatin with amlodipine 10mg."),
    ("simvastatin", "clarithromycin"):    ("danger",  "Clarithromycin dramatically raises simvastatin — rhabdomyolysis; suspend statin during course."),
    ("simvastatin", "itraconazole"):      ("danger",  "Itraconazole dramatically raises simvastatin — suspend statin during treatment."),
    ("atorvastatin", "itraconazole"):     ("warning", "Itraconazole raises atorvastatin — use minimum dose; monitor for myopathy."),
    ("rosuvastatin", "fenofibrate"):      ("warning", "Increased myopathy risk — monitor for muscle pain."),
    ("spironolactone", "nsaid"):          ("warning", "NSAIDs can reduce diuretic effect and increase hyperkalaemia risk."),

    # ── DIABETES / GLUCOSE ────────────────────────────────────
    ("metformin", "alcohol"):             ("warning", "Increases lactic acidosis risk — advise abstinence."),
    ("metformin", "contrast media"):      ("warning", "Hold metformin before and 48 hrs after iodinated contrast — acute kidney injury risk."),
    ("glibenclamide", "ciprofloxacin"):   ("warning", "Ciprofloxacin can cause hypoglycaemia with sulphonylureas — monitor glucose."),
    ("gliclazide", "fluconazole"):        ("warning", "Fluconazole inhibits sulphonylurea metabolism — hypoglycaemia risk."),
    ("glimepiride", "fluconazole"):       ("warning", "Fluconazole inhibits sulphonylurea metabolism — hypoglycaemia risk."),
    ("metformin", "furosemide"):          ("warning", "Dehydration from furosemide increases lactic acidosis risk."),
    ("insulin glargine", "metoprolol"):   ("warning", "Beta-blockers mask hypoglycaemia signs — monitor glucose more carefully."),
    ("insulin glargine", "alcohol"):      ("warning", "Alcohol potentiates insulin hypoglycaemia — educate patient."),

    # ── ANTIBIOTICS / OTHER ───────────────────────────────────
    ("azithromycin", "warfarin"):         ("warning", "Azithromycin can increase warfarin effect — monitor INR."),
    ("metronidazole", "alcohol"):         ("danger",  "Disulfiram-like reaction — severe flushing, vomiting, hypotension."),
    ("metronidazole", "warfarin"):        ("danger",  "Metronidazole markedly potentiates warfarin — high haemorrhage risk."),
    ("rifampicin", "combined oral contraceptive"): ("danger", "Rifampicin dramatically reduces contraceptive pill levels — use additional contraception for 4 weeks after completing course."),
    ("rifampicin", "warfarin"):           ("danger",  "Rifampicin is a powerful inducer — drastically reduces warfarin levels."),
    ("rifampicin", "methadone"):          ("danger",  "Rifampicin reduces methadone to sub-therapeutic levels — withdrawal risk."),
    ("ciprofloxacin", "antacid"):         ("warning", "Antacids chelate ciprofloxacin — separate by at least 2 hrs."),
    ("doxycycline", "antacid"):           ("warning", "Antacids and iron reduce doxycycline absorption — separate by 2 hrs."),
    ("metronidazole", "lithium"):         ("warning", "Metronidazole can raise lithium levels — toxicity risk."),

    # ── EPILEPSY / PSYCHOTROPICS ──────────────────────────────
    ("valproate", "lamotrigine"):         ("warning", "Valproate doubles lamotrigine levels — halve lamotrigine dose when adding valproate."),
    ("carbamazepine", "combined oral contraceptive"): ("danger", "Carbamazepine reduces contraceptive pill levels — unintended pregnancy risk; use additional contraception."),
    ("carbamazepine", "simvastatin"):     ("warning", "Carbamazepine reduces statin levels — reduced lipid-lowering effect."),
    ("carbamazepine", "warfarin"):        ("danger",  "Carbamazepine induces warfarin metabolism — INR drops."),
    ("phenytoin", "warfarin"):            ("warning", "Complex unpredictable interaction — careful INR and phenytoin monitoring."),
    ("phenytoin", "combined oral contraceptive"): ("danger", "Phenytoin reduces contraceptive levels — additional contraception needed."),
    ("lithium", "ibuprofen"):             ("danger",  "NSAIDs raise lithium levels — toxicity risk (tremor, confusion, seizures)."),
    ("lithium", "naproxen"):              ("danger",  "NSAIDs raise lithium levels — toxicity risk."),
    ("lithium", "diclofenac"):            ("danger",  "NSAIDs raise lithium levels — avoid; use paracetamol instead."),
    ("lithium", "thiazide"):              ("danger",  "Thiazides raise lithium levels — toxicity risk."),
    ("lithium", "metronidazole"):         ("warning", "Metronidazole can raise lithium — monitor levels."),
    ("haloperidol", "lithium"):           ("warning", "Increased neurotoxicity risk — monitor closely."),
    ("olanzapine", "valproate"):          ("warning", "Valproate may reduce olanzapine levels; both increase weight/metabolic risk."),
    ("clozapine", "ciprofloxacin"):       ("danger",  "Ciprofloxacin raises clozapine levels markedly — toxicity and agranulocytosis risk."),
    ("clozapine", "valproate"):           ("warning", "Both lower seizure threshold; increased risk."),

    # ── IMMUNOSUPPRESSANTS / TRANSPLANT ───────────────────────
    ("azathioprine", "allopurinol"):      ("danger",  "Allopurinol inhibits azathioprine metabolism — severe bone marrow suppression; reduce azathioprine to 25% of dose."),
    ("methotrexate", "ibuprofen"):        ("danger",  "NSAIDs reduce methotrexate excretion — severe toxicity risk; avoid."),
    ("methotrexate", "trimethoprim"):     ("danger",  "Combined folate antagonists — severe bone marrow suppression; avoid."),
    ("methotrexate", "aspirin"):          ("danger",  "Aspirin increases methotrexate toxicity — avoid."),

    # ── GOUT ──────────────────────────────────────────────────
    ("allopurinol", "azathioprine"):      ("danger",  "Allopurinol inhibits azathioprine metabolism — dose must be reduced to 25%; life-threatening if not."),
    ("colchicine", "clarithromycin"):     ("danger",  "Clarithromycin raises colchicine to toxic levels — life-threatening; avoid."),
    ("colchicine", "ciprofloxacin"):      ("warning", "Ciprofloxacin may increase colchicine levels — monitor for toxicity."),

    # ── RESPIRATORY / ASTHMA ──────────────────────────────────
    ("propranolol", "salbutamol"):        ("danger",  "Non-selective beta-blocker blocks salbutamol — can cause severe bronchospasm in asthma."),
    ("atenolol", "salbutamol"):           ("warning", "Beta-blockers reduce salbutamol bronchodilation — avoid in asthma."),
    ("theophylline", "ciprofloxacin"):    ("danger",  "Ciprofloxacin raises theophylline to toxic levels — seizures and arrhythmia risk."),
    ("theophylline", "clarithromycin"):   ("danger",  "Clarithromycin raises theophylline — toxicity risk."),

    # ── THYROID ────────────────────────────────────────────────
    ("levothyroxine", "metformin"):       ("info",    "Metformin may reduce levothyroxine effectiveness — monitor TSH."),
    ("levothyroxine", "calcium + vitamin d"): ("warning", "Calcium reduces levothyroxine absorption — separate by at least 4 hrs."),
    ("levothyroxine", "ferrous sulfate"): ("warning", "Iron reduces levothyroxine absorption — separate by at least 4 hrs."),
    ("levothyroxine", "omeprazole"):      ("warning", "PPIs reduce levothyroxine absorption — monitor TSH."),
    ("levothyroxine", "warfarin"):        ("warning", "Levothyroxine potentiates warfarin — monitor INR when thyroid dose changes."),
    ("carbimazole", "warfarin"):          ("warning", "Treating hyperthyroidism alters warfarin requirements — monitor INR carefully."),

    # ── GI / PPI INTERACTIONS ─────────────────────────────────
    ("clopidogrel", "omeprazole"):        ("warning", "Omeprazole inhibits CYP2C19 — reduces clopidogrel to active form; use pantoprazole instead."),
    ("clopidogrel", "esomeprazole"):      ("warning", "As with omeprazole — reduced clopidogrel activation; use pantoprazole."),

    # ── ERECTILE / HORMONAL ───────────────────────────────────
    ("sildenafil", "amlodipine"):         ("warning", "Additive hypotension — monitor blood pressure."),
    ("sildenafil", "doxazosin"):          ("warning", "Additive hypotension — significant BP drop risk."),
    ("tamoxifen", "fluoxetine"):          ("danger",  "Fluoxetine inhibits CYP2D6 — reduces tamoxifen to active metabolite; use a different antidepressant."),
    ("tamoxifen", "paroxetine"):          ("danger",  "Paroxetine is the strongest CYP2D6 inhibitor — dramatically reduces tamoxifen efficacy."),
    ("combined oral contraceptive", "rifampicin"): ("danger", "Rifampicin renders the pill ineffective — additional contraception needed."),
    ("combined oral contraceptive", "carbamazepine"): ("danger", "Carbamazepine renders the pill less effective — use additional contraception."),
    ("combined oral contraceptive", "lamotrigine"): ("warning", "Combined pill reduces lamotrigine levels significantly — seizure risk; monitor levels."),

    # ── ALCOHOL ───────────────────────────────────────────────
    ("alcohol", "metronidazole"):         ("danger",  "Disulfiram-like reaction — severe nausea, vomiting, flushing, hypotension."),
    ("alcohol", "metformin"):             ("warning", "Increased lactic acidosis risk."),
    ("alcohol", "diazepam"):              ("danger",  "Severe CNS and respiratory depression — potentially fatal."),
    ("alcohol", "paracetamol"):           ("warning", "Increases hepatotoxicity risk — especially with chronic heavy drinking."),
    ("alcohol", "warfarin"):              ("warning", "Alcohol can unpredictably alter INR — avoid regular heavy drinking."),
    ("disulfiram", "alcohol"):            ("danger",  "Intentional reaction: severe flushing, vomiting, hypotension; any alcohol source triggers it."),
}

# ── HELPERS ─────────────────────────────────────────────────

def sanitize(text, n=500):
    return re.sub(r"[^\w\s,.' \-()]", " ", text)[:n].strip()

def profile_text(p):
    if not p:
        return "No medical history provided."
    lines = []
    if p.get("name"):          lines.append("Patient: " + p["name"] + ", Age " + str(p.get("age","?")) + ", " + p.get("gender",""))
    if p.get("conditions"):    lines.append("Conditions: " + ", ".join(p["conditions"]))
    if p.get("allergies"):     lines.append("Drug allergies: " + ", ".join(p["allergies"]))
    if p.get("surgeries"):     lines.append("Surgeries: " + p["surgeries"])
    if p.get("genetic"):       lines.append("Genetic conditions: " + p["genetic"])
    if p.get("accidents"):     lines.append("Injuries: " + p["accidents"])
    if p.get("current_meds"):  lines.append("Currently taking: " + ", ".join(p["current_meds"]))
    if p.get("other_meds"):    lines.append("Other medicines: " + p["other_meds"])
    return "\n".join(lines)

def check_pairs(meds):
    results = []
    seen = set()
    meds_l = [m.lower() for m in meds if m]
    for i in range(len(meds_l)):
        for j in range(i+1, len(meds_l)):
            a, b = meds_l[i], meds_l[j]
            key = (min(a,b), max(a,b))
            if key in seen:
                continue
            seen.add(key)
            if a == b:
                results.append({"a":a,"b":b,"level":"warning","msg":"Same medicine added twice."})
            elif (a,b) in drug_interactions:
                lv,msg = drug_interactions[(a,b)]
                results.append({"a":a,"b":b,"level":lv,"msg":msg})
            elif (b,a) in drug_interactions:
                lv,msg = drug_interactions[(b,a)]
                results.append({"a":a,"b":b,"level":lv,"msg":msg})
            else:
                results.append({"a":a,"b":b,"level":"ok","msg":"No major known interaction found."})
    return results

def ask_ai(prompt):
    if not client:
        return "AI unavailable — API key not set."
    try:
        r = client.chat.completions.create(
            model="qwen/qwen3-8b:free",
            messages=[{"role":"user","content":prompt}]
        )
        return r.choices[0].message.content
    except Exception as e:
        return "AI error: " + str(e)

def ai_explain(med):
    prompt = (
        "Explain the medicine " + med + " in simple plain English. "
        "Cover: (1) uses, (2) common side effects, (3) key warnings. "
        "Under 150 words. End with: Always consult your doctor or pharmacist before use."
    )
    return ask_ai(prompt)

def ai_safety(med, profile):
    prompt = (
        "You are a clinical pharmacist assistant. A patient wants to take " + med + ".\n\n"
        "Patient background:\n" + profile_text(profile) + "\n\n"
        "1. State clearly: SAFE / USE WITH CAUTION / AVOID for this specific patient.\n"
        "2. Explain why, referencing their conditions, allergies, or current medications.\n"
        "3. If caution or avoid, suggest 1-2 safer alternatives.\n"
        "Under 200 words. End with: This is AI-generated. Always confirm with your doctor or pharmacist."
    )
    return ask_ai(prompt)

def ai_health(age, symptoms, profile):
    prompt = (
        "Patient age: " + str(age) + "\n"
        "Symptoms: " + sanitize(symptoms) + "\n\n"
        "Medical background:\n" + profile_text(profile) + "\n\n"
        "Give simple safe health advice tailored to this patient. "
        "Do NOT diagnose. Recommend seeing a doctor if symptoms are serious. "
        "End with: This is general information only — please see a qualified healthcare professional."
    )
    return ask_ai(prompt)

def ai_interactions(meds, profile):
    prompt = (
        "Patient background:\n" + profile_text(profile) + "\n\n"
        "Patient wants to take: " + ", ".join(meds) + "\n\n"
        "1. List clinically significant interactions between these medicines.\n"
        "2. Flag any risky given the patient's conditions or current medications.\n"
        "3. State severity (mild/moderate/severe) and reason for each.\n"
        "Under 200 words. End with: Always consult your pharmacist before combining medicines."
    )
    return ask_ai(prompt)

def footer():
    st.markdown("---")
    st.markdown(
        "<div style='text-align:center;padding:8px 0 4px'>"
        "<span style='font-size:12px;color:#a1a1a6'>"
        "MedHelix &nbsp;·&nbsp; For informational use only &nbsp;·&nbsp; "
        "Not a substitute for medical advice"
        "</span><br>"
        "<span style='font-size:13px;font-weight:500;color:#6e6e73'>Made by Sagar</span>"
        "</div>",
        unsafe_allow_html=True
    )

def hero(eyebrow, title, bold_part, subtitle):
    st.markdown(
        "<div style='margin-bottom:20px'>"
        "<div style='font-size:11px;font-weight:500;letter-spacing:.06em;text-transform:uppercase;"
        "color:#0071e3;margin-bottom:5px'>" + eyebrow + "</div>"
        "<div style='font-size:26px;font-weight:600;letter-spacing:-.5px;margin-bottom:5px'>"
        + bold_part + " <span style='font-weight:300'>" + title + "</span></div>"
        "<div style='font-size:14px;color:#6e6e73'>" + subtitle + "</div>"
        "</div>",
        unsafe_allow_html=True
    )

def info_card(html_content):
    st.markdown(
        "<div style='background:rgba(255,255,255,.82);backdrop-filter:blur(20px);"
        "border:.5px solid rgba(0,0,0,.08);border-radius:16px;padding:22px 24px;"
        "box-shadow:0 4px 16px rgba(0,0,0,.07);margin-bottom:14px'>"
        + html_content + "</div>",
        unsafe_allow_html=True
    )

# ── CONDITIONS / ALLERGIES LISTS ─────────────────────────────
CONDITIONS_LIST = [
    "Diabetes (Type 1)","Diabetes (Type 2)","Hypertension","Asthma","COPD",
    "Kidney Disease","Liver Disease / Cirrhosis","Heart Disease / CAD",
    "Heart Failure","Thyroid Disorder","Epilepsy / Seizure Disorder",
    "Stroke History","Cancer","HIV/AIDS","Autoimmune Disease",
    "Anaemia","Osteoporosis","Depression / Anxiety","GERD","Gout",
    "Psoriasis","Rheumatoid Arthritis","Bipolar Disorder","Schizophrenia",
]
ALLERGIES_LIST = [
    "Penicillin","Aspirin / NSAIDs","Sulfa Drugs","Codeine / Opioids",
    "Tetracycline","Erythromycin","Cephalosporins","ACE Inhibitors",
    "Statins","Metformin","Iodine / Contrast dye",
]


# ════════════════════════════════════════════════════════════
#  PAGE 1 — LOGIN
# ════════════════════════════════════════════════════════════

def page_login():
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown(
            "<div style='background:rgba(255,255,255,.85);backdrop-filter:blur(20px);"
            "border:.5px solid rgba(0,0,0,.08);border-radius:20px;padding:36px 28px;"
            "box-shadow:0 10px 40px rgba(0,0,0,.09);margin-top:60px'>"
            "<div style='width:50px;height:50px;border-radius:13px;background:#0071e3;"
            "display:flex;align-items:center;justify-content:center;font-size:22px;"
            "margin-bottom:18px'>&#x1F48A;</div>"
            "<div style='font-size:24px;font-weight:600;letter-spacing:-.4px;margin-bottom:5px'>"
            "MedHelix</div>"
            "<div style='font-size:14px;color:#6e6e73;margin-bottom:24px;line-height:1.5'>"
            "Your personal medicine safety assistant.<br>Sign in to get started.</div>"
            "</div>",
            unsafe_allow_html=True
        )
        st.markdown("")

        method = st.radio("Sign in with", ["Email", "Phone Number"], horizontal=True, label_visibility="collapsed")

        if method == "Email":
            val = st.text_input("Email address", placeholder="you@example.com")
            ok  = bool(val and re.match(r"[^@]+@[^@]+\.[^@]+", val))
            err = "Please enter a valid email address."
        else:
            val = st.text_input("Phone number", placeholder="+91 9876543210")
            ok  = bool(val and len(re.sub(r"[^\d]","",val)) >= 8)
            err = "Please enter a valid phone number (min 8 digits)."

        if st.button("Continue →", type="primary", use_container_width=True):
            if ok:
                st.session_state.logged_in = True
                st.session_state.user_id   = val
                st.session_state.page      = "profile_setup"
                st.rerun()
            else:
                st.error(err)

        st.markdown(
            "<p style='font-size:12px;color:#a1a1a6;text-align:center;margin-top:14px;line-height:1.5'>"
            "&#9877;&#65039; MedHelix is for informational purposes only.<br>"
            "Not a substitute for professional medical advice.</p>",
            unsafe_allow_html=True
        )


# ════════════════════════════════════════════════════════════
#  PAGE 2 — PROFILE SETUP
# ════════════════════════════════════════════════════════════

def page_profile_setup():
    st.markdown(
        "<div style='display:flex;align-items:center;gap:11px;margin-bottom:24px'>"
        "<div style='width:42px;height:42px;border-radius:11px;background:#0071e3;"
        "display:flex;align-items:center;justify-content:center;font-size:19px;flex-shrink:0'>"
        "&#x1F48A;</div>"
        "<div><div style='font-size:17px;font-weight:600;letter-spacing:-.3px'>One more step</div>"
        "<div style='font-size:13px;color:#6e6e73'>"
        "Complete your health profile for personalised safety advice</div></div></div>",
        unsafe_allow_html=True
    )

    with st.form("profile_form"):
        st.markdown("##### Basic Info")
        c1, c2 = st.columns(2)
        with c1:
            name   = st.text_input("Full Name", placeholder="Your name")
            age    = st.number_input("Age", 1, 120, value=25)
        with c2:
            gender = st.selectbox("Gender", ["Male","Female","Other"])
            blood  = st.selectbox("Blood Group", ["Unknown","A+","A-","B+","B-","AB+","AB-","O+","O-"])

        st.markdown("---")
        st.markdown("##### Chronic Conditions")
        conditions = st.multiselect("Select all that apply", CONDITIONS_LIST, label_visibility="collapsed")

        st.markdown("##### Known Drug Allergies")
        allergies = st.multiselect("Select all that apply", ALLERGIES_LIST, label_visibility="collapsed")

        st.markdown("---")
        st.markdown("##### Medical History")
        surgeries = st.text_area("Past Surgeries / Procedures",
            placeholder="e.g. Appendectomy (2018), Bypass surgery (2020)...")
        genetic   = st.text_area("Genetic / Hereditary Conditions",
            placeholder="e.g. G6PD deficiency, Sickle cell trait, Thalassaemia...")
        accidents = st.text_area("Accidents / Injuries with Lasting Effects",
            placeholder="e.g. Head injury (2019), Kidney damage from road accident...")

        st.markdown("---")
        st.markdown("##### Currently Taking (Long-term Medicines)")
        st.caption("Type 2–3 letters to search and select")
        current_meds = st.multiselect("Search medicines", medicine_list,
            placeholder="Start typing a medicine name...", label_visibility="collapsed")
        other_meds = st.text_input("Other medicines not in list",
            placeholder="e.g. Insulin glargine, Biologics...")

        submitted = st.form_submit_button("Save Profile & Enter App →", type="primary", use_container_width=True)

    if submitted:
        if not name.strip():
            st.error("Please enter your name to continue.")
        else:
            st.session_state.profile = {
                "name": name.strip(), "age": age, "gender": gender,
                "blood_group": blood, "conditions": conditions,
                "allergies": allergies, "surgeries": surgeries.strip(),
                "genetic": genetic.strip(), "accidents": accidents.strip(),
                "current_meds": current_meds, "other_meds": other_meds.strip(),
            }
            st.session_state.profile_complete = True
            st.session_state.page = "app"
            st.rerun()


# ════════════════════════════════════════════════════════════
#  PAGE 3 — MAIN APP
# ════════════════════════════════════════════════════════════

def page_app():
    profile = st.session_state.profile

    # ── Sidebar ───────────────────────────────────────────
    with st.sidebar:
        st.markdown(
            "<div style='display:flex;align-items:center;gap:8px;margin-bottom:10px'>"
            "<div style='width:28px;height:28px;border-radius:7px;background:#0071e3;"
            "display:flex;align-items:center;justify-content:center;font-size:13px'>&#x1F48A;</div>"
            "<span style='font-weight:600;font-size:16px;letter-spacing:-.3px'>MedHelix</span></div>",
            unsafe_allow_html=True
        )
        st.caption("Signed in as **" + st.session_state.user_id + "**")

        if profile:
            st.markdown("---")
            st.markdown("**" + profile.get("name","Patient") + "**")
            st.caption(
                "Age " + str(profile.get("age","–")) +
                " · " + profile.get("gender","–") +
                " · " + profile.get("blood_group","–")
            )
            if profile.get("conditions"):
                st.caption("📋 " + ", ".join(profile["conditions"]))
            if profile.get("allergies"):
                st.caption("⚠️ " + ", ".join(profile["allergies"]))
            if profile.get("current_meds"):
                st.caption("💊 " + ", ".join(profile["current_meds"]))

        st.markdown("---")
        st.caption(str(len(drug_info)) + " medicines · " + str(len(drug_interactions)) + " interactions")
        st.markdown("---")
        if st.button("Sign Out", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    # ── Disclaimer ────────────────────────────────────────
    st.markdown(
        "<div style='background:rgba(0,0,0,.03);border:.5px solid rgba(0,0,0,.08);"
        "border-radius:10px;padding:10px 15px;font-size:12px;color:#a1a1a6;"
        "line-height:1.5;margin-bottom:18px'>"
        "&#9877;&#65039; MedHelix is for general informational purposes only. "
        "Not a substitute for professional medical advice. "
        "Always consult a licensed doctor or pharmacist before taking any medication."
        "</div>",
        unsafe_allow_html=True
    )

    # ── Tab selector ──────────────────────────────────────
    tab = st.selectbox("", [
        "💊  Medicine Analyzer",
        "⚗️  Drug Interaction Checker",
        "🧠  AI Health Assistant",
        "👤  My Profile",
    ], label_visibility="collapsed")

    # ══════════════════════════════════════════════════════
    #  MEDICINE ANALYZER
    # ══════════════════════════════════════════════════════

    if "Medicine Analyzer" in tab:
        hero("Medicine Analyzer", "medicine", "Look up any", "Type 2–3 letters to filter. " + str(len(drug_info)) + " medicines in database.")

        if not st.session_state.profile_complete:
            st.info("💡 Complete your profile (👤 My Profile tab) to unlock personalised safety checks.")

        selected = st.selectbox(
            "Search medicine",
            medicine_list,
            index=None,
            placeholder="Type 2–3 letters — e.g. met, par, ibu, asp...",
            label_visibility="collapsed",
        )

        if selected:
            d = drug_info[selected]
            cat = d.get("category", d.get("cat", "Medicine"))

            st.markdown(
                "<span style='background:rgba(0,113,227,.08);color:#0071e3;"
                "border:.5px solid rgba(0,113,227,.2);border-radius:20px;"
                "padding:3px 11px;font-size:12px;font-weight:500'>" + cat + "</span>",
                unsafe_allow_html=True
            )
            st.markdown("### " + selected.capitalize())

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Uses",         d["use"])
            c2.metric("Side Effects", d["side_effects"])
            c3.metric("Dosage",       d["dosage"])
            c4.metric("Warning",      d["warning"])

            st.markdown("---")

            if st.session_state.profile_complete:
                st.markdown("#### 🔍 Personalised Safety Check")
                p = profile
                conds = ", ".join(p.get("conditions",[])) or "none"
                allgs = ", ".join(p.get("allergies",[])) or "none"
                cmeds = ", ".join(p.get("current_meds",[])) or "none"
                st.caption("Checking " + selected + " against — conditions: " + conds + " · allergies: " + allgs + " · current meds: " + cmeds)

                if st.button("Run Personalised Safety Check", type="primary"):
                    with st.spinner("Checking " + selected + " against your full medical history..."):
                        result = ai_safety(selected, profile)
                    lower = result.lower()
                    if any(w in lower for w in ["avoid","do not","contraindicated","dangerous","high risk"]):
                        st.error(result)
                    elif any(w in lower for w in ["caution","monitor","careful","risk"]):
                        st.warning(result)
                    else:
                        st.success(result)
                st.markdown("---")

            if st.button("🤖 General AI Explanation"):
                with st.spinner("Fetching explanation..."):
                    result = ai_explain(selected)
                st.info(result)
                st.caption("AI-generated. Always consult a healthcare professional.")

    # ══════════════════════════════════════════════════════
    #  DRUG INTERACTION CHECKER
    # ══════════════════════════════════════════════════════

    elif "Interaction" in tab:
        hero("Drug Interaction Checker", "combinations", "Check medicine", "Type 2–3 letters to search. Add up to 8 medicines.")

        # Search + add
        sc1, sc2 = st.columns([4, 1])
        with sc1:
            typed = st.selectbox(
                "Search",
                [""] + medicine_list,
                index=0,
                placeholder="Type medicine name — e.g. warfarin, asp, met...",
                label_visibility="collapsed",
                key="int_search",
            )
        with sc2:
            add_btn = st.button("＋ Add", use_container_width=True)

        if add_btn and typed:
            if typed in st.session_state.int_meds:
                st.warning(typed.capitalize() + " is already in your list.")
            elif len(st.session_state.int_meds) >= 8:
                st.error("Maximum 8 medicines at a time.")
            else:
                st.session_state.int_meds.append(typed)
                st.rerun()

        # Show selected + remove buttons
        if st.session_state.int_meds:
            chips = " ".join(
                "<span style='background:rgba(0,113,227,.08);color:#0071e3;"
                "border:.5px solid rgba(0,113,227,.2);border-radius:20px;"
                "padding:3px 11px;font-size:13px;font-weight:500;margin:2px;display:inline-block'>"
                + m.capitalize() + "</span>"
                for m in st.session_state.int_meds
            )
            st.markdown(
                "<div style='margin:10px 0 6px'><strong style='font-size:13px;color:#6e6e73'>"
                "Selected (" + str(len(st.session_state.int_meds)) + "/8):</strong>"
                "<div style='margin-top:7px'>" + chips + "</div></div>",
                unsafe_allow_html=True
            )

            n = len(st.session_state.int_meds)
            rm_cols = st.columns(min(n, 4))
            to_rm = None
            for i, m in enumerate(st.session_state.int_meds):
                with rm_cols[i % 4]:
                    if st.button("✕ " + m.capitalize(), key="rm_" + str(i), use_container_width=True):
                        to_rm = m
            if to_rm:
                st.session_state.int_meds.remove(to_rm)
                st.rerun()

            st.markdown("---")
            bc1, bc2 = st.columns([3, 1])
            with bc1:
                check_btn = st.button(
                    "🔍 Check All Interactions", type="primary",
                    use_container_width=True,
                    disabled=(len(st.session_state.int_meds) < 2)
                )
            with bc2:
                if st.button("Clear All", use_container_width=True):
                    st.session_state.int_meds = []
                    st.rerun()

            if check_btn and len(st.session_state.int_meds) >= 2:
                results = check_pairs(st.session_state.int_meds)
                d_n = sum(1 for r in results if r["level"]=="danger")
                w_n = sum(1 for r in results if r["level"]=="warning")
                o_n = sum(1 for r in results if r["level"]=="ok")

                st.markdown("#### Results")
                mc1, mc2, mc3 = st.columns(3)
                mc1.metric("🚨 Dangerous",     d_n)
                mc2.metric("⚠️ Warnings",      w_n)
                mc3.metric("✅ No interaction", o_n)
                st.markdown("---")

                for r in results:
                    label = "**" + r["a"].capitalize() + " + " + r["b"].capitalize() + "**"
                    if r["level"]   == "danger":  st.error("🚨 " + label + ": " + r["msg"])
                    elif r["level"] == "warning": st.warning("⚠️ " + label + ": " + r["msg"])
                    elif r["level"] == "info":    st.info("ℹ️ " + label + ": " + r["msg"])
                    else:                         st.success("✅ " + label + ": " + r["msg"])

                # Profile conflicts
                if profile.get("current_meds"):
                    st.markdown("---")
                    st.markdown("#### 🩺 Conflicts with Your Current Medications")
                    found = False
                    for nm in st.session_state.int_meds:
                        for ex in profile["current_meds"]:
                            if nm.lower() == ex.lower():
                                continue
                            a2, b2 = min(nm,ex), max(nm,ex)
                            if (a2,b2) in drug_interactions:
                                lv, msg = drug_interactions[(a2,b2)]
                                lbl = "**" + nm.capitalize() + "** + your current **" + ex.capitalize() + "**"
                                if lv=="danger": st.error("🚨 " + lbl + ": " + msg)
                                else: st.warning("⚠️ " + lbl + ": " + msg)
                                found = True
                    if not found:
                        st.success("✅ No known conflicts with your current medications.")

                st.markdown("---")
                st.markdown("#### 🤖 AI Deep-Dive Analysis (Personalised)")
                with st.spinner("Running AI analysis..."):
                    ai_res = ai_interactions(st.session_state.int_meds, profile)
                st.info(ai_res)
                st.caption("AI-generated. Does not replace pharmacist or doctor review.")
        else:
            st.info("👆 Search and add at least 2 medicines above to check interactions.")

    # ══════════════════════════════════════════════════════
    #  AI HEALTH ASSISTANT
    # ══════════════════════════════════════════════════════

    elif "Health Assistant" in tab:
        hero("AI Health Assistant", "symptoms", "Describe your", "Your medical history is automatically included for context.")

        ac1, ac2 = st.columns([1, 3])
        with ac1:
            age = st.number_input("Age", 1, 120,
                value=int(profile.get("age", 30)) if profile else 30)
        with ac2:
            symptoms = st.text_area("Describe your symptoms", max_chars=500,
                placeholder="e.g. headache for 2 days, mild fever, sore throat...")
        st.caption(str(len(symptoms)) + " / 500 characters")

        if st.button("Get Advice", type="primary", use_container_width=True):
            if not symptoms.strip():
                st.error("Please describe your symptoms first.")
            else:
                with st.spinner("Thinking..."):
                    advice = ai_health(age, symptoms, profile)
                st.session_state.health_history.append({
                    "age": age,
                    "symptoms": symptoms[:100] + ("..." if len(symptoms)>100 else ""),
                    "advice": advice,
                })
                st.success(advice)
                st.warning("General information only — not a diagnosis. Please consult a healthcare professional.")

        if st.session_state.health_history:
            with st.expander("📋 Session History (" + str(len(st.session_state.health_history)) + " queries)"):
                for i, entry in enumerate(reversed(st.session_state.health_history), 1):
                    st.markdown("**Query " + str(i) + "** — Age " + str(entry["age"]) + ": *" + entry["symptoms"] + "*")
                    st.markdown(entry["advice"])
                    st.markdown("---")
            if st.button("🗑️ Clear History"):
                st.session_state.health_history = []
                st.rerun()

    # ══════════════════════════════════════════════════════
    #  MY PROFILE
    # ══════════════════════════════════════════════════════

    elif "My Profile" in tab:
        hero("My Profile", "profile", "Your medical", "Update your health information at any time.")

        with st.form("edit_profile"):
            ec1, ec2 = st.columns(2)
            with ec1:
                name   = st.text_input("Full Name",   value=profile.get("name",""))
                age    = st.number_input("Age", 1, 120, value=int(profile.get("age",25)))
                gender = st.selectbox("Gender", ["Male","Female","Other"],
                    index=["Male","Female","Other"].index(profile.get("gender","Male")))
                blood  = st.selectbox("Blood Group",
                    ["Unknown","A+","A-","B+","B-","AB+","AB-","O+","O-"],
                    index=["Unknown","A+","A-","B+","B-","AB+","AB-","O+","O-"].index(
                        profile.get("blood_group","Unknown")))
            with ec2:
                conditions = st.multiselect("Chronic Conditions", CONDITIONS_LIST,
                    default=profile.get("conditions",[]))
                allergies  = st.multiselect("Known Drug Allergies", ALLERGIES_LIST,
                    default=profile.get("allergies",[]))

            st.markdown("---")
            st.markdown("**Medical History**")
            surgeries    = st.text_area("Past Surgeries", value=profile.get("surgeries",""),
                placeholder="e.g. Appendectomy (2018)...")
            genetic      = st.text_area("Genetic / Hereditary Conditions", value=profile.get("genetic",""),
                placeholder="e.g. G6PD deficiency...")
            accidents    = st.text_area("Accidents / Injuries", value=profile.get("accidents",""),
                placeholder="e.g. Kidney damage from road accident...")
            current_meds = st.multiselect("Currently Taking", medicine_list,
                default=profile.get("current_meds",[]),
                placeholder="Type to search medicines...")
            other_meds   = st.text_input("Other medicines not in list",
                value=profile.get("other_meds",""))

            save_btn = st.form_submit_button("💾 Update Profile", type="primary", use_container_width=True)

        if save_btn:
            if not name.strip():
                st.error("Please enter your name.")
            else:
                st.session_state.profile = {
                    "name":name.strip(),"age":age,"gender":gender,"blood_group":blood,
                    "conditions":conditions,"allergies":allergies,
                    "surgeries":surgeries.strip(),"genetic":genetic.strip(),
                    "accidents":accidents.strip(),"current_meds":current_meds,
                    "other_meds":other_meds.strip(),
                }
                st.session_state.profile_complete = True
                st.success("✅ Profile updated!")
                st.balloons()

    footer()


# ════════════════════════════════════════════════════════════
#  ENTRY POINT
# ════════════════════════════════════════════════════════════

if not st.session_state.logged_in or st.session_state.page == "login":
    page_login()
elif st.session_state.page == "profile_setup":
    page_profile_setup()
else:
    page_app()
