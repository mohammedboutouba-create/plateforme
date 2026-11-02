import io
import os
import re
import base64
import hashlib
import secrets
import sqlite3
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import urlparse
from xml.sax.saxutils import escape

import pandas as pd
import plotly.express as px
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

# ==========================================
# 0. الإعدادات والتهيئة العامة
# ==========================================
st.set_page_config(
    page_title="منصة التكامل والابتكار والمقاولاتية | Université d'Ain Témouchent",
    layout="wide"
)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(CURRENT_DIR, "university_integrated_platform_v26.db")


def get_image_file(candidates):
    for c in candidates:
        if os.path.exists(c):
            return c
        p1 = os.path.join(CURRENT_DIR, c)
        if os.path.exists(p1):
            return p1
        local_p = os.path.join(r"C:\Users\Ce PC\Desktop\mohammed", c)
        if os.path.exists(local_p):
            return local_p
    return None


LOGO_UNIV = get_image_file(["univ_logo.png", "image5.png", "logo.png", "image.png"])
LOGO_CDE = get_image_file(["images2.png", "cde_logo.png"])
LOGO_INCUBATOR = get_image_file(["images3.png", "incubator_logo.png"])

FACULTIES_AR = [
    "كلية العلوم والتكنولوجيا",
    "كلية العلوم الاقتصادية",
    "كلية الآداب واللغات والعلوم الاجتماعية",
    "كلية الحقوق",
]

FACULTIES_FR = [
    "Faculté des Sciences et de la Technologie",
    "Faculté des Sciences Économiques",
    "Faculté des Lettres et Sciences Sociales",
    "Faculté de Droit",
]

FACULTY_CODE_MAP = {
    FACULTIES_AR[0]: "FAC_TECH",
    FACULTIES_FR[0]: "FAC_TECH",
    FACULTIES_AR[1]: "FAC_ECON",
    FACULTIES_FR[1]: "FAC_ECON",
    FACULTIES_AR[2]: "FAC_LIT",
    FACULTIES_FR[2]: "FAC_LIT",
    FACULTIES_AR[3]: "FAC_LAW",
    FACULTIES_FR[3]: "FAC_LAW",
}

FACULTY_COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]

SHEET_COLUMNS_AR = [
    "الرقم",
    "الاسم واللقب",
    "القسم",
    "المستوى",
    "اسم المشروع",
    "ملخص عن المشروع",
]

SHEET_COLUMNS_FR = [
    "N°",
    "Nom & Prénom",
    "Département",
    "Niveau",
    "Intitulé du Projet",
    "Résumé du Projet",
]

ALLOWED_DOC_EXT = ["pdf", "xlsx", "xls"]
MAX_DOC_MB = 10
DOC_MIME = {
    "pdf": "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls": "application/vnd.ms-excel",
}


# ==========================================
# 1. نظام تشفير كلمات المرور
# ==========================================
def hash_password(password: str, salt: str = None) -> tuple:
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations=100000
    ).hex()
    return hashed, salt


def verify_password(stored_hash: str, stored_salt: str, provided_password: str) -> bool:
    if not stored_hash or not stored_salt:
        return False
    check_hash, _ = hash_password(provided_password, stored_salt)
    return secrets.compare_digest(stored_hash, check_hash)


# ==========================================
# 2. تشكيل النصوص العربية للـ PDF
# ==========================================
_AR_MAP = {
    "\u0621": ("\uFE80", "\uFE80", "\uFE80", "\uFE80"),
    "\u0622": ("\uFE81", "\uFE82", "\uFE81", "\uFE82"),
    "\u0623": ("\uFE83", "\uFE84", "\uFE83", "\uFE84"),
    "\u0624": ("\uFE85", "\uFE86", "\uFE85", "\uFE86"),
    "\u0625": ("\uFE87", "\uFE88", "\uFE87", "\uFE88"),
    "\u0626": ("\uFE89", "\uFE8A", "\uFE8B", "\uFE8C"),
    "\u0627": ("\uFE8D", "\uFE8E", "\uFE8D", "\uFE8E"),
    "\u0628": ("\uFE8F", "\uFE90", "\uFE91", "\uFE92"),
    "\u0629": ("\uFE93", "\uFE94", "\uFE93", "\uFE94"),
    "\u062A": ("\uFE95", "\uFE96", "\uFE97", "\uFE98"),
    "\u062B": ("\uFE99", "\uFE9A", "\uFE9B", "\uFE9C"),
    "\u062C": ("\uFE9D", "\uFE9E", "\uFE9F", "\uFEA0"),
    "\u062D": ("\uFEA1", "\uFEA2", "\uFEA3", "\uFEA4"),
    "\u062E": ("\uFEA5", "\uFEA6", "\uFEA7", "\uFEA8"),
    "\u062F": ("\uFEA9", "\uFEAA", "\uFEA9", "\uFEAA"),
    "\u0630": ("\uFEAB", "\uFEAC", "\uFEAB", "\uFEAC"),
    "\u0631": ("\uFEAD", "\uFEAE", "\uFEAD", "\uFEAE"),
    "\u0632": ("\uFEAF", "\uFEB0", "\uFEAF", "\uFEB0"),
    "\u0633": ("\uFEB1", "\uFEB2", "\uFEB3", "\uFEB4"),
    "\u0634": ("\uFEB5", "\uFEB6", "\uFEB7", "\uFEB8"),
    "\u0635": ("\uFEB9", "\uFEBA", "\uFEBB", "\uFEBC"),
    "\u0636": ("\uFEBD", "\uFEBE", "\uFEBF", "\uFEC0"),
    "\u0637": ("\uFEC1", "\uFEC2", "\uFEC3", "\uFEC4"),
    "\u0638": ("\uFEC5", "\uFEC6", "\uFEC7", "\uFEC8"),
    "\u0639": ("\uFEC9", "\uFECA", "\uFECB", "\uFECC"),
    "\u063A": ("\uFECD", "\uFECE", "\uFECF", "\uFED0"),
    "\u0641": ("\uFED1", "\uFED2", "\uFED3", "\uFED4"),
    "\u0642": ("\uFED5", "\uFED6", "\uFED7", "\uFED8"),
    "\u0643": ("\uFED9", "\uFEDA", "\uFEDB", "\uFEDC"),
    "\u0644": ("\uFEDD", "\uFEDE", "\uFEDF", "\uFEE0"),
    "\u0645": ("\uFEE1", "\uFEE2", "\uFEE3", "\uFEE4"),
    "\u0646": ("\uFEE5", "\uFEE6", "\uFEE7", "\uFEE8"),
    "\u0647": ("\uFEE9", "\uFEEA", "\uFEEB", "\uFEEC"),
    "\u0648": ("\uFEED", "\uFEEE", "\uFEED", "\uFEEE"),
    "\u0649": ("\uFEEF", "\uFEF0", "\uFEEF", "\uFEF0"),
    "\u064A": ("\uFEF1", "\uFEF2", "\uFEF3", "\uFEF4"),
}
_DUAL_JOIN = set("بتثجحخسشصضطظعغفقكلمنهيئ")
_RIGHT_JOIN = _DUAL_JOIN | set("اأإآدذرزوؤةى")
_LAM_ALEF = {
    "\u0622": ("\uFEF5", "\uFEF6"),
    "\u0623": ("\uFEF7", "\uFEF8"),
    "\u0625": ("\uFEF9", "\uFEFA"),
    "\u0627": ("\uFEFB", "\uFEFC"),
}


def _shape_arabic_word(text: str) -> str:
    chars = [c for c in text if not ("\u064B" <= c <= "\u065F")]
    out = []
    i = 0
    n = len(chars)
    while i < n:
        ch = chars[i]
        prev_c = chars[i - 1] if i > 0 else ""
        prev_joins = prev_c in _DUAL_JOIN

        if ch == "\u0644" and i + 1 < n and chars[i + 1] in _LAM_ALEF:
            lig = _LAM_ALEF[chars[i + 1]]
            out.append(lig[1] if prev_joins else lig[0])
            i += 2
            continue

        if ch in _AR_MAP:
            next_c = chars[i + 1] if i + 1 < n else ""
            next_joins = (ch in _DUAL_JOIN) and (next_c in _RIGHT_JOIN)
            forms = _AR_MAP[ch]
            if prev_joins and next_joins:
                out.append(forms[3])
            elif prev_joins:
                out.append(forms[1])
            elif next_joins:
                out.append(forms[2])
            else:
                out.append(forms[0])
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def _rtl_visual(text: str) -> str:
    if not text:
        return ""
    shaped = _shape_arabic_word(str(text))
    tokens = re.findall(r"[\u0600-\u06FF\uFE70-\uFEFC]+|[A-Za-z0-9_./:-]+|\s+|[^\s\w]", shaped)
    visual_tokens = []
    for tok in reversed(tokens):
        if re.match(r"^[\u0600-\u06FF\uFE70-\uFEFC]+$", tok):
            visual_tokens.append(tok[::-1])
        else:
            visual_tokens.append(tok)
    return "".join(visual_tokens)


def _load_font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/tahomabd.ttf" if bold else "C:/Windows/Fonts/tahoma.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


# ==========================================
# 3. معالجة وتصدير ملفات Excel و PDF
# ==========================================
def df_to_xlsx_bytes(df: pd.DataFrame, sheet_name: str = "المشاريع", is_rtl: bool = True) -> bytes:
    buf = io.BytesIO()
    try:
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
            ws = writer.sheets[sheet_name[:31]]
            ws.sheet_view.rightToLeft = is_rtl
        return buf.getvalue()
    except Exception:
        buf = io.BytesIO()
        headers = list(df.columns)
        rows_xml = []

        cells_h = [
            f'<c r="{chr(65 + c_idx)}1" t="inlineStr"><is><t>{escape(str(h))}</t></is></c>'
            for c_idx, h in enumerate(headers)
        ]
        rows_xml.append(f'<row r="1">{"".join(cells_h)}</row>')

        for r_idx, row in enumerate(df.fillna("").to_dict("records"), start=2):
            cells = []
            for c_idx, h in enumerate(headers):
                col_letter = chr(65 + c_idx)
                val = row.get(h, "")
                if str(val).strip().isdigit():
                    cells.append(f'<c r="{col_letter}{r_idx}"><v>{int(val)}</v></c>')
                else:
                    cells.append(
                        f'<c r="{col_letter}{r_idx}" t="inlineStr"><is><t>{escape(str(val))}</t></is></c>'
                    )
            rows_xml.append(f'<row r="{r_idx}">{"".join(cells)}</row>')

        rtl_attr = 'rightToLeft="1"' if is_rtl else 'rightToLeft="0"'
        sheet_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
            <sheetViews><sheetView {rtl_attr} workbookViewId="0"/></sheetViews>
            <sheetData>{"".join(rows_xml)}</sheetData>
        </worksheet>'''

        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "[Content_Types].xml",
                '''<?xml version="1.0" encoding="UTF-8"?>
                <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
                    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
                    <Default Extension="xml" ContentType="application/xml"/>
                    <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
                    <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
                </Types>''',
            )
            zf.writestr(
                "_rels/.rels",
                '''<?xml version="1.0" encoding="UTF-8"?>
                <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
                </Relationships>''',
            )
            zf.writestr(
                "xl/workbook.xml",
                f'''<?xml version="1.0" encoding="UTF-8"?>
                <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
                          xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
                    <sheets><sheet name="{escape(sheet_name[:31])}" sheetId="1" r:id="rId1"/></sheets>
                </workbook>''',
            )
            zf.writestr(
                "xl/_rels/workbook.xml.rels",
                '''<?xml version="1.0" encoding="UTF-8"?>
                <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
                </Relationships>''',
            )
            zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
        return buf.getvalue()


def read_excel_to_df(uploaded_file, target_columns: list) -> pd.DataFrame:
    raw_bytes = uploaded_file.getvalue()
    raw_df = None
    try:
        raw_df = pd.read_excel(io.BytesIO(raw_bytes))
    except Exception:
        with zipfile.ZipFile(io.BytesIO(raw_bytes), "r") as zf:
            shared_strings = []
            if "xl/sharedStrings.xml" in zf.namelist():
                ss_root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
                for si in ss_root.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"):
                    texts = [
                        t.text or ""
                        for t in si.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
                    ]
                    shared_strings.append("".join(texts))

            sheet_root = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
            ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            extracted_rows = []
            for row_el in sheet_root.findall(".//m:sheetData/m:row", ns):
                row_vals = {}
                for c_el in row_el.findall("m:c", ns):
                    ref = c_el.attrib.get("r", "A1")
                    col_letters = "".join(ch for ch in ref if ch.isalpha())
                    col_idx = 0
                    for ch in col_letters:
                        col_idx = col_idx * 26 + (ord(ch.upper()) - 64)
                    col_idx -= 1

                    c_type = c_el.attrib.get("t", "")
                    v_el = c_el.find("m:v", ns)
                    is_el = c_el.find(".//m:t", ns)
                    val = ""
                    if c_type == "s" and v_el is not None and v_el.text:
                        idx = int(v_el.text)
                        val = shared_strings[idx] if idx < len(shared_strings) else ""
                    elif c_type == "inlineStr" and is_el is not None:
                        val = is_el.text or ""
                    elif v_el is not None and v_el.text is not None:
                        val = v_el.text
                    row_vals[col_idx] = val
                if row_vals:
                    max_c = max(row_vals.keys())
                    extracted_rows.append([row_vals.get(i, "") for i in range(max_c + 1)])

            if extracted_rows:
                headers = [str(x).strip() for x in extracted_rows[0]]
                data_rows = extracted_rows[1:]
                raw_df = pd.DataFrame(data_rows, columns=headers)
            else:
                raw_df = pd.DataFrame(columns=target_columns)

    if raw_df is None or raw_df.empty:
        return pd.DataFrame(columns=target_columns)

    raw_df.columns = [str(c).strip() for c in raw_df.columns]
    result = pd.DataFrame()

    for idx, target_col in enumerate(target_columns):
        if target_col in raw_df.columns:
            result[target_col] = raw_df[target_col]
        elif idx < len(raw_df.columns):
            result[target_col] = raw_df.iloc[:, idx]
        else:
            result[target_col] = ""

    result = result.dropna(how="all").fillna("")
    cleaned_nums = []
    first_col = target_columns[0]
    for i, val in enumerate(result[first_col], start=1):
        try:
            cleaned_nums.append(int(float(str(val).strip())))
        except Exception:
            cleaned_nums.append(i)
    result[first_col] = cleaned_nums
    return result[target_columns]


def df_to_pdf_bytes(df: pd.DataFrame, faculty_name: str, cols: list, is_rtl: bool = True) -> bytes:
    page_w, margin = 1650, 50
    col_widths = [90, 250, 240, 150, 310, 510]
    headers = list(reversed(cols)) if is_rtl else cols
    widths = list(reversed(col_widths)) if is_rtl else col_widths

    font_title = _load_font(26, bold=True)
    font_sub = _load_font(17, bold=False)
    font_head = _load_font(18, bold=True)
    font_cell = _load_font(16, bold=False)

    clean_rows = df.fillna("").to_dict("records")
    row_heights = []
    wrapped_rows = []

    for r in clean_rows:
        row_cells = []
        max_lines = 1
        for col_name, w in zip(headers, widths):
            raw_val = str(r.get(col_name, "")).strip()
            max_chars = max(10, int(w / 10))
            words = raw_val.split()
            lines, cur = [], ""
            for word in words:
                if len(cur) + len(word) + 1 <= max_chars:
                    cur = f"{cur} {word}".strip()
                else:
                    if cur:
                        lines.append(cur)
                    cur = word
            if cur:
                lines.append(cur)
            if not lines:
                lines = [""]
            max_lines = max(max_lines, len(lines))
            row_cells.append(lines)
        wrapped_rows.append(row_cells)
        row_heights.append(max(44, max_lines * 26 + 16))

    total_h = max(750, 210 + sum(row_heights) + 80)
    img = Image.new("RGB", (page_w, total_h), "white")
    draw = ImageDraw.Draw(img)

    draw.rectangle([margin, 35, page_w - margin, 125], fill=(24, 62, 115))

    if is_rtl:
        title_txt = _rtl_visual(f"قائمة المشاريع - {faculty_name}")
        sub_txt = _rtl_visual(f"تاريخ الاستخراج: {now_str()} | الإدارة")
        draw.text((page_w - margin - 25, 50), title_txt, font=font_title, fill="white", anchor="ra")
        draw.text((page_w - margin - 25, 90), sub_txt, font=font_sub, fill=(220, 232, 245), anchor="ra")
    else:
        title_txt = f"Liste des Projets - {faculty_name}"
        sub_txt = f"Date d'extraction: {now_str()} | Administration"
        draw.text((margin + 25, 50), title_txt, font=font_title, fill="white", anchor="la")
        draw.text((margin + 25, 90), sub_txt, font=font_sub, fill=(220, 232, 245), anchor="la")

    y = 145
    header_h = 48
    x = margin
    for h_name, w in zip(headers, widths):
        draw.rectangle([x, y, x + w, y + header_h], fill=(230, 238, 248), outline=(120, 140, 170), width=2)
        txt = _rtl_visual(h_name) if is_rtl else h_name
        if is_rtl:
            draw.text((x + w - 12, y + 12), txt, font=font_head, fill=(20, 40, 80), anchor="ra")
        else:
            draw.text((x + 12, y + 12), txt, font=font_head, fill=(20, 40, 80), anchor="la")
        x += w
    y += header_h

    for r_idx, (row_cells, r_h) in enumerate(zip(wrapped_rows, row_heights)):
        bg = (255, 255, 255) if r_idx % 2 == 0 else (247, 250, 253)
        x = margin
        for lines, w in zip(row_cells, widths):
            draw.rectangle([x, y, x + w, y + r_h], fill=bg, outline=(180, 195, 210), width=1)
            for l_idx, line in enumerate(lines):
                line_str = _rtl_visual(line) if is_rtl else line
                if is_rtl:
                    draw.text(
                        (x + w - 12, y + 10 + l_idx * 24),
                        line_str,
                        font=font_cell,
                        fill=(30, 30, 30),
                        anchor="ra",
                    )
                else:
                    draw.text(
                        (x + 12, y + 10 + l_idx * 24),
                        line_str,
                        font=font_cell,
                        fill=(30, 30, 30),
                        anchor="la",
                    )
            x += w
        y += r_h

    buf = io.BytesIO()
    img.save(buf, format="PDF", resolution=150.0)
    return buf.getvalue()


# ==========================================
# 4. إعدادات قاعدة البيانات SQLite
# ==========================================
@st.cache_resource
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass
    return conn


conn = get_conn()


def q(sql, params=(), one=False):
    cur = conn.execute(sql, params)
    return cur.fetchone() if one else cur.fetchall()


def ex(sql, params=()):
    cur = conn.execute(sql, params)
    conn.commit()
    return cur.lastrowid


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def init_db():
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                faculty TEXT NOT NULL,
                password_hash TEXT,
                salt TEXT
            );
            CREATE TABLE IF NOT EXISTS academic_seasons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season_year TEXT NOT NULL UNIQUE,
                is_active INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS season_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season_year TEXT NOT NULL UNIQUE,
                total_projects INTEGER NOT NULL DEFAULT 0,
                innovative_certificates INTEGER NOT NULL DEFAULT 0,
                startup_certificates INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS faculty_sheets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                faculty_code TEXT,
                faculty TEXT,
                season_year TEXT NOT NULL,
                row_num INTEGER NOT NULL,
                full_name TEXT NOT NULL,
                department TEXT NOT NULL,
                level TEXT NOT NULL,
                project_name TEXT NOT NULL,
                project_summary TEXT NOT NULL,
                updated_by TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                link TEXT NOT NULL,
                uploaded_by INTEGER NOT NULL REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS defense_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_ext TEXT NOT NULL,
                file_data BLOB NOT NULL,
                faculty_code TEXT,
                faculty TEXT,
                season_year TEXT NOT NULL,
                uploaded_by INTEGER NOT NULL REFERENCES users(id),
                created_at TEXT NOT NULL
            );
            """
        )
        conn.commit()
    except Exception:
        pass

    try:
        cur_f = conn.execute("PRAGMA table_info(faculty_sheets)")
        f_cols = [r["name"] for r in cur_f.fetchall()]
        if "faculty_code" not in f_cols and "faculty" in f_cols:
            conn.execute("ALTER TABLE faculty_sheets ADD COLUMN faculty_code TEXT")
            conn.execute("UPDATE faculty_sheets SET faculty_code = faculty")
            conn.commit()

        cur_d = conn.execute("PRAGMA table_info(defense_reports)")
        d_cols = [r["name"] for r in cur_d.fetchall()]
        if "faculty_code" not in d_cols:
            if "target_faculty" in d_cols:
                conn.execute("ALTER TABLE defense_reports ADD COLUMN faculty_code TEXT")
                conn.execute("UPDATE defense_reports SET faculty_code = target_faculty")
                conn.commit()
            elif "faculty" in d_cols:
                conn.execute("ALTER TABLE defense_reports ADD COLUMN faculty_code TEXT")
                conn.execute("UPDATE defense_reports SET faculty_code = faculty")
                conn.commit()
    except Exception:
        pass

    try:
        conn.execute("""
            UPDATE faculty_sheets SET faculty_code = 'FAC_TECH' 
            WHERE faculty_code IN ('كلية العلوم والتكنولوجيا', 'Faculté des Sciences et de la Technologie')
        """)
        conn.execute("""
            UPDATE faculty_sheets SET faculty_code = 'FAC_ECON' 
            WHERE faculty_code IN ('كلية العلوم الاقتصادية', 'Faculté des Sciences Économiques')
        """)
        conn.execute("""
            UPDATE faculty_sheets SET faculty_code = 'FAC_LIT' 
            WHERE faculty_code IN ('كلية الآداب واللغات والعلوم الاجتماعية', 'Faculté des Lettres et Sciences Sociales')
        """)
        conn.execute("""
            UPDATE faculty_sheets SET faculty_code = 'FAC_LAW' 
            WHERE faculty_code IN ('كلية الحقوق', 'Faculté de Droit')
        """)
        conn.execute("UPDATE OR IGNORE academic_seasons SET season_year = REPLACE(season_year, '-', '/')")
        conn.execute("UPDATE OR IGNORE faculty_sheets SET season_year = REPLACE(season_year, '-', '/')")
        conn.execute("UPDATE OR IGNORE defense_reports SET season_year = REPLACE(season_year, '-', '/')")
        conn.commit()
    except Exception:
        pass

    try:
        inc_user = q("SELECT id FROM users WHERE role='INCUBATOR' LIMIT 1", one=True)
        if not inc_user:
            default_hash_inc, default_salt_inc = hash_password("123456789")
            conn.execute(
                "INSERT INTO users (name, role, faculty, password_hash, salt) VALUES (?, ?, ?, ?, ?)",
                ("مدير حاضنة الأعمال", "INCUBATOR", "إدارة الحاضنة", default_hash_inc, default_salt_inc)
            )

        cde_user = q("SELECT id FROM users WHERE role='CDE' LIMIT 1", one=True)
        if not cde_user:
            default_hash_cde, default_salt_cde = hash_password("987654321")
            conn.execute(
                "INSERT INTO users (name, role, faculty, password_hash, salt) VALUES (?, ?, ?, ?, ?)",
                ("مدير مركز تطوير المقاولاتية", "CDE", "مركز تطوير المقاولاتية", default_hash_cde, default_salt_cde)
            )
        conn.commit()
    except Exception:
        pass

    seasons_data = [
        ("2023/2024", 0),
        ("2024/2025", 0),
        ("2025/2026", 0),
        ("2026/2027", 1),
    ]
    for s_yr, is_act in seasons_data:
        try:
            exists = q("SELECT id FROM academic_seasons WHERE season_year=?", (s_yr,), one=True)
            if not exists:
                conn.execute("INSERT OR IGNORE INTO academic_seasons (season_year, is_active) VALUES (?, ?)",
                             (s_yr, is_act))
        except Exception:
            pass
    conn.commit()

    official_stats = [
        ("2023/2024", 50, 16, 0),
        ("2024/2025", 40, 36, 2),
        ("2025/2026", 60, 48, 4),
        ("2026/2027", 0, 0, 0),
    ]
    for s_yr, tot_proj, innov, start in official_stats:
        try:
            s_exist = q("SELECT id FROM season_stats WHERE season_year=?", (s_yr,), one=True)
            if not s_exist:
                conn.execute(
                    "INSERT OR IGNORE INTO season_stats (season_year, total_projects, innovative_certificates, startup_certificates) VALUES (?, ?, ?, ?)",
                    (s_yr, tot_proj, innov, start)
                )
            else:
                if s_yr in ["2023/2024", "2024/2025", "2025/2026"]:
                    conn.execute(
                        "UPDATE season_stats SET total_projects=?, innovative_certificates=?, startup_certificates=? WHERE season_year=?",
                        (tot_proj, innov, start, s_yr)
                    )
        except Exception:
            pass
    conn.commit()


init_db()


def get_active_season() -> str:
    row = q("SELECT season_year FROM academic_seasons WHERE is_active=1 LIMIT 1", one=True)
    return row["season_year"] if row else "2026/2027"


def valid_url(url: str) -> bool:
    try:
        p = urlparse(url.strip())
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False


def flash(msg: str, icon: str = "✅"):
    st.session_state["_flash"] = (msg, icon)


def load_faculty_df(faculty_code: str, season: str, cols: list) -> pd.DataFrame:
    cur_f = conn.execute("PRAGMA table_info(faculty_sheets)")
    existing_cols = [r["name"] for r in cur_f.fetchall()]

    if "faculty" in existing_cols and "faculty_code" in existing_cols:
        rows = q(
            """SELECT row_num, full_name, department, level, project_name, project_summary 
               FROM faculty_sheets 
               WHERE (faculty_code=? OR faculty=?) AND season_year=? 
               ORDER BY row_num ASC, id ASC""",
            (faculty_code, faculty_code, season),
        )
    elif "faculty_code" in existing_cols:
        rows = q(
            """SELECT row_num, full_name, department, level, project_name, project_summary 
               FROM faculty_sheets 
               WHERE faculty_code=? AND season_year=? 
               ORDER BY row_num ASC, id ASC""",
            (faculty_code, season),
        )
    else:
        rows = q(
            """SELECT row_num, full_name, department, level, project_name, project_summary 
               FROM faculty_sheets 
               WHERE faculty=? AND season_year=? 
               ORDER BY row_num ASC, id ASC""",
            (faculty_code, season),
        )

    if not rows:
        return pd.DataFrame(columns=cols)
    data = [
        {
            cols[0]: r["row_num"],
            cols[1]: r["full_name"],
            cols[2]: r["department"],
            cols[3]: r["level"],
            cols[4]: r["project_name"],
            cols[5]: r["project_summary"],
        }
        for r in rows
    ]
    return pd.DataFrame(data, columns=cols)


def save_faculty_df(faculty_code: str, season: str, df: pd.DataFrame, user_name: str, cols: list):
    ex("DELETE FROM faculty_sheets WHERE (faculty_code=? OR faculty=?) AND season_year=?",
       (faculty_code, faculty_code, season))

    cur_f = conn.execute("PRAGMA table_info(faculty_sheets)")
    existing_cols = [r["name"] for r in cur_f.fetchall()]
    has_legacy_faculty = "faculty" in existing_cols

    clean_df = df.dropna(how="all").fillna("")
    for idx, row in enumerate(clean_df.to_dict("records"), start=1):
        r_num = row.get(cols[0])
        try:
            r_num = int(float(str(r_num).strip())) if str(r_num).strip() != "" else idx
        except ValueError:
            r_num = idx

        f_name = str(row.get(cols[1], "")).strip()
        dept = str(row.get(cols[2], "")).strip()
        lvl = str(row.get(cols[3], "")).strip()
        proj = str(row.get(cols[4], "")).strip()
        summary = str(row.get(cols[5], "")).strip()

        if has_legacy_faculty:
            ex(
                """INSERT INTO faculty_sheets 
                   (faculty, faculty_code, season_year, row_num, full_name, department, level, project_name, project_summary, updated_by, updated_at) 
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (faculty_code, faculty_code, season, r_num, f_name, dept, lvl, proj, summary, user_name, now_str())
            )
        else:
            ex(
                """INSERT INTO faculty_sheets 
                   (faculty_code, season_year, row_num, full_name, department, level, project_name, project_summary, updated_by, updated_at) 
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (faculty_code, season, r_num, f_name, dept, lvl, proj, summary, user_name, now_str())
            )


def get_faculty_project_count(faculty_code: str, season: str) -> int:
    cur_f = conn.execute("PRAGMA table_info(faculty_sheets)")
    existing_cols = [r["name"] for r in cur_f.fetchall()]

    if "faculty" in existing_cols and "faculty_code" in existing_cols:
        return q(
            """SELECT COUNT(*) AS n FROM faculty_sheets 
               WHERE (faculty_code=? OR faculty=?) AND season_year=? AND TRIM(project_name) != ''""",
            (faculty_code, faculty_code, season),
            one=True,
        )["n"]
    elif "faculty_code" in existing_cols:
        return q(
            """SELECT COUNT(*) AS n FROM faculty_sheets 
               WHERE faculty_code=? AND season_year=? AND TRIM(project_name) != ''""",
            (faculty_code, season),
            one=True,
        )["n"]
    else:
        return q(
            """SELECT COUNT(*) AS n FROM faculty_sheets 
               WHERE faculty=? AND season_year=? AND TRIM(project_name) != ''""",
            (faculty_code, season),
            one=True,
        )["n"]


def get_season_full_stats(season: str):
    row = q(
        "SELECT total_projects, innovative_certificates, startup_certificates FROM season_stats WHERE season_year=?",
        (season,),
        one=True
    )
    if row and row["total_projects"] > 0:
        return row["total_projects"], row["innovative_certificates"], row["startup_certificates"]

    actual_sheet_count = q(
        "SELECT COUNT(*) AS n FROM faculty_sheets WHERE season_year=? AND TRIM(project_name) != ''",
        (season,),
        one=True
    )["n"]
    innov = row["innovative_certificates"] if row else 0
    start = row["startup_certificates"] if row else 0
    return actual_sheet_count, innov, start


# ==========================================
# 5. الشريط الجانبي (الجهة اليمنى)
# ==========================================
def load_clean_pil_image(path):
    if path and os.path.exists(path):
        try:
            img = Image.open(path).convert("RGBA")
            enhancer = ImageEnhance.Sharpness(img)
            return enhancer.enhance(1.3)
        except Exception:
            return path
    return None


def get_image_base64(path):
    if path and os.path.exists(path):
        try:
            with open(path, "rb") as f:
                return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
        except Exception:
            return None
    return None


univ_logo_b64 = get_image_base64(LOGO_UNIV)
logo_side_html = (
    f'<img src="{univ_logo_b64}" style="width: 52px; height: 52px; min-width: 52px; object-fit: contain; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.12));">'
    if univ_logo_b64 else
    '<span style="font-size: 32px; line-height: 1;">🏛️</span>'
)

st.sidebar.markdown(f"""
    <div style="padding: 12px 6px 14px 6px; border-bottom: 2px solid #3b82f6; margin-bottom: 16px; background: #f8fafc; border-radius: 12px;">
        <div style="display: flex; align-items: center; justify-content: center; flex-direction: row-reverse; gap: 10px; white-space: nowrap;">
            {logo_side_html}
            <div style="text-align: right; white-space: nowrap;">
                <span style="color: #1e3a8a; font-weight: 900; font-size: 15.5px; white-space: nowrap; display: block; line-height: 1.2;">
                    جامعة عين تموشنت بلحاج بوشعيب
                </span>
                <span style="color: #64748b; font-size: 11px; font-weight: 600; white-space: nowrap; display: block; margin-top: 3px;">
                    Univ. Ain Témouchent Belhadj Bouchaib
                </span>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

if "current_lang_code" not in st.session_state:
    st.session_state["current_lang_code"] = "Ar"

st.sidebar.markdown("""
    <div style="text-align: center; margin-bottom: 6px;">
        <span style="color: #1e293b; font-weight: 700; font-size: 14px;">🌐 اختر اللغة / Langue :</span>
    </div>
""", unsafe_allow_html=True)

lang_choice = st.sidebar.radio(
    "lang_selector",
    ["Ar", "Fr"],
    index=0 if st.session_state["current_lang_code"] == "Ar" else 1,
    horizontal=True,
    label_visibility="collapsed"
)
st.session_state["current_lang_code"] = lang_choice

is_arabic = (lang_choice == "Ar")
current_dir = "rtl" if is_arabic else "ltr"
current_align = "right" if is_arabic else "left"

st.sidebar.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

if "current_portal_code" not in st.session_state:
    st.session_state["current_portal_code"] = "INCUBATOR"

portal_options = [
    ("💡 حاضنة الأعمال", "INCUBATOR") if is_arabic else ("💡 Incubateur d'Entreprises", "INCUBATOR"),
    ("🚀 مركز تطوير المقاولاتية", "CDE") if is_arabic else ("🚀 Centre de Développement de l'Entrepreneuriat", "CDE")
]

st.sidebar.markdown(
    f"<div style='font-weight: 700; color: #1e293b; font-size: 14.5px; margin-bottom: 6px; text-align: {current_align};'>"
    f"{'🏢 اختر الفضاء:' if is_arabic else '🏢 Sélectionner l\'Espace :'}</div>",
    unsafe_allow_html=True
)

selected_portal_label = st.sidebar.radio(
    "portal_selector",
    [opt[0] for opt in portal_options],
    index=0 if st.session_state["current_portal_code"] == "INCUBATOR" else 1,
    label_visibility="collapsed"
)

current_portal = "INCUBATOR" if selected_portal_label == portal_options[0][0] else "CDE"
if st.session_state["current_portal_code"] != current_portal:
    st.session_state["current_portal_code"] = current_portal
    st.rerun()

is_cde = (current_portal == "CDE")

# ==========================================
# 6. التسميات المخصصة بحسب الفضاء واللغة
# ==========================================
if is_cde:
    metric_label_2 = "CSVF"
    metric_label_3 = "مؤسسة اقتصادية" if is_arabic else "Entreprise Économique"
else:
    metric_label_2 = "شهادات مشروع مبتكر" if is_arabic else "Labels Projet Innovant"
    metric_label_3 = "شهادات مؤسسة ناشئة" if is_arabic else "Labels Start-up"

# ==========================================
# 7. التنسيق الدقيق بين الإطار الأزرق والنص (CSS)
# ==========================================
st.markdown(
    f"""
    <style>
    html, body, [class*="css"] {{
        font-family: Tahoma, 'Segoe UI', sans-serif;
    }}
    .stApp {{
        direction: {current_dir};
        text-align: {current_align};
    }}

    .hero-center-box {{
        background: linear-gradient(180deg, #1e3a8a 0%, #1e40af 45%, #172554 100%);
        border: 1.5px solid rgba(255, 255, 255, 0.35);
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(30, 58, 138, 0.35);
        padding: 16px 22px;
        text-align: center;
        width: 100%;
        min-height: 175px;
        box-sizing: border-box;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }}

    .u-republic {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(255, 255, 255, 0.14);
        border: 1px solid rgba(255, 255, 255, 0.25);
        border-radius: 999px;
        padding: 3px 18px;
        margin-bottom: 6px;
        color: #eff6ff;
        font-size: 13px;
        font-weight: 700;
        white-space: nowrap;
    }}

    .univ-title-ar {{
        color: #fca5a5 !important;
        font-size: 26px !important;
        font-weight: 900 !important;
        margin: 4px 0 6px 0;
        padding: 0;
        line-height: 1.3;
        white-space: nowrap;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.6);
    }}

    .univ-title-fr {{
        color: #fca5a5 !important;
        font-size: 20px !important;
        font-weight: 900 !important;
        margin: 4px 0 6px 0;
        padding: 0;
        line-height: 1.35;
        white-space: normal;
        word-wrap: break-word;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.6);
    }}

    .u-ribbon {{
        background: linear-gradient(90deg, rgba(245, 158, 11, 0.25), rgba(251, 191, 36, 0.42), rgba(245, 158, 11, 0.25));
        border: 1px solid rgba(251, 191, 36, 0.65);
        border-radius: 12px;
        padding: 5px 20px;
        margin: 4px auto;
        display: inline-block;
    }}

    .u-ribbon h3 {{
        margin: 0;
        color: #fef08a;
        font-size: 15.5px;
        font-weight: 800;
        white-space: nowrap;
    }}

    .u-desc {{
        color: #dbeafe;
        font-size: 12.5px;
        margin: 6px 0 0 0;
        font-weight: 600;
        line-height: 1.4;
    }}

    .faculty-right-label {{
        text-align: {current_align};
        direction: {current_dir};
        font-size: 15px;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 4px;
    }}

    .app-footer {{
        text-align: center;
        padding: 24px 10px;
        margin-top: 45px;
        border-top: 1px solid #e2e8f0;
        color: #64748b;
        font-size: 14px;
        line-height: 1.8;
    }}

    .footer-social-links {{
        display: flex;
        justify-content: center;
        align-items: center;
        flex-wrap: wrap;
        gap: 15px;
        margin-bottom: 12px;
    }}

    .footer-social-links a {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        color: #1e40af;
        text-decoration: none;
        font-weight: 700;
        font-size: 13.5px;
        padding: 6px 14px;
        background: #f1f5f9;
        border-radius: 999px;
        border: 1px solid #cbd5e1;
        transition: all 0.2s ease;
    }}

    .footer-social-links a:hover {{
        background: #e2e8f0;
        color: #1d4ed8;
        transform: translateY(-2px);
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# 8. الترويسة العلوية واستبدال اللوغو في الواجهة
# ==========================================
img_cde_pil = load_clean_pil_image(LOGO_CDE)
img_incubator_pil = load_clean_pil_image(LOGO_INCUBATOR)

active_header_logo_right = img_cde_pil if is_cde else img_incubator_pil
active_header_logo_left = img_incubator_pil if is_cde else img_cde_pil

h_col_right, h_col_mid, h_col_left = st.columns([1.5, 7, 1.5], vertical_alignment="center")

with h_col_right:
    if active_header_logo_right is not None:
        st.image(active_header_logo_right, width=140)
    else:
        st.markdown(f"<div style='font-size: 55px; text-align: center;'>{'🚀' if is_cde else '💡'}</div>",
                    unsafe_allow_html=True)

with h_col_mid:
    if is_arabic:
        portal_title_ar = "🚀 منصة مركز تطوير المقاولاتية (CDE) والمصالح البيداغوجية" if is_cde else "🎓 منصة حاضنة الأعمال والمصالح البيداغوجية"
        portal_desc_ar = "تطوير روح المقاولاتية ومرافقة المشاريع المصغرة والابتكارية" if is_cde else "إدارة ومتابعة المشاريع الابتكارية وفق القرار الوزاري 1275"
        st.markdown(f"""
            <div class="hero-center-box">
                <div class="u-republic">الجمهورية الجزائرية الديمقراطية الشعبية</div>
                <div>
                    <h1 class="univ-title-ar">جامعة عين تموشنت بلحاج بوشعيب</h1>
                </div>
                <div class="u-ribbon">
                    <h3>{portal_title_ar}</h3>
                </div>
                <p class="u-desc">{portal_desc_ar}</p>
            </div>
        """, unsafe_allow_html=True)
    else:
        portal_title_fr = "🚀 Plateforme du CDE & Services Pédagogiques" if is_cde else "🎓 Plateforme de l'Incubateur & Services Pédagogiques"
        portal_desc_fr = "Développement de l'entrepreneuriat et accompagnement des projets" if is_cde else "Gestion et suivi des projets innovants (Arrêté Ministériel 1275)"
        st.markdown(f"""
            <div class="hero-center-box">
                <div class="u-republic">République Algérienne Démocratique et Populaire</div>
                <div>
                    <h1 class="univ-title-fr">Université d'Ain Témouchent Belhadj Bouchaib</h1>
                </div>
                <div class="u-ribbon">
                    <h3>{portal_title_fr}</h3>
                </div>
                <p class="u-desc">{portal_desc_fr}</p>
            </div>
        """, unsafe_allow_html=True)

with h_col_left:
    if active_header_logo_left is not None:
        st.image(active_header_logo_left, width=140)
    else:
        st.markdown(f"<div style='font-size: 55px; text-align: center;'>{'💡' if is_cde else '🚀'}</div>",
                    unsafe_allow_html=True)

st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

if "_flash" in st.session_state:
    _msg, _icon = st.session_state.pop("_flash")
    st.toast(_msg, icon=_icon)

# ==========================================
# 9. إدارة الدخول والحسابات في الشريط الجانبي
# ==========================================
seasons_rows = q("SELECT season_year, is_active FROM academic_seasons ORDER BY id DESC")
seasons_list = [r["season_year"] for r in seasons_rows]
active_season = get_active_season()

auth_key = "cde_authenticated" if is_cde else "incubator_authenticated"
role_target = "CDE" if is_cde else "INCUBATOR"

if auth_key not in st.session_state:
    st.session_state[auth_key] = False

admin_label = (
    ("⚙️ إدارة مركز تطوير المقاولاتية" if is_cde else "⚙️ إدارة مدير الحاضنة")
    if is_arabic else
    ("⚙️ Administration CDE" if is_cde else "⚙️ Administration Incubateur")
)

st.sidebar.markdown(
    f"<h4 style='text-align: {current_align}; color: #1e293b; font-weight: 700; margin-top: 15px;'>"
    f"{admin_label}</h4>",
    unsafe_allow_html=True
)

selected_season = st.sidebar.selectbox(
    "📅 الموسم الجامعي المعتمد:" if is_arabic else "📅 Année Universitaire :",
    seasons_list,
    index=seasons_list.index(active_season) if active_season in seasons_list else 0,
)

user_record = q("SELECT id, password_hash, salt FROM users WHERE role=? LIMIT 1", (role_target,), one=True)

if not st.session_state[auth_key]:
    pwd_prompt = (
        ("أدخل كلمة مرور إدارة المقاولاتية:" if is_cde else "أدخل كلمة مرور مدير الحاضنة:")
        if is_arabic else
        ("Mot de passe administration CDE :" if is_cde else "Mot de passe de l'incubateur :")
    )
    pwd_input = st.sidebar.text_input(
        pwd_prompt,
        type="password",
        placeholder="•••••••••",
        key=f"pwd_input_{current_portal}"
    )
    btn_login_txt = (
        ("🔑 تسجيل الدخول كمدير CDE" if is_cde else "🔑 تسجيل الدخول كمدير حاضنة")
        if is_arabic else
        ("🔑 Se connecter (CDE)" if is_cde else "🔑 Se connecter (Incubateur)")
    )
    if st.sidebar.button(btn_login_txt, use_container_width=True, key=f"btn_login_{current_portal}"):
        if user_record and verify_password(user_record["password_hash"], user_record["salt"], pwd_input):
            st.session_state[auth_key] = True
            flash("تم التحقق وتسجيل الدخول بنجاح!" if is_arabic else "Connexion réussie !")
            st.rerun()
        else:
            st.sidebar.error("❌ كلمة المرور غير صحيحة!" if is_arabic else "❌ Mot de passe incorrect !")
    st.sidebar.info("ℹ️ أنت في وضع الاطلاع والتحميل" if is_arabic else "ℹ️ Mode consultation et téléchargement")
else:
    auth_success_txt = (
        (
            "✅ متصل الآن: مدير مركز المقاولاتية (صلاحيات كاملة)" if is_cde else "✅ متصل الآن: مدير الحاضنة (صلاحيات كاملة)")
        if is_arabic else
        (
            "✅ Connecté: Directeur CDE (Accès complet)" if is_cde else "✅ Connecté: Directeur d'Incubateur (Accès complet)")
    )
    st.sidebar.success(auth_success_txt)
    if st.sidebar.button("🚪 تسجيل الخروج" if is_arabic else "🚪 Déconnexion", use_container_width=True,
                         key=f"btn_logout_{current_portal}"):
        st.session_state[auth_key] = False
        st.rerun()

    with st.sidebar.expander(
            "📊 تحيين الإحصائيات" if is_arabic else "📊 Mettre à jour les statistiques",
            expanded=False
    ):
        c_proj, c_innov, c_start = get_season_full_stats(selected_season)
        new_c_proj = st.number_input(
            f"{'إجمالي مشاريع موسم' if is_arabic else 'Total projets'} {selected_season}:",
            min_value=0, value=int(c_proj), step=1, key=f"st_proj_{current_portal}"
        )
        new_c_innov = st.number_input(
            f"{metric_label_2}:",
            min_value=0, value=int(c_innov), step=1, key=f"st_innov_{current_portal}"
        )
        new_c_start = st.number_input(
            f"{metric_label_3}:",
            min_value=0, value=int(c_start), step=1, key=f"st_start_{current_portal}"
        )
        if st.button("حفظ وتحديث الإحصائيات" if is_arabic else "Enregistrer les statistiques", use_container_width=True,
                     key=f"btn_save_st_{current_portal}"):
            conn.execute(
                """INSERT INTO season_stats (season_year, total_projects, innovative_certificates, startup_certificates)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(season_year) DO UPDATE SET 
                   total_projects=excluded.total_projects, 
                   innovative_certificates=excluded.innovative_certificates, 
                   startup_certificates=excluded.startup_certificates""",
                (selected_season, new_c_proj, new_c_innov, new_c_start)
            )
            conn.commit()
            flash("تم حفظ وتحديث إحصائيات الموسم بنجاح!" if is_arabic else "Statistiques mises à jour avec succès !")
            st.rerun()

    with st.sidebar.expander(
            "🔒 تغيير كلمة المرور المشفرة" if is_arabic else "🔒 Changer le mot de passe",
            expanded=False
    ):
        old_pwd = st.text_input(
            "كلمة المرور الحالية:" if is_arabic else "Mot de passe actuel :",
            type="password", key=f"old_pwd_{current_portal}"
        )
        new_pwd = st.text_input(
            "كلمة المرور الجديدة:" if is_arabic else "Nouveau mot de passe :",
            type="password", key=f"new_pwd_{current_portal}"
        )
        confirm_pwd = st.text_input(
            "تأكيد كلمة المرور:" if is_arabic else "Confirmer le mot de passe :",
            type="password", key=f"conf_pwd_{current_portal}"
        )
        if st.button(
                "حفظ وتشفير كلمة المرور الجديدة" if is_arabic else "Enregistrer le mot de passe",
                use_container_width=True, key=f"btn_save_pwd_{current_portal}"
        ):
            if not verify_password(user_record["password_hash"], user_record["salt"], old_pwd):
                st.error("كلمة المرور الحالية غير صحيحة!" if is_arabic else "Mot de passe actuel incorrect !")
            elif len(new_pwd.strip()) < 6:
                st.warning("يجب أن تتكون كلمة المرور من 6 أحرف على الأقل." if is_arabic else "Au moins 6 caractères.")
            elif new_pwd != confirm_pwd:
                st.error("كلمتا المرور غير متطابقتين!" if is_arabic else "Les mots de passe ne correspondent pas !")
            else:
                new_h, new_s = hash_password(new_pwd.strip())
                ex("UPDATE users SET password_hash=?, salt=? WHERE id=?", (new_h, new_s, user_record["id"]))
                flash("تم تحديث كلمة المرور بنجاح!" if is_arabic else "Mot de passe mis à jour avec succès !")
                st.rerun()

    with st.sidebar.expander(
            "➕ إدارة المواسم الجامعية" if is_arabic else "➕ Gestion des Années Universitaires",
            expanded=False
    ):
        new_season_input = st.text_input(
            "أدخل سنة الموسم (مثال: 2027/2028):" if is_arabic else "Année (ex: 2027/2028) :",
            key=f"new_season_{current_portal}"
        )
        if st.button(
                "تفعيل واعتماد موسم جديد" if is_arabic else "Activer la nouvelle année",
                use_container_width=True, key=f"btn_season_{current_portal}"
        ):
            clean_s = new_season_input.strip().replace("-", "/")
            if clean_s:
                existing_s = q("SELECT id FROM academic_seasons WHERE season_year=?", (clean_s,), one=True)
                if not existing_s:
                    ex("UPDATE academic_seasons SET is_active=0")
                    ex("INSERT INTO academic_seasons (season_year, is_active) VALUES (?, 1)", (clean_s,))
                    flash(f"تم فتح واعتماد الموسم {clean_s} بنجاح!" if is_arabic else f"Année {clean_s} activée !")
                    st.rerun()
                else:
                    ex("UPDATE academic_seasons SET is_active=0")
                    ex("UPDATE academic_seasons SET is_active=1 WHERE season_year=?", (clean_s,))
                    flash(f"تم التبديل إلى الموسم {clean_s}!" if is_arabic else f"Basculé vers l'année {clean_s} !")
                    st.rerun()

st.sidebar.markdown("---")
unread = q("SELECT * FROM notifications WHERE is_read=0 ORDER BY id DESC LIMIT 10")
with st.sidebar.expander(
        f"{'🔔 الإشعارات الواردة' if is_arabic else '🔔 Notifications'} ({len(unread)})",
        expanded=bool(unread)
):
    if unread:
        for n in unread:
            st.write(f"• {n['message']}")
            st.caption(n["created_at"])
        if st.button("تعليم الكل كمقروء" if is_arabic else "Tout marquer comme lu", key=f"read_all_{current_portal}"):
            ex("UPDATE notifications SET is_read=1")
            st.rerun()
    else:
        st.caption("لا توجد إشعارات جديدة." if is_arabic else "Aucune notification.")


# ==========================================
# 10. دالة عرض فضاء الكلية
# ==========================================
def render_faculty_hub(faculty_display_name: str, tab_idx: int, active_season: str, is_ar: bool, is_authorized: bool):
    clean_s = str(active_season).replace("-", "/")
    faculty_code = FACULTY_CODE_MAP[faculty_display_name]
    cols = SHEET_COLUMNS_AR if is_ar else SHEET_COLUMNS_FR

    st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%); padding: 18px 20px; border-radius: 16px; box-shadow: 0 4px 15px rgba(30, 58, 138, 0.25); text-align: center; margin-bottom: 25px;">
            <h2 style="color: #ffffff; font-size: 24px; font-weight: 900; margin: 0;">
                🏛️ {faculty_display_name}
            </h2>
            <p style="color: #dbeafe; font-size: 14px; margin: 6px 0 0 0; font-weight: 500;">
                {'الموسم الجامعي:' if is_ar else 'Année Universitaire :'} {clean_s}
            </p>
        </div>
    """, unsafe_allow_html=True)

    if not is_authorized:
        st.info("ℹ️ فضاء مخصص للاطلاع والتحميل." if is_ar else "ℹ️ Espace de consultation et de téléchargement.")

    st.markdown(f"""
        <div style="text-align: center; margin: 20px 0 12px 0;">
            <div style="display: inline-block; background: #eff6ff; border: 1.5px solid #bfdbfe; border-radius: 999px; padding: 6px 28px;">
                <h3 style="color: #1e3a8a; font-size: 19px; font-weight: 800; margin: 0;">
                    {'📋 قائمة المشاريع' if is_ar else '📋 Liste des Projets'}
                </h3>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if is_authorized:
        with st.expander(
                f"{'📥 استيراد قائمة المشاريع' if is_ar else '📥 Importer la liste des projets'} ({faculty_display_name})",
                expanded=False
        ):
            col_imp1, col_imp2 = st.columns([2, 1])
            with col_imp1:
                imp_file = st.file_uploader(
                    "اختر ملف إكسل (.xlsx / .xls)" if is_ar else "Choisir un fichier Excel (.xlsx / .xls)",
                    type=["xlsx", "xls"],
                    key=f"imp_excel_{tab_idx}_{is_ar}_{current_portal}",
                )
            with col_imp2:
                imp_mode = st.radio(
                    "طريقة الاستيراد:" if is_ar else "Mode d'importation :",
                    ["استبدال بيانات الجدول الحالي", "إضافة الأسطر إلى الجدول الحالي"] if is_ar else [
                        "Remplacer le tableau actuel", "Ajouter les lignes au tableau actuel"
                    ],
                    key=f"imp_mode_{tab_idx}_{is_ar}_{current_portal}",
                )
                if st.button(
                        "⬆️ تعبئة الجدول من ملف Excel" if is_ar else "⬆️ Charger depuis Excel",
                        key=f"btn_imp_{tab_idx}_{is_ar}_{current_portal}",
                        use_container_width=True
                ):
                    if imp_file is None:
                        st.warning("يرجى اختيار ملف أولاً." if is_ar else "Veuillez choisir un fichier.")
                    else:
                        try:
                            imported_df = read_excel_to_df(imp_file, cols)
                            if imported_df.empty:
                                st.warning("الملف فارغ." if is_ar else "Le fichier est vide.")
                            else:
                                current_mgr_name = "مدير مركز المقاولاتية" if is_cde else "مدير الحاضنة"
                                if "إضافة" in imp_mode or "Ajouter" in imp_mode:
                                    existing_df = load_faculty_df(faculty_code, active_season, cols)
                                    combined_df = pd.concat([existing_df, imported_df], ignore_index=True)
                                    combined_df[cols[0]] = list(range(1, len(combined_df) + 1))
                                    save_faculty_df(faculty_code, active_season, combined_df, current_mgr_name, cols)
                                else:
                                    save_faculty_df(faculty_code, active_season, imported_df, current_mgr_name, cols)

                                st.session_state[f"grid_ver_{tab_idx}_{current_portal}"] = (
                                        st.session_state.get(f"grid_ver_{tab_idx}_{current_portal}", 0) + 1
                                )
                                flash(
                                    f"تم استيراد {len(imported_df)} سطراً بنجاح!" if is_ar else f"{len(imported_df)} lignes importées avec succès !"
                                )
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

    last_meta = q(
        "SELECT updated_by, updated_at FROM faculty_sheets WHERE (faculty_code=? OR faculty=?) AND season_year=? ORDER BY id DESC LIMIT 1",
        (faculty_code, faculty_code, active_season),
        one=True,
    )
    if last_meta and last_meta["updated_by"]:
        st.markdown(
            f"<p style='text-align: center; color: #64748b; font-size: 13px;'>"
            f"{'🕒 آخر تحديث بواسطة:' if is_ar else '🕒 Dernière modification par :'} <b>{last_meta['updated_by']}</b> "
            f"{'بتاريخ:' if is_ar else 'le :'} <code>{last_meta['updated_at']}</code></p>",
            unsafe_allow_html=True
        )

    df_current = load_faculty_df(faculty_code, active_season, cols)
    grid_ver = st.session_state.get(f"grid_ver_{tab_idx}_{current_portal}", 0)

    column_config_dict = {
        cols[0]: st.column_config.NumberColumn(f"1. {cols[0]}", min_value=1, step=1, width="small"),
        cols[1]: st.column_config.TextColumn(f"2. {cols[1]}", width="medium"),
        cols[2]: st.column_config.TextColumn(f"3. {cols[2]}", width="medium"),
        cols[3]: st.column_config.SelectboxColumn(
            f"4. {cols[3]}",
            options=["ليسانس L3", "ماستر 1", "ماستر 2", "دكتوراه"] if is_ar else ["Licence L3", "Master 1", "Master 2",
                                                                                  "Doctorat"],
            width="small",
        ),
        cols[4]: st.column_config.TextColumn(f"5. {cols[4]}", width="medium"),
        cols[5]: st.column_config.TextColumn(f"6. {cols[5]}", width="large"),
    }

    edited_df = st.data_editor(
        df_current,
        num_rows="dynamic" if is_authorized else "fixed",
        disabled=not is_authorized,
        use_container_width=True,
        hide_index=True,
        key=f"grid_{tab_idx}_{active_season}_{grid_ver}_{is_ar}_{current_portal}",
        column_config=column_config_dict
    )

    if is_authorized:
        col_b1, col_b2, col_b3 = st.columns([1.5, 1.5, 1.5])
        with col_b1:
            if st.button("💾 حفظ الجدول" if is_ar else "💾 Enregistrer le tableau",
                         key=f"save_sheet_{tab_idx}_{is_ar}_{current_portal}", use_container_width=True):
                current_mgr_name = "مدير مركز المقاولاتية" if is_cde else "مدير الحاضنة"
                save_faculty_df(faculty_code, active_season, edited_df, current_mgr_name, cols)
                flash("تم حفظ التعديلات بنجاح." if is_ar else "Modifications enregistrées avec succès.")
                st.rerun()
        with col_b2:
            xlsx_export = df_to_xlsx_bytes(edited_df, sheet_name=faculty_display_name, is_rtl=is_ar)
            st.download_button(
                "📗 تحميل بصيغة Excel" if is_ar else "📗 Télécharger Excel",
                data=xlsx_export,
                file_name=f"{faculty_display_name}_{clean_s}.xlsx",
                mime=DOC_MIME["xlsx"],
                key=f"dl_xlsx_{tab_idx}_{is_ar}_{current_portal}",
                use_container_width=True,
            )
        with col_b3:
            pdf_export = df_to_pdf_bytes(edited_df, faculty_display_name, cols, is_rtl=is_ar)
            st.download_button(
                "📕 تحميل بصيغة PDF" if is_ar else "📕 Télécharger PDF",
                data=pdf_export,
                file_name=f"{faculty_display_name}_{clean_s}.pdf",
                mime=DOC_MIME["pdf"],
                key=f"dl_pdf_{tab_idx}_{is_ar}_{current_portal}",
                use_container_width=True,
            )
    else:
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            xlsx_export = df_to_xlsx_bytes(edited_df, sheet_name=faculty_display_name, is_rtl=is_ar)
            st.download_button(
                "📗 تحميل جدول المشاريع (Excel)" if is_ar else "📗 Télécharger la liste (Excel)",
                data=xlsx_export,
                file_name=f"{faculty_display_name}_{clean_s}.xlsx",
                mime=DOC_MIME["xlsx"],
                key=f"dl_xlsx_view_{tab_idx}_{is_ar}_{current_portal}",
                use_container_width=True,
            )
        with col_dl2:
            pdf_export = df_to_pdf_bytes(edited_df, faculty_display_name, cols, is_rtl=is_ar)
            st.download_button(
                "📕 تحميل جدول المشاريع (PDF)" if is_ar else "📕 Télécharger la liste (PDF)",
                data=pdf_export,
                file_name=f"{faculty_display_name}_{clean_s}.pdf",
                mime=DOC_MIME["pdf"],
                key=f"dl_pdf_view_{tab_idx}_{is_ar}_{current_portal}",
                use_container_width=True,
            )

    # محاضر المناقشة
    st.markdown("---")
    st.markdown(f"""
        <div style="text-align: center; margin: 25px 0 12px 0;">
            <div style="display: inline-block; background: #fffbeb; border: 1.5px solid #fde68a; border-radius: 999px; padding: 6px 28px;">
                <h3 style="color: #92400e; font-size: 20px; font-weight: 800; margin: 0;">
                    {'🎓 محاضر المناقشة والمداولات' if is_ar else '🎓 Procès-verbaux de Soutenance'}
                </h3>
            </div>
            <p style="color: #78350f; font-size: 13px; margin: 6px 0 0 0;">
                {'إيداع ومتابعة محاضر لجان المناقشة الرسمية والاطلاع والتحميل المباشر' if is_ar else 'Dépôt, consultation et téléchargement direct des PV des commissions'}
            </p>
        </div>
    """, unsafe_allow_html=True)

    if is_authorized:
        upload_pv_title = "📝 رفع محضر مناقشة / مداولة جديد" if is_ar else "📝 Déposer un nouveau PV"
        with st.expander(upload_pv_title, expanded=False):
            with st.form(f"pv_form_{tab_idx}_{is_ar}_{current_portal}", clear_on_submit=True):
                pv_file = st.file_uploader(
                    "اختر ملف المحضر (PDF أو Excel - حد أقصى 10 ميغابايت)" if is_ar else "Fichier PV (PDF ou Excel - Max 10 Mo)",
                    type=ALLOWED_DOC_EXT,
                    key=f"pv_file_{tab_idx}_{is_ar}_{current_portal}",
                )
                pv_title = st.text_input(
                    "عنوان أو موضوع المحضر (مثال: محضر مناقشة دفعة جوان 2026)" if is_ar else "Titre ou objet du PV :",
                    key=f"pv_title_{tab_idx}_{is_ar}_{current_portal}"
                )

                if st.form_submit_button("📤 إيداع ونشر المحضر" if is_ar else "📤 Déposer et publier le PV"):
                    if pv_file is None:
                        st.warning("يرجى اختيار ملف المحضر." if is_ar else "Veuillez choisir un fichier.")
                    else:
                        ext = pv_file.name.rsplit(".", 1)[-1].lower()
                        data = pv_file.getvalue()
                        if ext not in ALLOWED_DOC_EXT:
                            st.warning("صيغة الملف غير مدعومة." if is_ar else "Format de fichier non supporté.")
                        elif len(data) > MAX_DOC_MB * 1024 * 1024:
                            st.warning("حجم الملف يتجاوز الحد الأقصى." if is_ar else "Fichier trop volumineux.")
                        else:
                            final_pv_title = pv_title.strip() or f"محضر_{pv_file.name}"
                            ex(
                                """INSERT INTO defense_reports 
                                   (title, filename, file_ext, file_data, faculty_code, season_year, uploaded_by, created_at)
                                   VALUES (?,?,?,?,?,?,?,?)""",
                                (final_pv_title, pv_file.name, ext, data, faculty_code, active_season, 1, now_str()),
                            )
                            flash("تم إيداع محضر المناقشة بنجاح." if is_ar else "Procès-verbal déposé avec succès.")
                            st.rerun()

    cur_pv_check = conn.execute("PRAGMA table_info(defense_reports)")
    has_legacy_pv_faculty = "faculty" in [r["name"] for r in cur_pv_check.fetchall()]

    if has_legacy_pv_faculty:
        pvs = q(
            """SELECT r.id, r.title, r.filename, r.file_ext, r.file_data, r.faculty_code,
                      r.season_year, r.uploaded_by, r.created_at, u.name AS uploader
               FROM defense_reports r
               JOIN users u ON u.id = r.uploaded_by
               WHERE (r.faculty_code = ? OR r.faculty = ?) AND r.season_year = ?
               ORDER BY r.id DESC""",
            (faculty_code, faculty_code, active_season),
        )
    else:
        pvs = q(
            """SELECT r.id, r.title, r.filename, r.file_ext, r.file_data, r.faculty_code,
                      r.season_year, r.uploaded_by, r.created_at, u.name AS uploader
               FROM defense_reports r
               JOIN users u ON u.id = r.uploaded_by
               WHERE r.faculty_code = ? AND r.season_year = ?
               ORDER BY r.id DESC""",
            (faculty_code, active_season),
        )

    if not pvs:
        st.info(
            "📌 لا توجد محاضر مناقشة مودعة لهذه الكلية في هذا الموسم حتى الآن." if is_ar else "📌 Aucun PV déposé pour cette faculté durant cette année."
        )
    else:
        for pv in pvs:
            icon = "📕" if pv["file_ext"] == "pdf" else "📗"
            with st.container(border=True):
                col_info, col_btn, col_del = st.columns([5, 2, 1] if is_authorized else [6, 2, 0.1])
                col_info.markdown(f"{icon} **{pv['title']}** (`{pv['file_ext'].upper()}`)")
                meta = f"{'الموسم:' if is_ar else 'Année :'} {pv['season_year']} | {'التاريخ:' if is_ar else 'Date :'} {pv['created_at']} | {'بواسطة:' if is_ar else 'Par :'} **{pv['uploader']}**"
                col_info.caption(meta)
                col_btn.download_button(
                    "⬇️ تحميل المحضر" if is_ar else "⬇️ Télécharger le PV",
                    data=bytes(pv["file_data"]),
                    file_name=pv["filename"],
                    mime=DOC_MIME.get(pv["file_ext"], "application/octet-stream"),
                    key=f"dl_pv_{tab_idx}_{pv['id']}_{is_ar}_{current_portal}",
                    use_container_width=True,
                )
                if is_authorized:
                    if col_del.button("🗑️", key=f"del_pv_{tab_idx}_{pv['id']}_{is_ar}_{current_portal}",
                                      help="حذف المحضر"):
                        ex("DELETE FROM defense_reports WHERE id=?", (pv["id"],))
                        flash("تم حذف المحضر." if is_ar else "PV supprimé.", "🗑️")
                        st.rerun()


# ==========================================
# 11. عرض التبويبات والمحتوى
# ==========================================
is_portal_auth = st.session_state.get(auth_key, False)

if is_arabic:
    tabs_ar = st.tabs([
        "📊 مؤشر مشاريع المقاولاتية" if is_cde else "📊 مؤشر المشاريع الابتكارية",
        FACULTIES_AR[0],
        FACULTIES_AR[1],
        FACULTIES_AR[2],
        FACULTIES_AR[3],
        "📂 القرارات والمراجع",
    ])

    with tabs_ar[0]:
        clean_season_display = str(selected_season).replace("-", "/")
        title_tab_ar = (
            f"📊 مؤشر مشاريع المقاولاتية (الموسم الجامعي: {clean_season_display})"
            if is_cde else
            f"📊 مؤشر المشاريع الابتكارية (الموسم الجامعي: {clean_season_display})"
        )
        st.markdown(f"""
            <div style="background-color: #eef2ff; border-radius: 12px; padding: 18px; margin-bottom: 20px; text-align: center; border: 1.5px solid #c7d2fe;">
                <h2 style="color: #312e81; font-weight: 800; margin: 0; font-size: 24px;">
                    {title_tab_ar}
                </h2>
            </div>
        """, unsafe_allow_html=True)

        total_season_projects, innov_certs, startup_certs = get_season_full_stats(selected_season)

        col_sum1, col_sum2, col_sum3 = st.columns(3)
        col_sum1.metric(f"إجمالي المشاريع المسجلة ({clean_season_display})", f"{total_season_projects} مشروع")
        col_sum2.metric(metric_label_2, f"{innov_certs}")
        col_sum3.metric(metric_label_3, f"{startup_certs:02d}")

        st.markdown("---")
        st.markdown(
            f"<h3 style='text-align: center; font-weight: 800; color: #1e293b; margin-bottom: 20px;'>"
            f"🏛️ توزيع المشاريع الحقيقية حسب الكليات (الموسم الجامعي: {clean_season_display})</h3>",
            unsafe_allow_html=True
        )

        fac_cols = st.columns(4)
        chart_data = []
        for idx, fac_name in enumerate(FACULTIES_AR):
            fac_code = FACULTY_CODE_MAP[fac_name]
            fac_count = get_faculty_project_count(fac_code, selected_season)
            chart_data.append({"الكلية": fac_name, "عدد المشاريع": fac_count})
            with fac_cols[idx]:
                with st.container(border=True):
                    st.markdown(f"<div class='faculty-right-label'>🎓 {fac_name}</div>", unsafe_allow_html=True)
                    st.metric("عدد المشاريع المسجلة", f"{fac_count}")

        st.markdown("---")
        st.markdown(
            f"<h3 style='text-align: center; font-weight: 800; color: #1e293b; margin-bottom: 15px;'>"
            f"📊 مؤشر توزيع المشاريع بيانيًا (الموسم الجامعي: {clean_season_display})</h3>",
            unsafe_allow_html=True
        )

        df_chart = pd.DataFrame(chart_data)
        if df_chart["عدد المشاريع"].sum() > 0:
            fig = px.bar(
                df_chart,
                x="عدد المشاريع",
                y="الكلية",
                orientation='h',
                color="الكلية",
                color_discrete_sequence=FACULTY_COLORS,
                text="عدد المشاريع"
            )
            fig.update_layout(
                yaxis=dict(automargin=True),
                margin=dict(l=20, r=200, t=50, b=50),
                showlegend=False,
                xaxis_title="عدد المشاريع",
                yaxis_title=None
            )
            fig.update_traces(textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"لا توجد مشاريع مسجلة في جداول الكليات للموسم الجامعي {clean_season_display} لعرضها بيانيًا.")

    with tabs_ar[1]:
        render_faculty_hub(FACULTIES_AR[0], tab_idx=1, active_season=selected_season, is_ar=True,
                           is_authorized=is_portal_auth)

    with tabs_ar[2]:
        render_faculty_hub(FACULTIES_AR[1], tab_idx=2, active_season=selected_season, is_ar=True,
                           is_authorized=is_portal_auth)

    with tabs_ar[3]:
        render_faculty_hub(FACULTIES_AR[2], tab_idx=3, active_season=selected_season, is_ar=True,
                           is_authorized=is_portal_auth)

    with tabs_ar[4]:
        render_faculty_hub(FACULTIES_AR[3], tab_idx=4, active_season=selected_season, is_ar=True,
                           is_authorized=is_portal_auth)

    with tabs_ar[5]:
        st.markdown("""
            <div style="background-color: #ecfdf5; border-radius: 12px; padding: 18px; margin-bottom: 20px; text-align: center; border: 1.5px solid #a7f3d0;">
                <h2 style="color: #065f46; font-weight: 800; margin: 0; font-size: 24px;">📚 القرارات الوزارية والمكتبة المرجعية</h2>
            </div>
        """, unsafe_allow_html=True)

        if is_portal_auth:
            with st.form("ar_res_form", clear_on_submit=True):
                r_title = st.text_input("عنوان المورد / القرار الوزاري:")
                r_cat = st.selectbox("التصنيف:", ["قرارات وزارية وبيداغوجية", "أدلة ونماذج إدارية", "أدلة مقاولاتية"])
                r_link = st.text_input("رابط التحميل أو المعاينة:", "https://")
                if st.form_submit_button("إضافة إلى المكتبة"):
                    if not r_title.strip():
                        st.warning("يرجى إدخال العنوان.")
                    elif not valid_url(r_link):
                        st.warning("يرجى إدخال رابط صحيح.")
                    else:
                        ex(
                            "INSERT INTO resources (title, category, link, uploaded_by) VALUES (?,?,?,?)",
                            (r_title.strip(), r_cat, r_link.strip(), 1)
                        )
                        flash("تمت الإضافة بنجاح إلى المكتبة.")
                        st.rerun()

        resources = q(
            "SELECT r.*, u.name AS uploader FROM resources r JOIN users u ON u.id = r.uploaded_by ORDER BY r.id DESC")
        if not resources:
            st.caption("لا توجد موارد أو قرارات منشورة حالياً.")
        for r in resources:
            col_txt, col_del = st.columns([6, 1])
            col_txt.markdown(f"- 📄 **{r['title']}** (`{r['category']}`) - [رابط التحميل والإطلاع]({r['link']})")
            if is_portal_auth:
                if col_del.button("🗑️", key=f"del_res_ar_{r['id']}_{current_portal}"):
                    ex("DELETE FROM resources WHERE id=?", (r["id"],))
                    flash("تم الحذف بنجاح.", "🗑️")
                    st.rerun()

else:
    # --- Page Française ---
    tabs_fr = st.tabs([
        "📊 Indicateurs CDE" if is_cde else "📊 Indicateurs des Projets",
        FACULTIES_FR[0],
        FACULTIES_FR[1],
        FACULTIES_FR[2],
        FACULTIES_FR[3],
        "📂 Arrêtés & Références",
    ])

    with tabs_fr[0]:
        clean_season_display = str(selected_season).replace("-", "/")
        title_tab_fr = (
            f"📊 Tableau de Bord - Projets CDE (Année : {clean_season_display})"
            if is_cde else
            f"📊 Tableau de Bord des Projets Innovants (Année : {clean_season_display})"
        )
        st.markdown(f"""
            <div style="background-color: #eef2ff; border-radius: 12px; padding: 18px; margin-bottom: 20px; text-align: center; border: 1.5px solid #c7d2fe;">
                <h2 style="color: #312e81; font-weight: 800; margin: 0; font-size: 24px;">
                    {title_tab_fr}
                </h2>
            </div>
        """, unsafe_allow_html=True)

        total_season_projects, innov_certs, startup_certs = get_season_full_stats(selected_season)

        col_sum1, col_sum2, col_sum3 = st.columns(3)
        col_sum1.metric(f"Total Projets Enregistrés ({clean_season_display})", f"{total_season_projects}")
        col_sum2.metric(metric_label_2, f"{innov_certs}")
        col_sum3.metric(metric_label_3, f"{startup_certs:02d}")

        st.markdown("---")
        st.markdown(
            f"<h3 style='text-align: center; font-weight: 800; color: #1e293b; margin-bottom: 20px;'>"
            f"🏛️ Répartition Réelle des Projets par Faculté ({clean_season_display})</h3>",
            unsafe_allow_html=True
        )

        fac_cols = st.columns(4)
        chart_data_fr = []
        for idx, fac_name in enumerate(FACULTIES_FR):
            fac_code = FACULTY_CODE_MAP[fac_name]
            fac_count = get_faculty_project_count(fac_code, selected_season)
            chart_data_fr.append({"Faculté": fac_name, "Nombre de Projets": fac_count})
            with fac_cols[idx]:
                with st.container(border=True):
                    st.markdown(f"<div class='faculty-right-label'>🎓 {fac_name}</div>", unsafe_allow_html=True)
                    st.metric("Total Projets", f"{fac_count}")

        st.markdown("---")
        st.markdown(
            f"<h3 style='text-align: center; font-weight: 800; color: #1e293b; margin-bottom: 15px;'>"
            f"📊 Distribution Graphique des Projets ({clean_season_display})</h3>",
            unsafe_allow_html=True
        )

        df_chart_fr = pd.DataFrame(chart_data_fr)
        if df_chart_fr["Nombre de Projets"].sum() > 0:
            fig = px.bar(
                df_chart_fr,
                x="Nombre de Projets",
                y="Faculté",
                orientation='h',
                color="Faculté",
                color_discrete_sequence=FACULTY_COLORS,
                text="Nombre de Projets"
            )
            fig.update_layout(
                yaxis=dict(automargin=True),
                margin=dict(l=220, r=20, t=50, b=50),
                showlegend=False,
                xaxis_title="Nombre de Projets",
                yaxis_title=None
            )
            fig.update_traces(textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"Aucun projet enregistré dans les tableaux pour l'année universitaire {clean_season_display}.")

    with tabs_fr[1]:
        render_faculty_hub(FACULTIES_FR[0], tab_idx=1, active_season=selected_season, is_ar=False,
                           is_authorized=is_portal_auth)

    with tabs_fr[2]:
        render_faculty_hub(FACULTIES_FR[1], tab_idx=2, active_season=selected_season, is_ar=False,
                           is_authorized=is_portal_auth)

    with tabs_fr[3]:
        render_faculty_hub(FACULTIES_FR[2], tab_idx=3, active_season=selected_season, is_ar=False,
                           is_authorized=is_portal_auth)

    with tabs_fr[4]:
        render_faculty_hub(FACULTIES_FR[3], tab_idx=4, active_season=selected_season, is_ar=False,
                           is_authorized=is_portal_auth)

    with tabs_fr[5]:
        st.markdown("""
            <div style="background-color: #ecfdf5; border-radius: 12px; padding: 18px; margin-bottom: 20px; text-align: center; border: 1.5px solid #a7f3d0;">
                <h2 style="color: #065f46; font-weight: 800; margin: 0; font-size: 24px;">📚 Arrêtés Ministériels et Bibliothèque</h2>
            </div>
        """, unsafe_allow_html=True)

        if is_portal_auth:
            with st.form("fr_res_form", clear_on_submit=True):
                r_title = st.text_input("Titre du document :")
                r_cat = st.selectbox("Catégorie :",
                                     ["Arrêtés Ministériels", "Guides et Modèles", "Guides Entrepreneuriat"])
                r_link = st.text_input("Lien de téléchargement :", "https://")
                if st.form_submit_button("Ajouter à la bibliothèque"):
                    if not r_title.strip():
                        st.warning("Veuillez saisir un titre.")
                    elif not valid_url(r_link):
                        st.warning("Veuillez saisir un lien valide.")
                    else:
                        ex(
                            "INSERT INTO resources (title, category, link, uploaded_by) VALUES (?,?,?,?)",
                            (r_title.strip(), r_cat, r_link.strip(), 1)
                        )
                        flash("Document ajouté avec succès.")
                        st.rerun()

        resources = q(
            "SELECT r.*, u.name AS uploader FROM resources r JOIN users u ON u.id = r.uploaded_by ORDER BY r.id DESC")
        if not resources:
            st.caption("Aucune ressource disponible pour le moment.")
        for r in resources:
            col_txt, col_del = st.columns([6, 1])
            col_txt.markdown(f"- 📄 **{r['title']}** (`{r['category']}`) - [Lien de Téléchargement]({r['link']})")
            if is_portal_auth:
                if col_del.button("🗑️", key=f"del_res_fr_{r['id']}_{current_portal}"):
                    ex("DELETE FROM resources WHERE id=?", (r["id"],))
                    flash("Document supprimé.", "🗑️")
                    st.rerun()

# ==========================================
# 12. تذييل الصفحة (Footer)
# ==========================================
if is_arabic:
    st.markdown("""
        <div class="app-footer">
            <div class="footer-social-links">
                <a href="https://www.univ-temouchent.edu.dz/" target="_blank">🌐 موقع جامعة عين تموشنت</a>
                <a href="https://www.facebook.com/CU.Belhadj.Bouchaib" target="_blank">🔵 صفحة فايسبوك الجامعة</a>
                <a href="https://www.facebook.com/profile.php?id=61572561927203" target="_blank">💡 صفحة فايسبوك حاضنة الأعمال</a>
                <a href="https://www.facebook.com/profile.php?id=61555986874987" target="_blank">🚀 صفحة فايسبوك CDE</a>
            </div>
            <p style="margin: 0; font-weight: 700; color: #1e293b;">
                جامعة عين تموشنت بلحاج بوشعيب - جميع الحقوق محفوظة © 2026
            </p>
            <p style="margin: 4px 0 0 0; font-size: 13px; color: #64748b;">
                نسخة تجريبية | التطوير أ.د محمد بوطوبة
            </p>
        </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <div class="app-footer">
            <div class="footer-social-links">
                <a href="https://www.univ-temouchent.edu.dz/" target="_blank">🌐 Site Web Université</a>
                <a href="https://www.facebook.com/CU.Belhadj.Bouchaib" target="_blank">🔵 Facebook Université</a>
                <a href="https://www.facebook.com/profile.php?id=61572561927203" target="_blank">💡 Facebook Incubateur</a>
                <a href="https://www.facebook.com/profile.php?id=61555986874987" target="_blank">🚀 Facebook CDE</a>
            </div>
            <p style="margin: 0; font-weight: 700; color: #1e293b;">
                Université d'Ain Témouchent Belhadj Bouchaib - Tous droits réservés © 2026
            </p>
            <p style="margin: 4px 0 0 0; font-size: 13px; color: #64748b;">
                Version bêta | Développé par : Pr Mohammed Boutouba
            </p>
        </div>
    """, unsafe_allow_html=True)
