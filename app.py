import json
from datetime import date, timedelta
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import psycopg
import streamlit as st

st.set_page_config(
    page_title="PULSE · Gym, Übungen, Supps & Weight",
    page_icon="[PULSE]",
    layout="wide",
)

DATA_FILE = Path("gym_daten.json")
STACK_FILE = Path("mein_supplement_stack.json")
EXERCISES_FILE = Path("meine_uebungen.json")
WEIGHT_FILE = Path("koerpergewicht.json")

DEFAULT_ACTIVE_SUPPS = [
    "Kreatin (Ultrapure Creatine)",
    "Zink",
    "Magnesium (Complex / Bisglycinat)",
    "Vitamin D3 + K2",
]

SUPPLEMENTS_CATALOG = [
    {
        "name": "Kreatin (Ultrapure Creatine)",
        "kategorie": "Kraft & Energie",
        "einnahme": "Meist 3–5 g täglich (egal ob Trainingstag oder Pause)",
        "wirkung": "Unterstützt die schnelle ATP-Energiebereitstellung bei intensiven Sätzen und hilft vielen bei Kraft- und Leistungssteigerung im Training.",
        "tipp": "Konstant täglich nehmen – ausreichend Wasser über den Tag trinken.",
    },
    {
        "name": "Zink",
        "kategorie": "Mikronährstoffe & Immunsystem",
        "einnahme": "Meist täglich zu einer Mahlzeit",
        "wirkung": "Trägt zu einer normalen Funktion des Immunsystems, zum Schutz der Zellen vor oxidativem Stress sowie zu Haut, Haaren und Stoffwechsel bei.",
        "tipp": "Auf leeren Magen kann Zink manchmal unangenehm sein – am besten zu einer Mahlzeit einnehmen.",
    },
    {
        "name": "Magnesium (Complex / Bisglycinat)",
        "kategorie": "Muskel & Regeneration",
        "einnahme": "Oft abends oder im Alltag nach dem Training",
        "wirkung": "Unterstützt die normale Muskelfunktion, das Nervensystem sowie die Verringerung von Müdigkeit und Ermüdung.",
        "tipp": "Komplex- oder Bisglycinat-Varianten werden im Alltag häufig besonders gut vertragen.",
    },
    {
        "name": "Vitamin D3 + K2",
        "kategorie": "Vitamine & Knochen",
        "einnahme": "Täglich oder im Wochenrhythmus zu einer Mahlzeit",
        "wirkung": "Vitamin D3 unterstützt Immunsystem und Muskelfunktion; gemeinsam mit K2 trägt es zur Erhaltung normaler Knochen bei.",
        "tipp": "Fettlösliche Vitamine wie D3 und K2 am besten zusammen mit einer Mahlzeit einnehmen.",
    },
    {
        "name": "Omega-3 (EPA & DHA)",
        "kategorie": "Fettsäuren & Basis",
        "einnahme": "Täglich zu einer Mahlzeit",
        "wirkung": "EPA und DHA unterstützen die normale Herzfunktion, DHA trägt zur Erhaltung einer normalen Gehirnfunktion bei.",
        "tipp": "Auf konkrete EPA- und DHA-Angaben achten und gut zum Essen einnehmen.",
    },
    {
        "name": "Designer Whey Protein",
        "kategorie": "Protein & Muskelaufbau",
        "einnahme": "Nach dem Training, morgens oder als Snack zwischendurch",
        "wirkung": "Liefert hochwertiges Molkenprotein, um den täglichen Eiweißbedarf für Muskelaufbau und Regeneration praktisch zu decken.",
        "tipp": "Praktische Ergänzung zum Alltag – normale Mahlzeiten bleiben die Basis.",
    },
    {
        "name": "Isoclear Whey Isolate",
        "kategorie": "Protein (Klar & Fruchtig)",
        "einnahme": "Rund ums Training oder an warmen Tagen statt Milchshake",
        "wirkung": "Klares Molkenprotein-Isolat mit frischer, leichter Konsistenz für eine unkomplizierte Proteinzufuhr.",
        "tipp": "Angenehm leicht, wenn dir cremige Shakes beim oder nach dem Training zu schwer sind.",
    },
    {
        "name": "EAA (Essenzielle Aminosäuren)",
        "kategorie": "Intra / Peri-Workout",
        "einnahme": "Vor oder während des Trainings",
        "wirkung": "Enthält alle neun essenziellen Aminosäuren, die der Körper nicht selbst synthetisieren kann.",
        "tipp": "Vor allem interessant bei nüchternem Training oder längeren Einheiten.",
    },
    {
        "name": "Ashwagandha (Ashwa+ / KSM-66)",
        "kategorie": "Stress & Abendroutine",
        "einnahme": "Häufig abends oder in intensiven Phasen",
        "wirkung": "Pflanzenextrakt, der im Alltag und bei mentaler Belastung oder Abendroutinen häufig ergänzend genutzt wird.",
        "tipp": "Auf Verträglichkeit achten und bei Bedarf Einnahmepausen einplanen.",
    },
    {
        "name": "Multivitamin / Daily / Essentials",
        "kategorie": "All-in-One Basis",
        "einnahme": "Täglich als Basis-Routine",
        "wirkung": "Kombiniert wichtige Vitamine und Mikronährstoffe, um mögliche Lücken in der täglichen Ernährung abzufedern.",
        "tipp": "Doppelungen mit Einzelpräparaten (z. B. Zink oder D3+K2) im Blick behalten.",
    },
    {
        "name": "Elektrolyte / Hydration",
        "kategorie": "Flüssigkeit & Performance",
        "einnahme": "Bei schweißtreibendem Training, Hitze oder langen Sessions",
        "wirkung": "Unterstützt den Flüssigkeits- und Elektrolythaushalt (z. B. Natrium, Kalium, Magnesium), wenn du stark schwitzt.",
        "tipp": "Besonders hilfreich bei langen Einheiten oder warmen Temperaturen.",
    },
    {
        "name": "Kollagen (Collagen Peptides)",
        "kategorie": "Struktur & Regeneration",
        "einnahme": "Täglich (z. B. im Shake, Kaffee oder neutral eingerührt)",
        "wirkung": "Liefert Kollagenpeptide als Baustein für Bindegewebe, Sehnen und Gelenkstrukturen im Zusammenspiel mit Training.",
        "tipp": "Funktioniert vor allem über regelmäßige Einnahme über mehrere Wochen.",
    },
    {
        "name": "Pre-Workout / Koffein",
        "kategorie": "Fokus & Antrieb",
        "einnahme": "Ca. 20–45 Minuten vor dem Training",
        "wirkung": "Koffein kann Wachheit, Fokus und gefühlte Leistungsfähigkeit vor harten Einheiten spürbar steigern.",
        "tipp": "Bei Training am Nachmittag/Abend vorsichtig dosieren, damit dein Schlaf gut bleibt.",
    },
]

MUSCLE_GROUPS = {
    "Brust": {
        "primaer": "Großer Brustmuskel (Pectoralis major)",
        "sekundaer": "Vordere Schulter, Trizeps, Sägemuskel",
        "highlight": "chest",
        "exercises": [
            "Butterfly (Gerät)",
            "Brustpresse (Maschine)",
            "Liegestütze",
            "Dips (Brust-Fokus)",
            "Bankdrücken (Langhantel)",
            "Schrägbankdrücken (Kurzhanteln)",
            "Flachbankdrücken (Kurzhanteln)",
            "Cable Flys / Kabelzug-Flys",
            "Negativ-Bankdrücken",
            "Überzüge (Pullover)",
        ],
    },
    "Rücken": {
        "primaer": "Breiter Rückenmuskel (Latissimus), Trapezmuskel",
        "sekundaer": "Hintere Schulter, Bizeps, Rhomboiden, unterer Rücken",
        "highlight": "back",
        "exercises": [
            "Latzug zur Brust",
            "Rudern am Kabelzug",
            "Langhantel-Rudern vorgebeugt",
            "Kurzhantel-Rudern einarmig",
            "Klimmzüge",
            "T-Bar-Rudern",
            "Rudermaschine / Chest-Supported Row",
            "Überzüge am Kabelzug",
            "Kreuzheben",
            "Hyperextensions / Rückenstrecker",
        ],
    },
    "Beine": {
        "primaer": "Quadrizeps (Vorderseite), Beinbeuger, Gesäß (Gluteus)",
        "sekundaer": "Wadenmuskulatur, Adduktoren, Rumpf",
        "highlight": "legs",
        "exercises": [
            "Kniebeugen (Langhantel)",
            "Beinpresse (45° / Maschine)",
            "Beinstrecker (Maschine)",
            "Beinbeuger liegend oder sitzend",
            "Rumänisches Kreuzheben",
            "Ausfallschritte / Lunges",
            "Bulgarian Split Squats",
            "Hip Thrusts",
            "Wadenheben stehend",
            "Wadenheben sitzend",
        ],
    },
    "Bizeps": {
        "primaer": "Zweiköpfiger Armbeuger (Bizeps brachii)",
        "sekundaer": "Oberarmspeichenmuskel (Brachioradialis), Armbeuger",
        "highlight": "biceps",
        "exercises": [
            "Langhantel-Curls",
            "SZ-Stangen-Curls",
            "Kurzhantel-Curls abwechselnd",
            "Hammer-Curls",
            "Scott-Curls / Preacher Curls",
            "Schrägbank-Curls",
            "Kabelzug-Curls mit Stange oder Seil",
            "Konzentrations-Curls",
            "Spider-Curls",
            "Reverse-Curls",
        ],
    },
    "Trizeps": {
        "primaer": "Dreiköpfiger Armstrecker (Trizeps brachii)",
        "sekundaer": "Vordere Schulter, Brust (bei Drückvarianten)",
        "highlight": "triceps",
        "exercises": [
            "Trizepsdrücken am Kabelzug (Seil)",
            "Trizepsdrücken am Kabelzug (Stange/V-Griff)",
            "French Press / Stirndrücken (SZ-Stange)",
            "Überkopf-Trizepsdrücken (Kabel oder Kurzhantel)",
            "Dips (aufrechter/Trizeps-Fokus)",
            "Enges Bankdrücken",
            "Kickbacks (Kurzhantel oder Kabel)",
            "Einarmiges Kabel-Pushdown",
            "JM Press / Skullcrushers-Variante",
            "Diamant-Liegestütze",
        ],
    },
    "Schultern": {
        "primaer": "Deltamuskel (vorderer, seitlicher, hinterer Kopf)",
        "sekundaer": "Trizeps, Trapezmuskel, Rotatorenmanschette",
        "highlight": "shoulders",
        "exercises": [
            "Seitheben (Kurzhanteln)",
            "Seitheben am Kabelzug",
            "Seitheben-Maschine",
            "Schulterdrücken / Überkopfdrücken (Kurzhanteln)",
            "Military Press / Schulterdrücken (Langhantel)",
            "Schulterpresse (Maschine)",
            "Frontheben",
            "Vorgebeugtes Seitheben (hintere Schulter)",
            "Reverse Butterfly / Reverse Flys",
            "Face Pulls am Kabelzug",
        ],
    },
}

DEFAULT_SELECTED_EXERCISES = [
    ex for group in MUSCLE_GROUPS.values() for ex in group["exercises"]
]

SPLIT_PRESETS = ["Push", "Pull", "Beine", "Schultern", "Oberkörper", "Ganzkörper"]

APP_CSS = """
<style>
    .stApp {
        background:
            radial-gradient(circle at 12% 8%, rgba(45, 212, 191, 0.14) 0%, transparent 36%),
            radial-gradient(circle at 88% 14%, rgba(168, 85, 247, 0.12) 0%, transparent 38%),
            linear-gradient(180deg, #0d131a 0%, #080b10 100%);
        color: #f3f6fa;
    }
    .block-container {
        padding-top: 1.25rem;
        padding-bottom: 3rem;
        max-width: 1360px;
    }
    .app-header {
        background: linear-gradient(135deg, rgba(22, 30, 41, 0.94) 0%, rgba(13, 18, 26, 0.97) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 24px;
        padding: 20px 24px;
        margin-bottom: 16px;
        box-shadow: 0 20px 45px rgba(0, 0, 0, 0.45);
    }
    .app-badge {
        display: inline-block;
        background: rgba(45, 212, 191, 0.14);
        color: #5eead4;
        border: 1px solid rgba(94, 234, 212, 0.3);
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        padding: 4px 11px;
        border-radius: 999px;
        margin-bottom: 8px;
    }
    .app-title {
        font-size: 1.85rem;
        font-weight: 800;
        color: #ffffff;
        margin: 0 0 4px 0;
        letter-spacing: -0.02em;
    }
    .app-sub {
        color: #94a3b8;
        font-size: 0.94rem;
        margin: 0;
    }
    .surface-card {
        background: rgba(18, 24, 33, 0.92);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 22px;
        padding: 18px 20px;
        margin-bottom: 16px;
        box-shadow: 0 14px 32px rgba(0, 0, 0, 0.35);
    }
    .stat-tile {
        background: rgba(20, 27, 37, 0.94);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 18px;
        padding: 14px 16px;
        box-shadow: 0 10px 24px rgba(0, 0, 0, 0.28);
    }
    .stat-tile-mint { border-top: 3px solid #2dd4bf; }
    .stat-tile-violet { border-top: 3px solid #a855f7; }
    .stat-tile-amber { border-top: 3px solid #f59e0b; }
    .stat-tile-green { border-top: 3px solid #22c55e; }
    .tile-label {
        font-size: 0.73rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #94a3b8;
        font-weight: 700;
    }
    .tile-number {
        font-size: 1.48rem;
        font-weight: 800;
        color: #ffffff;
        margin-top: 4px;
    }
    .tile-note {
        font-size: 0.78rem;
        color: #cbd5e1;
        margin-top: 2px;
    }
    .week-row {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 10px;
        margin-top: 8px;
    }
    .day-pill {
        background: rgba(13, 18, 26, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 10px 6px;
        text-align: center;
    }
    .day-pill-done {
        background: rgba(45, 212, 191, 0.12);
        border: 1px solid rgba(94, 234, 212, 0.45);
    }
    .day-pill-today {
        border: 1.5px solid #a855f7;
    }
    .day-name {
        font-size: 0.75rem;
        color: #94a3b8;
        font-weight: 700;
        margin-bottom: 6px;
    }
    .day-circle {
        width: 30px;
        height: 30px;
        line-height: 30px;
        border-radius: 999px;
        margin: 0 auto;
        font-size: 0.82rem;
        font-weight: 800;
        background: rgba(30, 41, 59, 0.85);
        color: #cbd5e1;
    }
    .day-pill-done .day-circle {
        background: #2dd4bf;
        color: #051316;
    }
    .supp-card {
        background: rgba(18, 24, 33, 0.92);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 16px 18px;
        margin-bottom: 10px;
        box-shadow: 0 12px 26px rgba(0, 0, 0, 0.3);
    }
    .supp-card-active {
        border: 1px solid rgba(94, 234, 212, 0.45);
        background: linear-gradient(145deg, rgba(20, 42, 46, 0.94) 0%, rgba(18, 24, 33, 0.96) 100%);
    }
    .badge-cat {
        display: inline-block;
        background: rgba(168, 85, 247, 0.16);
        color: #d8b4fe;
        border: 1px solid rgba(216, 180, 254, 0.3);
        font-size: 0.72rem;
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 999px;
        margin-bottom: 8px;
    }
    .badge-mine {
        display: inline-block;
        background: rgba(45, 212, 191, 0.18);
        color: #5eead4;
        border: 1px solid rgba(94, 234, 212, 0.38);
        font-size: 0.72rem;
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 999px;
        margin-left: 6px;
        margin-bottom: 8px;
    }
    .supp-heading {
        font-size: 1.08rem;
        font-weight: 700;
        color: #ffffff;
        margin: 0 0 6px 0;
    }
    .supp-detail {
        background: rgba(9, 13, 19, 0.72);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 14px;
        padding: 10px 12px;
        font-size: 0.83rem;
        color: #cbd5e1;
        margin-top: 8px;
    }
    .anatomy-box {
        background: rgba(11, 16, 24, 0.92);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 18px;
        padding: 14px;
        text-align: center;
    }
    .draft-item {
        background: rgba(13, 18, 26, 0.88);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 12px 14px;
        margin-bottom: 8px;
    }
    div[data-testid="stForm"] {
        background: rgba(18, 24, 33, 0.92);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 22px;
        padding: 18px 20px;
        box-shadow: 0 14px 32px rgba(0, 0, 0, 0.35);
    }
    button[data-testid="stBaseButton-secondaryFormSubmit"], button[data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, #2dd4bf 0%, #10b981 100%) !important;
        color: #051316 !important;
        border: none !important;
        border-radius: 14px !important;
        font-weight: 800 !important;
    }
    button[data-testid="stBaseButton-secondaryFormSubmit"]:hover, button[data-testid="stBaseButton-primary"]:hover {
        filter: brightness(1.07);
    }
</style>
"""


def load_list(path: Path, default_items: list) -> list:
    if not path.exists():
        return list(default_items)
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, list) else list(default_items)
    except Exception:
        return list(default_items)


def save_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def estimate_1rm(weight: float, reps: int) -> float:
    if weight <= 0 or reps <= 0:
        return 0.0
    if reps == 1:
        return float(weight)
    return float(weight * (1 + reps / 30.0))


def get_db_connection():
    cfg = st.secrets["postgres"]
    return psycopg.connect(
        host=cfg["host"],
        port=int(cfg["port"]),
        dbname=cfg["dbname"],
        user=cfg["user"],
        password=cfg["password"],
        sslmode="require",
    )


def infer_split_from_exercise(ex_name: str) -> str:
    ex_low = (ex_name or "").lower()
    for group_name, info in MUSCLE_GROUPS.items():
        for ex in info["exercises"]:
            if ex.lower() == ex_low:
                if group_name in ("Brust", "Trizeps"):
                    return "Push"
                if group_name in ("Rücken", "Bizeps"):
                    return "Pull"
                return group_name
    if any(k in ex_low for k in ("bank", "butterfly", "trizeps", "dips", "push")):
        return "Push"
    if any(k in ex_low for k in ("rudern", "lat", "klimm", "curl", "bizeps", "pull", "kreuzheben")):
        return "Pull"
    if any(k in ex_low for k in ("bein", "squat", "kniebeuge", "waden", "hip thrust", "lunges")):
        return "Beine"
    if any(k in ex_low for k in ("schulter", "seitheben", "press", "face pull")):
        return "Schultern"
    return "Trainingstag"


def load_workouts_db():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT datum, uebung, gewicht, wiederholungen FROM workouts ORDER BY id ASC")
            rows = cur.fetchall()

        local_meta = load_list(DATA_FILE, [])
        meta_idx = 0
        result = []
        for idx, r in enumerate(rows, start=1):
            datum_val = str(r[0])
            uebung_val = str(r[1])
            gewicht_val = float(r[2])
            wdh_val = int(r[3])

            split_val = infer_split_from_exercise(uebung_val)
            satz_nr = 1
            notiz_val = ""
            if meta_idx < len(local_meta):
                m = local_meta[meta_idx]
                if str(m.get("datum")) == datum_val and str(m.get("uebung")) == uebung_val:
                    split_val = m.get("trainingstag") or split_val
                    satz_nr = int(m.get("satz_nr", 1))
                    notiz_val = m.get("notiz", "")
                    meta_idx += 1

            result.append({
                "id": idx,
                "datum": datum_val,
                "trainingstag": split_val,
                "uebung": uebung_val,
                "satz_nr": satz_nr,
                "saetze": 1,
                "wiederholungen": wdh_val,
                "gewicht_kg": gewicht_val,
                "volumen_kg": round(gewicht_val * wdh_val, 1),
                "geschaetzt_1rm_kg": round(estimate_1rm(gewicht_val, wdh_val), 1),
                "notiz": notiz_val,
            })
        return result
    finally:
        conn.close()


def save_workout_db(datum_str, uebung_str, gewicht_val, wdh_val):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO workouts (datum, uebung, gewicht, wiederholungen) VALUES (%s, %s, %s, %s)",
                (datum_str, uebung_str, float(gewicht_val), int(wdh_val)),
            )
        conn.commit()
    finally:
        conn.close()


def render_muscle_svg(highlight_key: str) -> str:
    base_fill = "#243042"
    active_fill = "#2dd4bf"
    sec_fill = "#a855f7"

    chest_c = active_fill if highlight_key == "chest" else base_fill
    shoulders_f = active_fill if highlight_key == "shoulders" else (sec_fill if highlight_key == "chest" else base_fill)
    shoulders_b = active_fill if highlight_key == "shoulders" else (sec_fill if highlight_key == "back" else base_fill)
    biceps_c = active_fill if highlight_key == "biceps" else base_fill
    triceps_c = active_fill if highlight_key == "triceps" else base_fill
    back_c = active_fill if highlight_key == "back" else (sec_fill if highlight_key == "legs" else base_fill)
    legs_f = active_fill if highlight_key == "legs" else base_fill
    legs_b = active_fill if highlight_key == "legs" else (sec_fill if highlight_key == "back" else base_fill)

    svg = (
        f'<svg viewBox="0 0 340 210" width="100%" height="205" xmlns="http://www.w3.org/2000/svg">'
        f'<text x="85" y="18" fill="#94a3b8" font-size="11" font-weight="700" text-anchor="middle">VORDERSEITE</text>'
        f'<circle cx="85" cy="36" r="11" fill="#334155"/>'
        f'<rect x="78" y="47" width="14" height="7" rx="3" fill="#334155"/>'
        f'<rect x="65" y="55" width="19" height="22" rx="6" fill="{chest_c}"/>'
        f'<rect x="86" y="55" width="19" height="22" rx="6" fill="{chest_c}"/>'
        f'<ellipse cx="57" cy="61" rx="8" ry="9" fill="{shoulders_f}"/>'
        f'<ellipse cx="113" cy="61" rx="8" ry="9" fill="{shoulders_f}"/>'
        f'<rect x="47" y="72" width="10" height="24" rx="5" fill="{biceps_c}"/>'
        f'<rect x="113" y="72" width="10" height="24" rx="5" fill="{biceps_c}"/>'
        f'<rect x="44" y="99" width="9" height="28" rx="4" fill="#1e293b"/>'
        f'<rect x="117" y="99" width="9" height="28" rx="4" fill="#1e293b"/>'
        f'<rect x="69" y="79" width="32" height="36" rx="7" fill="#1e293b"/>'
        f'<rect x="67" y="118" width="15" height="44" rx="7" fill="{legs_f}"/>'
        f'<rect x="88" y="118" width="15" height="44" rx="7" fill="{legs_f}"/>'
        f'<rect x="68" y="165" width="13" height="34" rx="6" fill="{legs_f}"/>'
        f'<rect x="89" y="165" width="13" height="34" rx="6" fill="{legs_f}"/>'
        f'<text x="255" y="18" fill="#94a3b8" font-size="11" font-weight="700" text-anchor="middle">RÜCKSEITE</text>'
        f'<circle cx="255" cy="36" r="11" fill="#334155"/>'
        f'<rect x="248" y="47" width="14" height="7" rx="3" fill="#334155"/>'
        f'<polygon points="234,55 276,55 268,108 242,108" fill="{back_c}"/>'
        f'<ellipse cx="227" cy="61" rx="8" ry="9" fill="{shoulders_b}"/>'
        f'<ellipse cx="283" cy="61" rx="8" ry="9" fill="{shoulders_b}"/>'
        f'<rect x="217" y="72" width="10" height="24" rx="5" fill="{triceps_c}"/>'
        f'<rect x="283" y="72" width="10" height="24" rx="5" fill="{triceps_c}"/>'
        f'<rect x="214" y="99" width="9" height="28" rx="4" fill="#1e293b"/>'
        f'<rect x="287" y="99" width="9" height="28" rx="4" fill="#1e293b"/>'
        f'<rect x="237" y="118" width="15" height="44" rx="7" fill="{legs_b}"/>'
        f'<rect x="258" y="118" width="15" height="44" rx="7" fill="{legs_b}"/>'
        f'<rect x="238" y="165" width="13" height="34" rx="6" fill="{legs_b}"/>'
        f'<rect x="259" y="165" width="13" height="34" rx="6" fill="{legs_b}"/>'
        f'</svg>'
    )
    legend = (
        '<div style="font-size:0.76rem; color:#94a3b8; margin-top:4px;">'
        '<span style="color:#2dd4bf; font-weight:700;">■ Primär</span> &nbsp;·&nbsp;'
        '<span style="color:#a855f7; font-weight:700;">■ Sekundär / Fokus</span>'
        '</div>'
    )
    return f'<div class="anatomy-box">{svg}{legend}</div>'
        <svg viewBox="0 0 340 210" width="100%" height="205" xmlns="http://www.w3.org/2000/svg">
            <text x="85" y="18" fill="#94a3b8" font-size="11" font-weight="700" text-anchor="middle">VORDERSEITE</text>
            <circle cx="85" cy="36" r="11" fill="#334155"/>
            <rect x="78" y="47" width="14" height="7" rx="3" fill="#334155"/>
            <rect x="65" y="55" width="19" height="22" rx="6" fill="{chest_c}"/>
            <rect x="86" y="55" width="19" height="22" rx="6" fill="{chest_c}"/>
            <ellipse cx="57" cy="61" rx="8" ry="9" fill="{shoulders_f}"/>
            <ellipse cx="113" cy="61" rx="8" ry="9" fill="{shoulders_f}"/>
            <rect x="47" y="72" width="10" height="24" rx="5" fill="{biceps_c}"/>
            <rect x="113" y="72" width="10" height="24" rx="5" fill="{biceps_c}"/>
            <rect x="44" y="99" width="9" height="28" rx="4" fill="#1e293b"/>
            <rect x="117" y="99" width="9" height="28" rx="4" fill="#1e293b"/>
            <rect x="69" y="79" width="32" height="36" rx="7" fill="#1e293b"/>
            <rect x="67" y="118" width="15" height="44" rx="7" fill="{legs_f}"/>
            <rect x="88" y="118" width="15" height="44" rx="7" fill="{legs_f}"/>
            <rect x="68" y="165" width="13" height="34" rx="6" fill="{legs_f}"/>
            <rect x="89" y="165" width="13" height="34" rx="6" fill="{legs_f}"/>

            <text x="255" y="18" fill="#94a3b8" font-size="11" font-weight="700" text-anchor="middle">RÜCKSEITE</text>
            <circle cx="255" cy="36" r="11" fill="#334155"/>
            <rect x="248" y="47" width="14" height="7" rx="3" fill="#334155"/>
            <polygon points="234,55 276,55 268,108 242,108" fill="{back_c}"/>
            <ellipse cx="227" cy="61" rx="8" ry="9" fill="{shoulders_b}"/>
            <ellipse cx="283" cy="61" rx="8" ry="9" fill="{shoulders_b}"/>
            <rect x="217" y="72" width="10" height="24" rx="5" fill="{triceps_c}"/>
            <rect x="283" y="72" width="10" height="24" rx="5" fill="{triceps_c}"/>
            <rect x="214" y="99" width="9" height="28" rx="4" fill="#1e293b"/>
            <rect x="287" y="99" width="9" height="28" rx="4" fill="#1e293b"/>
            <rect x="237" y="118" width="15" height="44" rx="7" fill="{legs_b}"/>
            <rect x="258" y="118" width="15" height="44" rx="7" fill="{legs_b}"/>
            <rect x="238" y="165" width="13" height="34" rx="6" fill="{legs_b}"/>
            <rect x="259" y="165" width="13" height="34" rx="6" fill="{legs_b}"/>
        </svg>
        <div style="font-size:0.76rem; color:#94a3b8; margin-top:4px;">
            <span style="color:#2dd4bf; font-weight:700;">■ Primär</span> &nbsp;·&nbsp;
            <span style="color:#a855f7; font-weight:700;">■ Sekundär / Fokus</span>
        </div>
    </div>
    """


def add_trendline_df(session_df: pd.DataFrame) -> pd.DataFrame:
    if len(session_df) < 2:
        out = session_df.copy()
        out["trend_vol"] = out["volumen_kg"]
        return out
    ordered = session_df.sort_values("datum_dt").copy()
    x_num = np.arange(len(ordered), dtype=float)
    y_val = ordered["volumen_kg"].astype(float).to_numpy()
    slope, intercept = np.polyfit(x_num, y_val, 1)
    ordered["trend_vol"] = np.round(intercept + slope * x_num, 1)
    return ordered


# --- State Initialisierung ---
if "entries" not in st.session_state:
    st.session_state.entries = load_workouts_db()

if "session_draft" not in st.session_state:
    st.session_state.session_draft = []

if "active_view" not in st.session_state:
    st.session_state.active_view = "workout"

if "active_supps" not in st.session_state:
    st.session_state.active_supps = load_list(STACK_FILE, DEFAULT_ACTIVE_SUPPS)

if "selected_exercises" not in st.session_state:
    st.session_state.selected_exercises = load_list(EXERCISES_FILE, DEFAULT_SELECTED_EXERCISES)

if "bodyweight_logs" not in st.session_state:
    st.session_state.bodyweight_logs = load_list(WEIGHT_FILE, [])

st.markdown(APP_CSS, unsafe_allow_html=True)

today = date.today()
total_sets = len(st.session_state.entries)
total_volume = sum(float(e.get("volumen_kg", 0.0)) for e in st.session_state.entries)
trained_dates = {e.get("datum") for e in st.session_state.entries if e.get("datum")}
total_sessions = len({
    (e.get("datum"), e.get("trainingstag"))
    for e in st.session_state.entries
    if e.get("datum")
})
latest_bw_str = (
    f"{float(sorted(st.session_state.bodyweight_logs, key=lambda x: x['datum'])[-1]['gewicht_kg']):.1f} kg"
    if st.session_state.bodyweight_logs
    else "—"
)

# --- Header ---
st.markdown(
    """
    <div class="app-header">
        <div class="app-badge">PULSE · GYM, ÜBUNGEN, SUPPS &amp; WEIGHT</div>
        <h1 class="app-title">Dein persönliches Gym-Dashboard</h1>
        <p class="app-sub">Wähle gezielt einen Bereich aus, um übersichtlich zu loggen, Einheiten zu vergleichen und deine Aktivität zu prüfen.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Kompakte Kennzahlen ---
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(
        f"""
        <div class="stat-tile stat-tile-mint">
            <div class="tile-label">Einheiten</div>
            <div class="tile-number">{total_sessions}</div>
            <div class="tile-note">Geloggte Trainingstage</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with k2:
    st.markdown(
        f"""
        <div class="stat-tile stat-tile-violet">
            <div class="tile-label">Sätze / Aktive Übungen</div>
            <div class="tile-number">{total_sets} <span style="font-size:0.95rem; color:#94a3b8;">/ {len(st.session_state.selected_exercises)}</span></div>
            <div class="tile-note">Sätze gesamt · ausgewählte Übungen</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with k3:
    st.markdown(
        f"""
        <div class="stat-tile stat-tile-amber">
            <div class="tile-label">Körpergewicht</div>
            <div class="tile-number">{latest_bw_str}</div>
            <div class="tile-note">Volumen gesamt: {total_volume:,.0f} kg</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with k4:
    st.markdown(
        f"""
        <div class="stat-tile stat-tile-green">
            <div class="tile-label">Aktiver Stack</div>
            <div class="tile-number">{len(st.session_state.active_supps)}</div>
            <div class="tile-note">Ausgewählte Supplemente</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")

# --- Haupt-Auswahlkacheln (spaltet die Ansicht auf) ---
nav_items = [
    ("workout", "🏋️ Training eintragen"),
    ("analytics", "📈 Kurven & Vergleiche"),
    ("activity", "📅 Trainingsaktivität"),
    ("weight", "⚖️ Körpergewicht"),
    ("exercises", "💪 Übungen & Muskeln"),
    ("supps", "💊 Supplemente & Stack"),
]
nav_cols = st.columns(len(nav_items))
for col, (view_key, label) in zip(nav_cols, nav_items):
    is_active = st.session_state.active_view == view_key
    if col.button(
        label,
        key=f"nav_{view_key}",
        type="primary" if is_active else "secondary",
        use_container_width=True,
    ):
        st.session_state.active_view = view_key
        st.rerun()

st.divider()

view = st.session_state.active_view

# ==============================================================================
# 1. TRAINING EINTRAGEN (Ganzes Training am Stück + dynamische Sätze)
# ==============================================================================
if view == "workout":
    left_col, right_col = st.columns([1.15, 1.05], gap="large")

    with left_col:
        st.markdown('<div class="surface-card">', unsafe_allow_html=True)
        st.markdown("### 1. Trainingstag wählen & Übung hinzufügen")

        known_splits = sorted(
            set(SPLIT_PRESETS)
            | {
                e.get("trainingstag", "").strip()
                for e in st.session_state.entries
                if e.get("trainingstag", "").strip() and e.get("trainingstag", "").strip() != "Trainingstag"
            }
        )
        selectable_ex = sorted(
            set(st.session_state.selected_exercises)
            | {e.get("uebung", "").strip() for e in st.session_state.entries if e.get("uebung", "").strip()}
        )

        d_col, s_col = st.columns([1, 1.4])
        session_date = d_col.date_input("Datum", value=today, key="draft_date")
        chosen_split = s_col.selectbox(
            "Trainingstag / Split",
            known_splits + ["Eigener Name…"],
            key="draft_split_select",
        )
        if chosen_split == "Eigener Name…":
            final_split = st.text_input("Eigener Trainingstag / Split", placeholder="z. B. Push A, Schultern & Arme", key="draft_custom_split").strip() or "Trainingstag"
        else:
            final_split = chosen_split

        ex_col, set_cnt_col = st.columns([2, 1])
        pick_ex = ex_col.selectbox(
            "Übung wählen",
            selectable_ex + ["— Eigene Übung tippen —"],
            key="draft_ex_select",
        )
        num_sets = int(
            set_cnt_col.number_input(
                "Anzahl Sätze",
                min_value=1,
                max_value=8,
                value=2,
                step=1,
                key="draft_num_sets",
            )
        )

        if pick_ex == "— Eigene Übung tippen —":
            custom_ex = st.text_input("Name der eigenen Übung", placeholder="z. B. Schrägbankdrücken", key="draft_custom_ex").strip()
            exercise_name = custom_ex
        else:
            exercise_name = pick_ex

        st.markdown(f"**Sätze für diese Übung ({num_sets} Sätze – jeweils eigenes Gewicht & Wdh.):**")

        set_rows_input = []
        for s_idx in range(1, num_sets + 1):
            sc1, sc2, sc3 = st.columns([0.8, 1.2, 1.0])
            sc1.markdown(f"<div style='padding-top:30px; font-weight:700; color:#5eead4;'>Satz {s_idx}</div>", unsafe_allow_html=True)
            w_val = sc2.number_input(
                f"Gewicht Satz {s_idx} (kg)",
                min_value=0.0,
                max_value=1000.0,
                value=60.0,
                step=2.5,
                key=f"set_w_{s_idx}",
            )
            r_val = sc3.number_input(
                f"Wdh. Satz {s_idx}",
                min_value=1,
                max_value=100,
                value=10,
                step=1,
                key=f"set_r_{s_idx}",
            )
            set_rows_input.append((s_idx, float(w_val), int(r_val)))

        draft_note = st.text_input("Notiz zur Übung (optional)", placeholder="z. B. Drop-Set, RIR 1", key="draft_note").strip()

        if st.button("➕ Übung zum aktuellen Training hinzufügen", use_container_width=True):
            if not exercise_name:
                st.warning("Bitte wähle eine Übung oder gib einen Namen ein.")
            else:
                for s_idx, w_val, r_val in set_rows_input:
                    st.session_state.session_draft.append({
                        "datum": session_date.isoformat(),
                        "trainingstag": final_split,
                        "uebung": exercise_name,
                        "satz_nr": s_idx,
                        "wiederholungen": r_val,
                        "gewicht_kg": w_val,
                        "volumen_kg": round(w_val * r_val, 1),
                        "geschaetzt_1rm_kg": round(estimate_1rm(w_val, r_val), 1),
                        "notiz": draft_note,
                    })
                st.success(f"{exercise_name} ({num_sets} Sätze) zum Training hinzugefügt.")
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    with right_col:
        st.markdown('<div class="surface-card">', unsafe_allow_html=True)
        st.markdown("### 2. Aktuelles Training (Sammelkorb)")

        draft = st.session_state.session_draft
        if not draft:
            st.info("Noch keine Übungen im aktuellen Training. Füge links Übungen hinzu – du kannst mehrere nacheinander sammeln und dann gesammelt speichern.")
        else:
            draft_df = pd.DataFrame(draft)
            draft_vol = float(draft_df["volumen_kg"].sum())
            st.markdown(
                f"**{draft[0]['datum']} · {draft[0]['trainingstag']}** — {len(draft)} Sätze · **{draft_vol:,.1f} kg** Gesamtvolumen"
            )

            for ex_name, grp in draft_df.groupby("uebung", sort=False):
                parts = [f"S{int(r['satz_nr'])}: {float(r['gewicht_kg']):g} kg × {int(r['wiederholungen'])}" for _, r in grp.iterrows()]
                note_txt = f" · _{grp.iloc[0]['notiz']}_" if grp.iloc[0].get("notiz") else ""
                st.markdown(
                    f"""
                    <div class="draft-item">
                        <div style="font-weight:700; color:#ffffff;">{ex_name}{note_txt}</div>
                        <div style="font-size:0.85rem; color:#94a3b8; margin-top:3px;">{" | ".join(parts)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            b1, b2 = st.columns([2, 1])
            if b1.button("💾 Ganzes Training speichern", type="primary", use_container_width=True):
                for item in draft:
                    save_workout_db(
                        item["datum"],
                        item["uebung"],
                        item["gewicht_kg"],
                        item["wiederholungen"],
                    )
                    st.session_state.entries.append({
                        "id": len(st.session_state.entries) + 1,
                        **item,
                        "saetze": 1,
                    })
                save_json(DATA_FILE, st.session_state.entries)
                st.session_state["focus_exercise"] = draft[-1]["uebung"]
                st.session_state.session_draft = []
                st.success("Training komplett in Supabase gespeichert!")
                st.rerun()

            if b2.button("Verwerfen", use_container_width=True):
                st.session_state.session_draft = []
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


# ==============================================================================
# 2. KURVEN & VERGLEICHE (Trainingstage vergleichen, Übung, Split-Trendlinien)
# ==============================================================================
elif view == "analytics":
    if not st.session_state.entries:
        st.info("Es sind noch keine Trainingssätze vorhanden. Lege zuerst unter **Training eintragen** Sätze an.")
    else:
        df = pd.DataFrame(st.session_state.entries)
        df["datum_dt"] = pd.to_datetime(df["datum"])
        df["session_label"] = df["datum"].astype(str) + " (" + df["trainingstag"].astype(str) + ")"

        sub_mode = st.radio(
            "Ansicht wählen",
            [
                "Gesamtübersicht: Splits & Ausgleichslinie",
                "Trainingstag mit vorherigem vergleichen",
                "Einzelne Übung im Detail",
            ],
            horizontal=True,
        )

        # --- A: Gesamtübersicht aller Splits/Trainingstage mit Ausgleichslinie ---
        if sub_mode == "Gesamtübersicht: Splits & Ausgleichslinie":
            st.markdown('<div class="surface-card">', unsafe_allow_html=True)
            st.markdown("### Verlaufskurven der einzelnen Trainingstage / Splits + Ausgleichslinie")

            session_summary = (
                df.groupby(["datum", "datum_dt", "trainingstag", "session_label"], as_index=False)
                .agg(
                    volumen_kg=("volumen_kg", "sum"),
                    saetze=("uebung", "count"),
                    max_gewicht_kg=("gewicht_kg", "max"),
                )
                .sort_values("datum_dt")
            )

            available_splits = sorted(session_summary["trainingstag"].unique())
            chosen_splits = st.multiselect(
                "Splits / Trainingstage einblenden (jeweils eigene Farbe)",
                available_splits,
                default=available_splits,
            )

            filtered_sessions = session_summary[session_summary["trainingstag"].isin(chosen_splits)].copy()
            if filtered_sessions.empty:
                st.warning("Bitte mindestens einen Split auswählen.")
            else:
                metric_choice = st.selectbox(
                    "Kennzahl für die Kurven",
                    ["volumen_kg", "saetze", "max_gewicht_kg"],
                    format_func=lambda k: {
                        "volumen_kg": "Gesamtvolumen pro Einheit (kg)",
                        "saetze": "Anzahl Sätze pro Einheit",
                        "max_gewicht_kg": "Höchstes Gewicht der Einheit (kg)",
                    }[k],
                )
                filtered_sessions["wert"] = filtered_sessions[metric_choice]

                # Ausgleichslinie über den zeitlichen Verlauf
                trend_df = add_trendline_df(filtered_sessions.assign(volumen_kg=filtered_sessions["wert"]))

                split_lines = (
                    alt.Chart(filtered_sessions)
                    .mark_line(point=alt.OverlayMarkDef(size=70), strokeWidth=3)
                    .encode(
                        x=alt.X("datum_dt:T", title="Datum"),
                        y=alt.Y("wert:Q", title="Wert", scale=alt.Scale(zero=False)),
                        color=alt.Color("trainingstag:N", title="Trainingstag / Split"),
                        tooltip=[
                            alt.Tooltip("datum:N", title="Datum"),
                            alt.Tooltip("trainingstag:N", title="Split"),
                            alt.Tooltip("wert:Q", title="Wert"),
                            alt.Tooltip("saetze:Q", title="Sätze"),
                        ],
                    )
                )

                trend_line = (
                    alt.Chart(trend_df)
                    .mark_line(strokeDash=[6, 4], strokeWidth=2.5, color="#f59e0b")
                    .encode(
                        x=alt.X("datum_dt:T"),
                        y=alt.Y("trend_vol:Q"),
                        tooltip=[alt.Tooltip("trend_vol:Q", title="Ausgleichslinie")],
                    )
                )

                chart_all = (
                    (split_lines + trend_line)
                    .properties(height=340)
                    .configure_view(strokeOpacity=0)
                    .configure_axis(
                        gridColor="rgba(148,163,184,0.12)",
                        labelColor="#94a3b8",
                        titleColor="#cbd5e1",
                    )
                )
                st.altair_chart(chart_all, use_container_width=True)
                st.caption("Gestrichelte gelbe Linie = lineare Ausgleichslinie (Gesamttrend über die ausgewählten Einheiten).")

            st.markdown("</div>", unsafe_allow_html=True)

        # --- B: Einzelnen Trainingstag direkt mit dem davor vergleichen ---
        elif sub_mode == "Trainingstag mit vorherigem vergleichen":
            st.markdown('<div class="surface-card">', unsafe_allow_html=True)
            st.markdown("### Trainingstag einzeln mit dem vorherigen Trainingstag vergleichen")

            sessions_ordered = (
                df.groupby(["datum", "datum_dt", "trainingstag", "session_label"], as_index=False)
                .agg(
                    volumen_kg=("volumen_kg", "sum"),
                    saetze=("uebung", "count"),
                    wdh_gesamt=("wiederholungen", "sum"),
                    max_gewicht_kg=("gewicht_kg", "max"),
                )
                .sort_values("datum_dt")
                .reset_index(drop=True)
            )

            labels = sessions_ordered["session_label"].tolist()
            selected_label = st.selectbox("Trainingstag auswählen", labels, index=len(labels) - 1)
            idx_curr = labels.index(selected_label)
            curr_row = sessions_ordered.iloc[idx_curr]

            if idx_curr == 0:
                st.info("Das ist dein ältester geloggter Trainingstag – es gibt noch keinen vorherigen Tag zum Vergleichen.")
            else:
                prev_row = sessions_ordered.iloc[idx_curr - 1]
                vol_diff = float(curr_row["volumen_kg"]) - float(prev_row["volumen_kg"])
                sets_diff = int(curr_row["saetze"]) - int(prev_row["saetze"])
                reps_diff = int(curr_row["wdh_gesamt"]) - int(prev_row["wdh_gesamt"])
                top_diff = float(curr_row["max_gewicht_kg"]) - float(prev_row["max_gewicht_kg"])

                st.caption(f"Vergleich: **{curr_row['session_label']}** vs. vorheriger Tag **{prev_row['session_label']}**")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Volumen", f"{curr_row['volumen_kg']:,.1f} kg", f"{vol_diff:+,.1f} kg")
                m2.metric("Sätze", f"{int(curr_row['saetze'])}", f"{sets_diff:+d}")
                m3.metric("Wdh. gesamt", f"{int(curr_row['wdh_gesamt'])}", f"{reps_diff:+d}")
                m4.metric("Top-Gewicht", f"{curr_row['max_gewicht_kg']:g} kg", f"{top_diff:+g} kg")

                curr_ex = (
                    df[(df["datum"] == curr_row["datum"]) & (df["trainingstag"] == curr_row["trainingstag"])]
                    .groupby("uebung", as_index=False)
                    .agg(
                        saetze_neu=("uebung", "count"),
                        vol_neu=("volumen_kg", "sum"),
                        max_kg_neu=("gewicht_kg", "max"),
                    )
                )
                prev_ex = (
                    df[(df["datum"] == prev_row["datum"]) & (df["trainingstag"] == prev_row["trainingstag"])]
                    .groupby("uebung", as_index=False)
                    .agg(
                        saetze_vorher=("uebung", "count"),
                        vol_vorher=("volumen_kg", "sum"),
                        max_kg_vorher=("gewicht_kg", "max"),
                    )
                )
                comp_ex = pd.merge(curr_ex, prev_ex, on="uebung", how="outer").fillna(0)
                comp_ex["Volumen_Diff_kg"] = (comp_ex["vol_neu"] - comp_ex["vol_vorher"]).round(1)
                comp_ex["Max_Kg_Diff"] = (comp_ex["max_kg_neu"] - comp_ex["max_kg_vorher"]).round(1)
                st.dataframe(comp_ex, use_container_width=True, hide_index=True)

            st.markdown("</div>", unsafe_allow_html=True)

        # --- C: Gesonderte Entwicklung einer einzelnen Übung ---
        else:
            st.markdown('<div class="surface-card">', unsafe_allow_html=True)
            st.markdown("### Entwicklung einer einzelnen Übung")

            exercises = sorted(df["uebung"].dropna().unique())
            default_pos = 0
            if "focus_exercise" in st.session_state and st.session_state["focus_exercise"] in exercises:
                default_pos = exercises.index(st.session_state["focus_exercise"])

            selected_exercise = st.selectbox("Übung auswählen", exercises, index=default_pos)
            ex_df = df[df["uebung"] == selected_exercise].sort_values("datum_dt")

            line = (
                alt.Chart(ex_df)
                .mark_line(point=alt.OverlayMarkDef(color="#2dd4bf", size=70), color="#2dd4bf", strokeWidth=3)
                .encode(
                    x=alt.X("datum_dt:T", title="Datum"),
                    y=alt.Y("gewicht_kg:Q", title="Gewicht (kg)", scale=alt.Scale(zero=False)),
                    tooltip=[
                        alt.Tooltip("datum:N", title="Datum"),
                        alt.Tooltip("trainingstag:N", title="Split"),
                        alt.Tooltip("satz_nr:Q", title="Satz"),
                        alt.Tooltip("gewicht_kg:Q", title="Gewicht (kg)"),
                        alt.Tooltip("wiederholungen:Q", title="Wdh."),
                    ],
                )
                .properties(height=280)
                .configure_view(strokeOpacity=0)
                .configure_axis(
                    gridColor="rgba(148,163,184,0.12)",
                    labelColor="#94a3b8",
                    titleColor="#cbd5e1",
                )
            )
            st.altair_chart(line, use_container_width=True)

            first_kg = float(ex_df["gewicht_kg"].iloc[0])
            last_kg = float(ex_df["gewicht_kg"].iloc[-1])
            best_kg = float(ex_df["gewicht_kg"].max())
            best_1rm = max(
                estimate_1rm(float(r["gewicht_kg"]), int(r["wiederholungen"]))
                for _, r in ex_df.iterrows()
            )
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Startgewicht", f"{first_kg:g} kg")
            c2.metric("Aktuell", f"{last_kg:g} kg", f"{last_kg - first_kg:+g} kg")
            c3.metric("Bestleistung", f"{best_kg:g} kg")
            c4.metric("Geschätztes 1RM", f"{best_1rm:.1f} kg")

            st.dataframe(
                ex_df[["datum", "trainingstag", "satz_nr", "gewicht_kg", "wiederholungen", "volumen_kg", "notiz"]],
                use_container_width=True,
                hide_index=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)


# ==============================================================================
# 3. TRAININGSFAKTIVITÄT (Wann und wie oft trainiert)
# ==============================================================================
elif view == "activity":
    st.markdown('<div class="surface-card">', unsafe_allow_html=True)
    st.markdown("### Trainingsaktivität – wann und wie oft du trainiert hast")

    monday = today - timedelta(days=today.weekday())
    day_labels = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    pills_html = ['<div class="tile-label">Aktuelle Woche</div><div class="week-row">']
    for offset, label in enumerate(day_labels):
        d = monday + timedelta(days=offset)
        is_done = d.isoformat() in trained_dates
        is_today = d == today
        cls = "day-pill"
        if is_done:
            cls += " day-pill-done"
        if is_today:
            cls += " day-pill-today"
        symbol = "✓" if is_done else str(d.day)
        pills_html.append(
            f'<div class="{cls}"><div class="day-name">{label} {d.day}.</div><div class="day-circle">{symbol}</div></div>'
        )
    pills_html.append("</div>")
    st.markdown("".join(pills_html), unsafe_allow_html=True)

    st.write("")
    if not st.session_state.entries:
        st.info("Noch keine Trainingstage erfasst.")
    else:
        df = pd.DataFrame(st.session_state.entries)
        df["datum_dt"] = pd.to_datetime(df["datum"])

        last_30_cutoff = pd.Timestamp(today - timedelta(days=30))
        last_7_cutoff = pd.Timestamp(today - timedelta(days=7))
        days_30 = df[df["datum_dt"] >= last_30_cutoff]["datum"].nunique()
        days_7 = df[df["datum_dt"] >= last_7_cutoff]["datum"].nunique()
        days_total = df["datum"].nunique()

        a1, a2, a3 = st.columns(3)
        a1.metric("Trainingstage (letzte 7 Tage)", f"{days_7} Tage")
        a2.metric("Trainingstage (letzte 30 Tage)", f"{days_30} Tage")
        a3.metric("Trainingstage gesamt", f"{days_total} Tage")

        week_counts = (
            df.assign(woche=df["datum_dt"].dt.to_period("W").dt.start_time)
            .groupby("woche", as_index=False)
            .agg(trainingstage=("datum", "nunique"), saetze=("uebung", "count"))
            .sort_values("woche")
        )
        bar_act = (
            alt.Chart(week_counts)
            .mark_bar(color="#2dd4bf", cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
            .encode(
                x=alt.X("woche:T", title="Wochenstart"),
                y=alt.Y("trainingstage:Q", title="Trainingstage / Woche", axis=alt.Axis(tickMinStep=1)),
                tooltip=[
                    alt.Tooltip("woche:T", title="Woche ab"),
                    alt.Tooltip("trainingstage:Q", title="Trainingstage"),
                    alt.Tooltip("saetze:Q", title="Sätze"),
                ],
            )
            .properties(height=240)
            .configure_view(strokeOpacity=0)
            .configure_axis(
                gridColor="rgba(148,163,184,0.12)",
                labelColor="#94a3b8",
                titleColor="#cbd5e1",
            )
        )
        st.altair_chart(bar_act, use_container_width=True)

        log_days = (
            df.groupby(["datum", "trainingstag"], as_index=False)
            .agg(
                uebungen=("uebung", "nunique"),
                saetze=("uebung", "count"),
                volumen_kg=("volumen_kg", "sum"),
            )
            .sort_values("datum", ascending=False)
        )
        st.dataframe(log_days, use_container_width=True, hide_index=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ==============================================================================
# 4. KÖRPERGEWICHT & VERLAUF
# ==============================================================================
elif view == "weight":
    st.markdown('<div class="surface-card">', unsafe_allow_html=True)
    st.markdown("### Körpergewicht erfassen & Verlauf ansehen")

    with st.form("bw_form", clear_on_submit=True):
        bc1, bc2, bc3 = st.columns([1.2, 1.2, 1.0])
        bw_date = bc1.date_input("Datum", value=today)
        bw_kg = bc2.number_input("Gewicht (kg)", min_value=20.0, max_value=350.0, value=73.0, step=0.1)
        bw_submit = bc3.form_submit_button("Gewicht speichern", use_container_width=True)
        if bw_submit:
            st.session_state.bodyweight_logs.append({"datum": bw_date.isoformat(), "gewicht_kg": float(bw_kg)})
            st.session_state.bodyweight_logs.sort(key=lambda x: x["datum"])
            save_json(WEIGHT_FILE, st.session_state.bodyweight_logs)
            st.success("Körpergewicht gespeichert.")
            st.rerun()

    if st.session_state.bodyweight_logs:
        bw_df = pd.DataFrame(st.session_state.bodyweight_logs)
        bw_df["datum_dt"] = pd.to_datetime(bw_df["datum"])
        bw_chart = (
            alt.Chart(bw_df)
            .mark_line(point=alt.OverlayMarkDef(color="#f59e0b", size=65), color="#f59e0b", strokeWidth=3)
            .encode(
                x=alt.X("datum_dt:T", title="Datum"),
                y=alt.Y("gewicht_kg:Q", title="Körpergewicht (kg)", scale=alt.Scale(zero=False)),
                tooltip=[alt.Tooltip("datum:N", title="Datum"), alt.Tooltip("gewicht_kg:Q", title="kg")],
            )
            .properties(height=250)
            .configure_view(strokeOpacity=0)
            .configure_axis(
                gridColor="rgba(148,163,184,0.12)",
                labelColor="#94a3b8",
                titleColor="#cbd5e1",
            )
        )
        st.altair_chart(bw_chart, use_container_width=True)
        st.dataframe(bw_df[["datum", "gewicht_kg"]].sort_values("datum", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("Noch keine Gewichtseinträge vorhanden.")

    st.markdown("</div>", unsafe_allow_html=True)


# ==============================================================================
# 5. ÜBUNGEN & MUSKELGRUPPEN
# ==============================================================================
elif view == "exercises":
    st.markdown('<div class="surface-card">', unsafe_allow_html=True)
    st.markdown("### Übungen & Muskelgruppen")

    mg_names = list(MUSCLE_GROUPS.keys())
    picked_mg = st.selectbox("Muskelgruppe wählen", mg_names)
    mg_info = MUSCLE_GROUPS[picked_mg]

    m_left, m_right = st.columns([1.25, 1.0], gap="large")
    with m_left:
        st.markdown(f"**Primär:** {mg_info['primaer']}")
        st.markdown(f"**Sekundär:** {mg_info['sekundaer']}")
        st.write("")
        for ex in mg_info["exercises"]:
            is_sel = ex in st.session_state.selected_exercises
            checked = st.checkbox(ex, value=is_sel, key=f"ex_chk_{picked_mg}_{ex}")
            if checked and not is_sel:
                st.session_state.selected_exercises.append(ex)
                save_json(EXERCISES_FILE, st.session_state.selected_exercises)
            elif not checked and is_sel:
                st.session_state.selected_exercises.remove(ex)
                save_json(EXERCISES_FILE, st.session_state.selected_exercises)

    with m_right:
        st.markdown(render_muscle_svg(mg_info["highlight"]), unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ==============================================================================
# 6. SUPPLEMENTE & STACK
# ==============================================================================
elif view == "supps":
    st.markdown('<div class="surface-card">', unsafe_allow_html=True)
    st.markdown("### Supplemente & dein aktiver Stack")

    for supp in SUPPLEMENTS_CATALOG:
        name = supp["name"]
        is_active = name in st.session_state.active_supps
        card_cls = "supp-card supp-card-active" if is_active else "supp-card"
        badge_mine = '<span class="badge-mine">Im Stack</span>' if is_active else ""

        st.markdown(
            f"""
            <div class="{card_cls}">
                <span class="badge-cat">{supp["kategorie"]}</span>{badge_mine}
                <div class="supp-heading">{name}</div>
                <div style="font-size:0.88rem; color:#e2e8f0;">{supp["wirkung"]}</div>
                <div class="supp-detail">
                    <strong>Einnahme:</strong> {supp["einnahme"]}<br>
                    <strong>Tipp:</strong> {supp["tipp"]}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        toggle_val = st.checkbox(
            "In meinem Stack aktiv",
            value=is_active,
            key=f"supp_chk_{name}",
        )
        if toggle_val and not is_active:
            st.session_state.active_supps.append(name)
            save_json(STACK_FILE, st.session_state.active_supps)
            st.rerun()
        elif not toggle_val and is_active:
            st.session_state.active_supps.remove(name)
            save_json(STACK_FILE, st.session_state.active_supps)
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
