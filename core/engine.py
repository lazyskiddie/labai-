"""
LabAI Core Engine
Preprocessing → OCR → Parser → Analyzer → ML feature extraction
"""
import re, io, json, logging

log = logging.getLogger("labai")

try:
    from PIL import Image, ImageFilter, ImageEnhance, ImageOps
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

# ── Reference ranges ─────────────────────────────────────────────
REF = {
    "Hemoglobin":              {"lo": 12.0, "hi": 17.5, "ulo": 7.0,  "uhi": 20.0},
    "Hematocrit":              {"lo": 36,   "hi": 52,   "ulo": 21,   "uhi": 65},
    "RBC":                     {"lo": 3.8,  "hi": 6.0},
    "WBC":                     {"lo": 4.0,  "hi": 11.0, "ulo": 2.0,  "uhi": 30.0},
    "Platelets":               {"lo": 150,  "hi": 400,  "ulo": 50,   "uhi": 1000},
    "Neutrophils %":           {"lo": 40,   "hi": 75},
    "Lymphocytes %":           {"lo": 20,   "hi": 45},
    "Monocytes %":             {"lo": 2,    "hi": 10},
    "Eosinophils %":           {"lo": 0,    "hi": 6},
    "MCV":                     {"lo": 80,   "hi": 100},
    "MCH":                     {"lo": 27,   "hi": 33},
    "MCHC":                    {"lo": 31.5, "hi": 36},
    "RDW":                     {"lo": 11.5, "hi": 14.5},
    "ESR":                     {"lo": 0,    "hi": 20},
    "CRP":                     {"lo": 0,    "hi": 1.0},
    "TSH":                     {"lo": 0.4,  "hi": 4.0,  "ulo": 0.01, "uhi": 100},
    "T3 Total":                {"lo": 80,   "hi": 200},
    "T4 Total":                {"lo": 5.0,  "hi": 12.0},
    "Free T3":                 {"lo": 2.3,  "hi": 4.2},
    "Free T4":                 {"lo": 0.8,  "hi": 1.8},
    "Anti-TPO":                {"lo": 0,    "hi": 35},
    "Total Cholesterol":       {"lo": 0,    "hi": 200,  "uhi": 300},
    "LDL Cholesterol":         {"lo": 0,    "hi": 100,  "uhi": 190},
    "HDL Cholesterol":         {"lo": 40,   "hi": 9999},
    "Triglycerides":           {"lo": 0,    "hi": 150,  "uhi": 500},
    "VLDL":                    {"lo": 2,    "hi": 30},
    "ALT":                     {"lo": 0,    "hi": 40,   "uhi": 500},
    "AST":                     {"lo": 0,    "hi": 40,   "uhi": 500},
    "ALP":                     {"lo": 40,   "hi": 130},
    "GGT":                     {"lo": 0,    "hi": 60},
    "Bilirubin Total":         {"lo": 0,    "hi": 1.2,  "uhi": 15},
    "Bilirubin Direct":        {"lo": 0,    "hi": 0.3},
    "Albumin":                 {"lo": 3.5,  "hi": 5.0},
    "Total Protein":           {"lo": 6.0,  "hi": 8.5},
    "INR":                     {"lo": 0.8,  "hi": 1.1,  "uhi": 4.0},
    "Creatinine":              {"lo": 0.6,  "hi": 1.2,  "uhi": 10},
    "BUN":                     {"lo": 7,    "hi": 25,   "uhi": 100},
    "eGFR":                    {"lo": 60,   "hi": 9999, "ulo": 15},
    "Uric Acid":               {"lo": 2.5,  "hi": 7.0},
    "Sodium":                  {"lo": 136,  "hi": 145,  "ulo": 120,  "uhi": 160},
    "Potassium":               {"lo": 3.5,  "hi": 5.0,  "ulo": 2.5,  "uhi": 6.5},
    "Chloride":                {"lo": 98,   "hi": 106},
    "Calcium":                 {"lo": 8.5,  "hi": 10.5, "ulo": 6.5,  "uhi": 13.0},
    "Phosphorus":              {"lo": 2.5,  "hi": 4.5},
    "Magnesium":               {"lo": 1.7,  "hi": 2.2},
    "Fasting Glucose":         {"lo": 70,   "hi": 100,  "ulo": 40,   "uhi": 500},
    "Random Glucose":          {"lo": 70,   "hi": 140,  "ulo": 40,   "uhi": 500},
    "HbA1c":                   {"lo": 0,    "hi": 5.6,  "uhi": 14},
    "Fasting Insulin":         {"lo": 2,    "hi": 25},
    "Serum Iron":              {"lo": 60,   "hi": 170},
    "Ferritin":                {"lo": 12,   "hi": 300},
    "TIBC":                    {"lo": 250,  "hi": 370},
    "Transferrin Saturation":  {"lo": 20,   "hi": 50},
    "Vitamin B12":             {"lo": 200,  "hi": 900},
    "Folate":                  {"lo": 2.7,  "hi": 17},
    "Vitamin D (25-OH)":       {"lo": 30,   "hi": 100},
    "Troponin I":              {"lo": 0,    "hi": 0.04, "uhi": 2.0},
    "CK Total":                {"lo": 20,   "hi": 200},
    "CK-MB":                   {"lo": 0,    "hi": 5},
    "BNP":                     {"lo": 0,    "hi": 100},
    "Homocysteine":            {"lo": 5,    "hi": 15},
    "hs-CRP":                  {"lo": 0,    "hi": 1.0},
    "Cortisol (AM)":           {"lo": 6,    "hi": 23},
    "Testosterone (Male)":     {"lo": 300,  "hi": 1000},
    "Estradiol (Female)":      {"lo": 15,   "hi": 350},
    "Prolactin":               {"lo": 2,    "hi": 29},
    "LH":                      {"lo": 1.5,  "hi": 9.3},
    "FSH":                     {"lo": 1.5,  "hi": 12.4},
    "Urine pH":                {"lo": 4.5,  "hi": 8.0},
    "Urine Protein":           {"lo": 0,    "hi": 0.15},
    "Urine Glucose":           {"lo": 0,    "hi": 0},
    "Urine WBC":               {"lo": 0,    "hi": 5},
    "Urine RBC":               {"lo": 0,    "hi": 3},
    "Microalbumin":            {"lo": 0,    "hi": 30},
    "Urine Specific Gravity":  {"lo": 1.003,"hi": 1.030},
    "PSA":                     {"lo": 0,    "hi": 4.0},
    "CEA":                     {"lo": 0,    "hi": 3.0},
    "CA-125":                  {"lo": 0,    "hi": 35},
    "AFP":                     {"lo": 0,    "hi": 10},
    "ANA":                     {"lo": 0,    "hi": 1},
    "Rheumatoid Factor":       {"lo": 0,    "hi": 14},
    "Procalcitonin":           {"lo": 0,    "hi": 0.5},
}

# ── Synonyms ─────────────────────────────────────────────────────
SYN = {
    "hb":"Hemoglobin","haemoglobin":"Hemoglobin","hemoglobin":"Hemoglobin",
    "hgb":"Hemoglobin","hb level":"Hemoglobin",
    "hct":"Hematocrit","pcv":"Hematocrit","packed cell volume":"Hematocrit",
    "rbc":"RBC","red blood cells":"RBC","red cell count":"RBC",
    "wbc":"WBC","white blood cells":"WBC","tlc":"WBC",
    "total leukocyte count":"WBC","total wbc":"WBC","leukocytes":"WBC",
    "plt":"Platelets","platelet":"Platelets","platelets":"Platelets",
    "platelet count":"Platelets","thrombocytes":"Platelets",
    "neutrophil":"Neutrophils %","neutrophils":"Neutrophils %",
    "pmn":"Neutrophils %","segs":"Neutrophils %","neu":"Neutrophils %",
    "lymphocyte":"Lymphocytes %","lymphocytes":"Lymphocytes %",
    "lymphs":"Lymphocytes %","lym":"Lymphocytes %",
    "monocyte":"Monocytes %","monocytes":"Monocytes %","mono":"Monocytes %",
    "eosinophil":"Eosinophils %","eosinophils":"Eosinophils %","eos":"Eosinophils %",
    "mcv":"MCV","mean corpuscular volume":"MCV","mean cell volume":"MCV",
    "mch":"MCH","mean corpuscular hemoglobin":"MCH",
    "mchc":"MCHC","rdw":"RDW","red cell distribution width":"RDW",
    "esr":"ESR","erythrocyte sedimentation rate":"ESR","sed rate":"ESR",
    "crp":"CRP","c reactive protein":"CRP","c-reactive protein":"CRP",
    "tsh":"TSH","thyroid stimulating hormone":"TSH",
    "t3":"T3 Total","total t3":"T3 Total","triiodothyronine":"T3 Total",
    "t4":"T4 Total","total t4":"T4 Total","thyroxine":"T4 Total",
    "ft3":"Free T3","free t3":"Free T3","free triiodothyronine":"Free T3",
    "ft4":"Free T4","free t4":"Free T4","free thyroxine":"Free T4",
    "anti tpo":"Anti-TPO","anti-tpo":"Anti-TPO","tpo antibody":"Anti-TPO",
    "total cholesterol":"Total Cholesterol","cholesterol":"Total Cholesterol",
    "chol":"Total Cholesterol","tc":"Total Cholesterol",
    "ldl":"LDL Cholesterol","ldl-c":"LDL Cholesterol",
    "low density lipoprotein":"LDL Cholesterol",
    "hdl":"HDL Cholesterol","hdl-c":"HDL Cholesterol",
    "high density lipoprotein":"HDL Cholesterol",
    "tg":"Triglycerides","triglycerides":"Triglycerides",
    "triglyceride":"Triglycerides","trigs":"Triglycerides",
    "vldl":"VLDL",
    "alt":"ALT","sgpt":"ALT","alanine aminotransferase":"ALT",
    "ast":"AST","sgot":"AST","aspartate aminotransferase":"AST",
    "alp":"ALP","alkaline phosphatase":"ALP","alk phos":"ALP",
    "ggt":"GGT","gamma gt":"GGT",
    "total bilirubin":"Bilirubin Total","bilirubin":"Bilirubin Total","tbil":"Bilirubin Total",
    "direct bilirubin":"Bilirubin Direct","dbil":"Bilirubin Direct",
    "albumin":"Albumin","serum albumin":"Albumin","alb":"Albumin",
    "total protein":"Total Protein","protein":"Total Protein",
    "inr":"INR","international normalized ratio":"INR",
    "creatinine":"Creatinine","serum creatinine":"Creatinine","cr":"Creatinine",
    "bun":"BUN","blood urea nitrogen":"BUN","urea":"BUN","blood urea":"BUN",
    "egfr":"eGFR","gfr":"eGFR","estimated gfr":"eGFR",
    "uric acid":"Uric Acid","serum uric acid":"Uric Acid","sua":"Uric Acid",
    "sodium":"Sodium","na":"Sodium","serum sodium":"Sodium",
    "potassium":"Potassium","k":"Potassium","serum potassium":"Potassium",
    "chloride":"Chloride","cl":"Chloride",
    "calcium":"Calcium","serum calcium":"Calcium","ca":"Calcium",
    "phosphorus":"Phosphorus","phosphate":"Phosphorus","po4":"Phosphorus",
    "magnesium":"Magnesium","mg":"Magnesium",
    "glucose":"Fasting Glucose","blood glucose":"Fasting Glucose",
    "fbs":"Fasting Glucose","fasting blood sugar":"Fasting Glucose",
    "fasting glucose":"Fasting Glucose","blood sugar":"Fasting Glucose",
    "rbs":"Random Glucose","random blood sugar":"Random Glucose","ppbs":"Random Glucose",
    "hba1c":"HbA1c","a1c":"HbA1c","glycated hemoglobin":"HbA1c","hemoglobin a1c":"HbA1c",
    "insulin":"Fasting Insulin","fasting insulin":"Fasting Insulin",
    "serum iron":"Serum Iron","iron":"Serum Iron","fe":"Serum Iron",
    "ferritin":"Ferritin","serum ferritin":"Ferritin",
    "tibc":"TIBC","total iron binding capacity":"TIBC",
    "transferrin saturation":"Transferrin Saturation","tsat":"Transferrin Saturation",
    "b12":"Vitamin B12","vitamin b12":"Vitamin B12","cobalamin":"Vitamin B12","vit b12":"Vitamin B12",
    "folate":"Folate","folic acid":"Folate",
    "vitamin d":"Vitamin D (25-OH)","vit d":"Vitamin D (25-OH)",
    "25-oh vitamin d":"Vitamin D (25-OH)","25 oh vitamin d":"Vitamin D (25-OH)",
    "vitamin d3":"Vitamin D (25-OH)",
    "troponin i":"Troponin I","troponin":"Troponin I","tni":"Troponin I",
    "ck":"CK Total","creatine kinase":"CK Total","cpk":"CK Total",
    "ck-mb":"CK-MB","ckmb":"CK-MB",
    "bnp":"BNP","brain natriuretic peptide":"BNP",
    "homocysteine":"Homocysteine",
    "hs-crp":"hs-CRP","high sensitivity crp":"hs-CRP","hscrp":"hs-CRP",
    "cortisol":"Cortisol (AM)","serum cortisol":"Cortisol (AM)",
    "testosterone":"Testosterone (Male)","total testosterone":"Testosterone (Male)",
    "estradiol":"Estradiol (Female)","e2":"Estradiol (Female)",
    "prolactin":"Prolactin","prl":"Prolactin",
    "lh":"LH","luteinizing hormone":"LH",
    "fsh":"FSH","follicle stimulating hormone":"FSH",
    "urine ph":"Urine pH",
    "urine protein":"Urine Protein","proteinuria":"Urine Protein",
    "urine glucose":"Urine Glucose","glycosuria":"Urine Glucose",
    "urine wbc":"Urine WBC","pus cells":"Urine WBC",
    "urine rbc":"Urine RBC","hematuria":"Urine RBC",
    "microalbumin":"Microalbumin","urine microalbumin":"Microalbumin",
    "specific gravity":"Urine Specific Gravity",
    "urine specific gravity":"Urine Specific Gravity",
    "psa":"PSA","prostate specific antigen":"PSA",
    "cea":"CEA","carcinoembryonic antigen":"CEA",
    "ca 125":"CA-125","ca125":"CA-125",
    "afp":"AFP","alpha fetoprotein":"AFP",
    "ana":"ANA","antinuclear antibody":"ANA",
    "rheumatoid factor":"Rheumatoid Factor","rf":"Rheumatoid Factor","ra factor":"Rheumatoid Factor",
    "procalcitonin":"Procalcitonin","pct":"Procalcitonin",
}

FEATURE_KEYS = [
    "Hemoglobin","WBC","Platelets","TSH","Free T4","ALT","AST",
    "Creatinine","BUN","eGFR","Fasting Glucose","HbA1c",
    "Total Cholesterol","LDL Cholesterol","HDL Cholesterol",
    "Triglycerides","Ferritin","Sodium","Potassium","Calcium",
]


def normalize_name(raw: str):
    clean = raw.strip().lower()
    clean = " ".join(clean.split())
    clean = "".join(c for c in clean if c.isalnum() or c in " -./")
    for noise in ("serum", "level", "blood", "total"):
        clean = clean.replace(noise, "").strip()
    clean = " ".join(clean.split())
    if clean in SYN:
        return SYN[clean]
    for k, v in SYN.items():
        if clean == k or (len(clean) > 2 and clean in k) or (len(k) > 2 and k in clean):
            return v
    return None


def analyze_value(name: str, value: float) -> str:
    ref = REF.get(name)
    if not ref:
        return "unknown"
    if ref.get("ulo") is not None and value < ref["ulo"]:
        return "critical"
    if ref.get("uhi") is not None and value > ref["uhi"]:
        return "critical"
    if value < ref["lo"]:
        return "low"
    if value > ref["hi"]:
        return "high"
    return "normal"


def extract_feature_vector(values_dict: dict) -> list:
    return [float(values_dict.get(k, 0) or 0) for k in FEATURE_KEYS]


# ── Image preprocessing ──────────────────────────────────────────
def preprocess_image(img):
    w, h = img.size
    scale = max(1.0, min(3.0, 2400 / max(w, h)))
    if scale > 1.1:
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    img = img.convert("L")
    img = ImageEnhance.Contrast(img).enhance(1.8)
    img = ImageEnhance.Sharpness(img).enhance(2.0)
    img = img.filter(ImageFilter.SHARPEN)
    img = ImageOps.autocontrast(img, cutoff=2)
    return img


def ocr_image_bytes(image_bytes: bytes) -> str:
    if not OCR_AVAILABLE:
        return ""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = preprocess_image(img)
        cfg = "--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,:/()-% "
        return pytesseract.image_to_string(img, config=cfg)
    except Exception as e:
        log.error(f"OCR error: {e}")
        return ""


# ── Parser ───────────────────────────────────────────────────────
PARSE_RE = [
    re.compile(r"([A-Za-z][A-Za-z0-9\s\-\(\)\/\.]{2,40}?)\s*[:\-=]\s*([0-9]+\.?[0-9]*)", re.M),
    re.compile(r"([A-Za-z][A-Za-z0-9\s\-\/\.]{2,35}?)\s{2,}([0-9]+\.?[0-9]*)\s+(?:mg\/dL|g\/dL|U\/L|mmol\/L|ng\/mL|pg\/mL|mIU\/L|%|mEq\/L)", re.M | re.I),
]


def parse_lab_values(text: str) -> dict:
    values = {}
    for line in text.split("\n"):
        line = line.strip()
        if len(line) < 4:
            continue
        for pat in PARSE_RE:
            for m in pat.finditer(line):
                name = normalize_name(m.group(1))
                if not name:
                    continue
                try:
                    v = float(m.group(2))
                    if 0 < v < 1e6 and name not in values:
                        values[name] = v
                except ValueError:
                    pass
        lower = line.lower()
        for syn, canonical in SYN.items():
            if syn in lower and canonical not in values:
                nums = re.findall(r"\b(\d+\.?\d*)\b", line)
                for n in nums:
                    try:
                        v = float(n)
                        if 0 < v < 1e6:
                            values[canonical] = v
                            break
                    except ValueError:
                        pass
    return values


def compute_stats(matrix: list) -> dict:
    if not NUMPY_AVAILABLE:
        raise RuntimeError("numpy not installed")
    arr = np.array(matrix, dtype=np.float32)
    means = arr.mean(axis=0).tolist()
    stds = np.where(arr.std(axis=0) > 0, arr.std(axis=0), 1.0).tolist()
    return {"means": means, "stds": stds}