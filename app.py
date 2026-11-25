import json
from datetime import date, timedelta
from pathlib import Path
import altair as alt
import pandas as pd
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
import psycopg

def load_workouts_db():
    cfg = st.secrets["postgres"]
    conn = psycopg.connect(
        host=cfg["host"],
        port=int(cfg["port"]),
        dbname=cfg["dbname"],
        user=cfg["user"],
        password=cfg["password"],
        sslmode="require",
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT datum, uebung, gewicht, wiederholungen FROM workouts ORDER BY id ASC")
            rows = cur.fetchall()
        return [
            {
                "datum": r[0],
                "trainingstag": "Trainingstag",
                "uebung": r[1],
                "saetze": 1,
                "wiederholungen": int(r[3]),
                "gewicht_kg": float(r[2]),
                "volumen_kg": float(r[2]) * int(r[3]),
                "geschaetzt_1rm_kg": round(estimate_1rm(float(r[2]), int(r[3])), 1),
                "notiz": "",
            }
            for r in rows
        ]
    finally:
        conn.close()

def save_workout_db(datum_str, uebung_str, gewicht_val, wdh_val):
    cfg = st.secrets["postgres"]
    conn = psycopg.connect(
        host=cfg["host"],
        port=int(cfg["port"]),
        dbname=cfg["dbname"],
        user=cfg["user"],
        password=cfg["password"],
        sslmode="require",
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO workouts (datum, uebung, gewicht, wiederholungen) VALUES (%s, %s, %s, %s)",
                (datum_str, uebung_str, float(gewicht_val), int(wdh_val)),
            )
        conn.commit()
    finally:
        conn.close()
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
        padding-top: 1.35rem;
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

    return f"""
    <div class="anatomy-box">
        <svg viewBox="0 0 340 210" width="100%" height="205" xmlns="http://www.w3.org/2000/svg">
            <!-- Vorderansicht (Front) -->
            <text x="85" y="18" fill="#94a3b8" font-size="11" font-weight="700" text-anchor="middle">VORDERSEITE</text>
            <circle cx="85" cy="36" r="11" fill="#334155"/>
            <rect x="78" y="47" width="14" height="7" rx="3" fill="#334155"/>
            <!-- Brust -->
            <rect x="65" y="55" width="19" height="22" rx="6" fill="{chest_c}"/>
            <rect x="86" y="55" width="19" height="22" rx="6" fill="{chest_c}"/>
            <!-- Schultern vorn -->
            <ellipse cx="57" cy="61" rx="8" ry="9" fill="{shoulders_f}"/>
            <ellipse cx="113" cy="61" rx="8" ry="9" fill="{shoulders_f}"/>
            <!-- Bizeps vorn -->
            <rect x="47" y="72" width="10" height="24" rx="5" fill="{biceps_c}"/>
            <rect x="113" y="72" width="10" height="24" rx="5" fill="{biceps_c}"/>
            <rect x="44" y="99" width="9" height="28" rx="4" fill="#1e293b"/>
            <rect x="117" y="99" width="9" height="28" rx="4" fill="#1e293b"/>
            <!-- Rumpf -->
            <rect x="69" y="79" width="32" height="36" rx="7" fill="#1e293b"/>
            <!-- Beine vorn -->
            <rect x="67" y="118" width="15" height="44" rx="7" fill="{legs_f}"/>
            <rect x="88" y="118" width="15" height="44" rx="7" fill="{legs_f}"/>
            <rect x="68" y="165" width="13" height="34" rx="6" fill="{legs_f}"/>
            <rect x="89" y="165" width="13" height="34" rx="6" fill="{legs_f}"/>

            <!-- Rückansicht (Back) -->
            <text x="255" y="18" fill="#94a3b8" font-size="11" font-weight="700" text-anchor="middle">RÜCKSEITE</text>
            <circle cx="255" cy="36" r="11" fill="#334155"/>
            <rect x="248" y="47" width="14" height="7" rx="3" fill="#334155"/>
            <!-- Rücken / Lat -->
            <polygon points="234,55 276,55 268,108 242,108" fill="{back_c}"/>
            <!-- Schultern hinten -->
            <ellipse cx="227" cy="61" rx="8" ry="9" fill="{shoulders_b}"/>
            <ellipse cx="283" cy="61" rx="8" ry="9" fill="{shoulders_b}"/>
            <!-- Trizeps hinten -->
            <rect x="217" y="72" width="10" height="24" rx="5" fill="{triceps_c}"/>
            <rect x="283" y="72" width="10" height="24" rx="5" fill="{triceps_c}"/>
            <rect x="214" y="99" width="9" height="28" rx="4" fill="#1e293b"/>
            <rect x="287" y="99" width="9" height="28" rx="4" fill="#1e293b"/>
            <!-- Beine / Glutes / Waden hinten -->
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


if "entries" not in st.session_state:
    st.session_state.entries = load_workouts_db()

if "active_supps" not in st.session_state:
    st.session_state.active_supps = load_list(STACK_FILE, DEFAULT_ACTIVE_SUPPS)

if "selected_exercises" not in st.session_state:
    st.session_state.selected_exercises = load_list(EXERCISES_FILE, DEFAULT_SELECTED_EXERCISES)

if "bodyweight_logs" not in st.session_state:
    st.session_state.bodyweight_logs = load_list(WEIGHT_FILE, [])

st.markdown(APP_CSS, unsafe_allow_html=True)

total_sets = sum(int(e.get("saetze", 0)) for e in st.session_state.entries)
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

st.markdown(
    """
    <div class="app-header">
        <div class="app-badge">PULSE · WORKOUT, ÜBUNGEN, SUPPS &amp; WEIGHT</div>
        <h1 class="app-title">Dein persönliches Gym-Dashboard</h1>
        <p class="app-sub">Sätze loggen, Kurven direkt nebenan verfolgen, Übungen &amp; Supplemente an-/abwählen und Körpergewicht auswerten.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

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

today = date.today()
monday = today - timedelta(days=today.weekday())
day_labels = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
pills_html = ['<div class="surface-card"><div class="tile-label">Aktuelle Woche · Trainingsaktivität</div><div class="week-row">']
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
pills_html.append("</div></div>")
st.markdown("".join(pills_html), unsafe_allow_html=True)

tab_live, tab_exercises, tab_weight, tab_history, tab_supps = st.tabs([
    "Sätze & Live-Statistik",
    "Übungen & Muskelgruppen",
    "Körpergewicht",
    "Verlauf & Einträge",
    "Supplemente & Stack",
])

with tab_live:
    col_entry, col_chart = st.columns([1.02, 1.38], gap="large")

    with col_entry:
        st.markdown("### Neuen Satz eintragen")
        known_days = sorted({
            e.get("trainingstag", "").strip()
            for e in st.session_state.entries
            if e.get("trainingstag", "").strip()
        })
        selectable_ex = sorted(set(st.session_state.selected_exercises) | {
            e.get("uebung", "").strip()
            for e in st.session_state.entries
            if e.get("uebung", "").strip()
        })

        with st.form("gym_set_form", clear_on_submit=True):
            entry_date = st.date_input("Datum", value=today)

            if known_days:
                pick_day = st.selectbox(
                    "Trainingstag wählen",
                    ["— Neu eingeben —"] + known_days,
                )
            else:
                pick_day = "— Neu eingeben —"

            custom_day = st.text_input(
                "Trainingstag / Split",
                placeholder="z. B. Push, Pull, Leg Day, Oberkörper",
            )

            if selectable_ex:
                pick_ex = st.selectbox(
                    "Übung wählen (aus deinen aktiven Übungen)",
                    ["— Eigene Übung tippen —"] + selectable_ex,
                )
            else:
                pick_ex = "— Eigene Übung tippen —"

            custom_ex = st.text_input(
                "Eigene Übung (falls nicht in Liste)",
                placeholder="z. B. Bankdrücken, Schrägbank, Klimmzüge",
            )

            c1, c2, c3 = st.columns(3)
            sets_val = c1.number_input("Sätze", min_value=1, max_value=30, value=3, step=1)
            reps_val = c2.number_input("Wdh.", min_value=1, max_value=100, value=10, step=1)
            weight_val = c3.number_input(
                "Gewicht (kg)", min_value=0.0, max_value=1000.0, value=60.0, step=2.5
            )

            note_val = st.text_input(
                "Notiz (optional)", placeholder="z. B. RIR 1, sauberer Satz"
            )

            submit_set = st.form_submit_button("Satz speichern", use_container_width=True)
            if submit_set:
                final_day = (
                    custom_day.strip()
                    or ("" if pick_day == "— Neu eingeben —" else pick_day)
                    or "Trainingstag"
                )
                final_ex = (
                    custom_ex.strip()
                    or ("" if pick_ex == "— Eigene Übung tippen —" else pick_ex)
                )

                if not final_ex:
                    st.warning("Bitte wähle eine Übung oder gib einen Namen ein.")
                else:
                    vol = round(int(sets_val) * int(reps_val) * float(weight_val), 1)
                    e1rm = round(estimate_1rm(float(weight_val), int(reps_val)), 1)
                    st.session_state.entries.append({
                        "datum": entry_date.isoformat(),
                        "trainingstag": final_day,
                        "uebung": final_ex,
                        "saetze": int(sets_val),
                        "wiederholungen": int(reps_val),
                        "gewicht_kg": float(weight_val),
                        "volumen_kg": vol,
                        "geschaetzt_1rm_kg": e1rm,
                        "notiz": note_val.strip(),
                    })
                    save_json(DATA_FILE, st.session_state.entries)
                    save_workout_db(entry_date.isoformat(), final_ex, weight_val, reps_val)
                    st.session_state["focus_exercise"] = final_ex
                    st.success(f"Gespeichert: {final_ex} ({weight_val} kg × {reps_val})")
                    st.rerun()

    with col_chart:
        st.markdown('<div class="surface-card">', unsafe_allow_html=True)
        st.markdown("### Direkte Statistik")
        if st.session_state.entries:
            df = pd.DataFrame(st.session_state.entries)
            df["datum_dt"] = pd.to_datetime(df["datum"])
            exercises = sorted(df["uebung"].dropna().unique())

            default_pos = 0
            if "focus_exercise" in st.session_state and st.session_state["focus_exercise"] in exercises:
                default_pos = exercises.index(st.session_state["focus_exercise"])

            selected_exercise = st.selectbox(
                "Übung für Kurve auswählen",
                exercises,
                index=default_pos,
                key="live_curve_ex",
            )
            ex_df = df[df["uebung"] == selected_exercise].sort_values("datum_dt")

            line = (
                alt.Chart(ex_df)
                .mark_line(point=alt.OverlayMarkDef(color="#2dd4bf", size=65), color="#2dd4bf", strokeWidth=3)
                .encode(
                    x=alt.X("datum_dt:T", title="Datum"),
                    y=alt.Y("gewicht_kg:Q", title="Gewicht (kg)", scale=alt.Scale(zero=False)),
                    tooltip=[
                        alt.Tooltip("datum:N", title="Datum"),
                        alt.Tooltip("trainingstag:N", title="Tag"),
                        alt.Tooltip("gewicht_kg:Q", title="Gewicht (kg)"),
                        alt.Tooltip("saetze:Q", title="Sätze"),
                        alt.Tooltip("wiederholungen:Q", title="Wdh."),
                    ],
                )
                .properties(height=255)
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

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Start", f"{first_kg:.1f} kg")
            m2.metric("Aktuell", f"{last_kg:.1f} kg", delta=f"{last_kg - first_kg:+.1f} kg")
            m3.metric("Bestwert (PR)", f"{best_kg:.1f} kg")
            m4.metric("Est. 1RM", f"{best_1rm:.1f} kg")
        else:
            st.info(
                "Trag links deinen ersten Satz ein – rechts erscheint sofort deine Verlaufskurve, dein PR und dein geschätztes 1RM."
            )
        st.markdown("</div>", unsafe_allow_html=True)

with tab_exercises:
    st.markdown('<div class="surface-card">', unsafe_allow_html=True)
    st.markdown("### Standard-Übungen nach Muskelgruppe & Muskelansprache")
    st.caption(
        "Je 10 Standard-Übungen für Brust, Rücken, Beine, Bizeps, Trizeps und Schultern – inklusive Muskelübersicht und An-/Abwahl für deinen Trainingspool."
    )

    group_names = list(MUSCLE_GROUPS.keys())
    chosen_group = st.selectbox("Muskelgruppe wählen", group_names)
    group_info = MUSCLE_GROUPS[chosen_group]

    col_vis, col_list = st.columns([1.05, 1.45], gap="large")
    with col_vis:
        st.markdown(render_muscle_svg(group_info["highlight"]), unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="supp-detail">
                <strong>Primäre Muskeln:</strong> {group_info["primaer"]}<br>
                <strong>Sekundäre Beteiligung:</strong> {group_info["sekundaer"]}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_list:
        st.markdown(f"#### 10 Standard-Übungen · {chosen_group}")
        b_col1, b_col2 = st.columns(2)
        if b_col1.button("Alle 10 der Gruppe aktivieren", key=f"all_{chosen_group}"):
            updated = set(st.session_state.selected_exercises)
            updated.update(group_info["exercises"])
            st.session_state.selected_exercises = sorted(updated)
            save_json(EXERCISES_FILE, st.session_state.selected_exercises)
            st.rerun()
        if b_col2.button("Alle 10 der Gruppe abwählen", key=f"none_{chosen_group}"):
            updated = [ex for ex in st.session_state.selected_exercises if ex not in group_info["exercises"]]
            st.session_state.selected_exercises = updated
            save_json(EXERCISES_FILE, st.session_state.selected_exercises)
            st.rerun()

        changed_ex = False
        current_set = set(st.session_state.selected_exercises)
        for idx, ex_name in enumerate(group_info["exercises"]):
            is_checked = ex_name in current_set
            new_checked = st.checkbox(
                f"{idx + 1}. {ex_name}",
                value=is_checked,
                key=f"cb_ex_{chosen_group}_{idx}_{ex_name}",
            )
            if new_checked and not is_checked:
                current_set.add(ex_name)
                changed_ex = True
            elif not new_checked and is_checked:
                current_set.discard(ex_name)
                changed_ex = True

        if changed_ex:
            st.session_state.selected_exercises = sorted(current_set)
            save_json(EXERCISES_FILE, st.session_state.selected_exercises)
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

with tab_weight:
    col_w_form, col_w_stats = st.columns([1.0, 1.45], gap="large")

    with col_w_form:
        st.markdown("### Körpergewicht eintragen")
        with st.form("bodyweight_form", clear_on_submit=True):
            bw_date = st.date_input("Datum", value=today, key="bw_date_input")
            bw_rhythm = st.radio(
                "Eintragsrhythmus",
                ["Täglich", "Wöchentlich"],
                horizontal=True,
            )
            bw_kg = st.number_input(
                "Körpergewicht (kg)",
                min_value=25.0,
                max_value=300.0,
                value=75.0,
                step=0.1,
                format="%.1f",
            )
            bw_note = st.text_input(
                "Notiz (optional)",
                placeholder="z. B. morgens nüchtern, nach Wochenend-Essen",
            )
            bw_save = st.form_submit_button("Gewicht speichern", use_container_width=True)
            if bw_save:
                st.session_state.bodyweight_logs.append({
                    "datum": bw_date.isoformat(),
                    "rhythmus": bw_rhythm,
                    "gewicht_kg": round(float(bw_kg), 1),
                    "notiz": bw_note.strip(),
                })
                save_json(WEIGHT_FILE, st.session_state.bodyweight_logs)
                st.success(f"Körpergewicht gespeichert: {bw_kg:.1f} kg ({bw_rhythm})")
                st.rerun()

    with col_w_stats:
        st.markdown('<div class="surface-card">', unsafe_allow_html=True)
        st.markdown("### Statistik zur Körpergewichts-Veränderung")
        if st.session_state.bodyweight_logs:
            bw_df = pd.DataFrame(st.session_state.bodyweight_logs)
            bw_df["datum_dt"] = pd.to_datetime(bw_df["datum"])
            bw_df = bw_df.sort_values("datum_dt")

            rhythm_filter = st.radio(
                "Messungen anzeigen",
                ["Alle Einträge", "Nur Täglich", "Nur Wöchentlich"],
                horizontal=True,
                key="bw_filter_radio",
            )
            view_bw = bw_df.copy()
            if rhythm_filter == "Nur Täglich":
                view_bw = view_bw[view_bw["rhythmus"] == "Täglich"]
            elif rhythm_filter == "Nur Wöchentlich":
                view_bw = view_bw[view_bw["rhythmus"] == "Wöchentlich"]

            if not view_bw.empty:
                bw_chart = (
                    alt.Chart(view_bw)
                    .mark_line(point=alt.OverlayMarkDef(color="#a855f7", size=65), color="#a855f7", strokeWidth=3)
                    .encode(
                        x=alt.X("datum_dt:T", title="Datum"),
                        y=alt.Y("gewicht_kg:Q", title="Körpergewicht (kg)", scale=alt.Scale(zero=False)),
                        tooltip=[
                            alt.Tooltip("datum:N", title="Datum"),
                            alt.Tooltip("rhythmus:N", title="Rhythmus"),
                            alt.Tooltip("gewicht_kg:Q", title="Gewicht (kg)"),
                            alt.Tooltip("notiz:N", title="Notiz"),
                        ],
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

                start_bw = float(view_bw["gewicht_kg"].iloc[0])
                curr_bw = float(view_bw["gewicht_kg"].iloc[-1])
                delta_bw = curr_bw - start_bw
                pct_bw = (delta_bw / start_bw * 100.0) if start_bw > 0 else 0.0

                w1, w2, w3, w4 = st.columns(4)
                w1.metric("Startgewicht", f"{start_bw:.1f} kg")
                w2.metric("Aktuell", f"{curr_bw:.1f} kg")
                w3.metric("Veränderung", f"{delta_bw:+.1f} kg", delta=f"{delta_bw:+.1f} kg")
                w4.metric("In Prozent", f"{pct_bw:+.1f} %")

            st.markdown("#### Gespeicherte Gewichtseinträge")
            bw_cols = [c for c in ["datum", "rhythmus", "gewicht_kg", "notiz"] if c in bw_df.columns]
            st.dataframe(bw_df.sort_values("datum", ascending=False)[bw_cols], use_container_width=True, hide_index=True)

            with st.expander("Gewichtseintrag löschen"):
                bw_labels = [
                    f"#{i + 1} · {item.get('datum')} · {item.get('gewicht_kg')} kg ({item.get('rhythmus', '-')})"
                    for i, item in enumerate(st.session_state.bodyweight_logs)
                ]
                pick_bw_del = st.selectbox("Eintrag wählen", bw_labels, key="bw_del_select")
                if st.button("Gewichtseintrag löschen"):
                    st.session_state.bodyweight_logs.pop(bw_labels.index(pick_bw_del))
                    save_json(WEIGHT_FILE, st.session_state.bodyweight_logs)
                    st.rerun()
        else:
            st.info(
                "Noch kein Körpergewicht eingetragen. Trag links deinen ersten Wert ein, um Verlauf und Veränderung zu sehen."
            )
        st.markdown("</div>", unsafe_allow_html=True)

with tab_history:
    st.markdown('<div class="surface-card">', unsafe_allow_html=True)
    st.markdown("### Fortschritt über Monate & Jahre")
    if st.session_state.entries:
        df = pd.DataFrame(st.session_state.entries)
        df["datum_dt"] = pd.to_datetime(df["datum"])
        df["monat"] = df["datum_dt"].dt.to_period("M").astype(str)
        exercises = sorted(df["uebung"].dropna().unique())

        c_ex, c_mode = st.columns([1.2, 1.8])
        ex_pick = c_ex.selectbox("Übung wählen", exercises, key="hist_ex")
        mode_pick = c_mode.radio(
            "Darstellung",
            ["Monats-Maximalgewicht (Balken)", "Alle Einträge (Verlauf)"],
            horizontal=True,
        )

        sub = df[df["uebung"] == ex_pick].sort_values("datum_dt")
        if mode_pick == "Monats-Maximalgewicht (Balken)":
            m_df = sub.groupby("monat", as_index=False)["gewicht_kg"].max()
            bars = (
                alt.Chart(m_df)
                .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, color="#a855f7")
                .encode(
                    x=alt.X("monat:N", title="Monat"),
                    y=alt.Y("gewicht_kg:Q", title="Max. Gewicht (kg)", scale=alt.Scale(zero=False)),
                    tooltip=["monat", "gewicht_kg"],
                )
                .properties(height=300)
                .configure_view(strokeOpacity=0)
                .configure_axis(
                    gridColor="rgba(148,163,184,0.12)",
                    labelColor="#94a3b8",
                    titleColor="#cbd5e1",
                )
            )
            st.altair_chart(bars, use_container_width=True)
        else:
            st.line_chart(sub.set_index("datum_dt")[["gewicht_kg"]], height=300)

        st.markdown("#### Alle gespeicherten Sätze")
        filter_ex = st.selectbox(
            "Nach Übung filtern",
            ["Alle Übungen"] + exercises,
            key="hist_filter",
        )
        show_df = df.sort_values("datum", ascending=False)
        if filter_ex != "Alle Übungen":
            show_df = show_df[show_df["uebung"] == filter_ex]

        cols = [
            c
            for c in [
                "datum",
                "trainingstag",
                "uebung",
                "saetze",
                "wiederholungen",
                "gewicht_kg",
                "volumen_kg",
                "geschaetzt_1rm_kg",
                "notiz",
            ]
            if c in show_df.columns
        ]
        st.dataframe(show_df[cols], use_container_width=True, hide_index=True)

        with st.expander("Eintrag löschen"):
            labels = [
                f"#{i + 1} · {e.get('datum')} · {e.get('uebung')} · {e.get('gewicht_kg')} kg"
                for i, e in enumerate(st.session_state.entries)
            ]
            chosen_del = st.selectbox("Eintrag auswählen", labels)
            if st.button("Ausgewählten Eintrag löschen"):
                st.session_state.entries.pop(labels.index(chosen_del))
                save_json(DATA_FILE, st.session_state.entries)
                st.rerun()
    else:
        st.info("Noch keine Einträge gespeichert.")
    st.markdown("</div>", unsafe_allow_html=True)

with tab_supps:
    st.markdown('<div class="surface-card">', unsafe_allow_html=True)
    st.markdown("### Dein persönlicher Supplement-Stack")
    st.caption(
        "Wähle einzelne Supplemente direkt an oder ab – dein Stack speichert sich automatisch. Basis bleiben immer Training, Schlaf und Ernährung."
    )

    names_list = [s["name"] for s in SUPPLEMENTS_CATALOG]
    current_defaults = [s for s in st.session_state.active_supps if s in names_list]

    picked_supps = st.multiselect(
        "Schnellauswahl über Liste",
        options=names_list,
        default=current_defaults,
    )

    if picked_supps != st.session_state.active_supps:
        st.session_state.active_supps = list(picked_supps)
        save_json(STACK_FILE, st.session_state.active_supps)
        st.rerun()

    if st.session_state.active_supps:
        st.success("Aktuell aktiv: " + " · ".join(st.session_state.active_supps))
    else:
        st.info("Derzeit keine Supplemente ausgewählt.")
    st.markdown("</div>", unsafe_allow_html=True)

    f1, f2 = st.columns([1.2, 1.8])
    cat_options = ["Alle Kategorien"] + sorted({s["kategorie"] for s in SUPPLEMENTS_CATALOG})
    selected_cat = f1.selectbox("Kategorie filtern", cat_options)
    only_selected = f2.checkbox("Nur meine ausgewählten Supplemente anzeigen", value=False)

    cards_to_show = SUPPLEMENTS_CATALOG
    if only_selected:
        cards_to_show = [s for s in cards_to_show if s["name"] in st.session_state.active_supps]
    if selected_cat != "Alle Kategorien":
        cards_to_show = [s for s in cards_to_show if s["kategorie"] == selected_cat]

    supp_changed = False
    active_set = set(st.session_state.active_supps)

    for idx in range(0, len(cards_to_show), 2):
        row_cols = st.columns(2, gap="large")
        for col_i in range(2):
            if idx + col_i < len(cards_to_show):
                supp = cards_to_show[idx + col_i]
                is_active = supp["name"] in active_set
                card_class = "supp-card supp-card-active" if is_active else "supp-card"
                mine_badge = '<span class="badge-mine">AKTIV</span>' if is_active else ""

                with row_cols[col_i]:
                    st.markdown(
                        f"""
                        <div class="{card_class}">
                            <span class="badge-cat">{supp["kategorie"]}</span>{mine_badge}
                            <h4 class="supp-heading">{supp["name"]}</h4>
                            <p style="color:#cbd5e1; margin:0 0 8px 0; line-height:1.5;">{supp["wirkung"]}</p>
                            <div class="supp-detail">
                                <strong>Typischer Einsatz:</strong> {supp["einnahme"]}<br>
                                <strong>Praxistipp:</strong> {supp["tipp"]}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    toggle_val = st.checkbox(
                        "Nehme ich aktuell",
                        value=is_active,
                        key=f"supp_toggle_{supp['name']}",
                    )
                    if toggle_val and not is_active:
                        active_set.add(supp["name"])
                        supp_changed = True
                    elif not toggle_val and is_active:
                        active_set.discard(supp["name"])
                        supp_changed = True

    if supp_changed:
        st.session_state.active_supps = [n for n in names_list if n in active_set]
        save_json(STACK_FILE, st.session_state.active_supps)
        st.rerun()
