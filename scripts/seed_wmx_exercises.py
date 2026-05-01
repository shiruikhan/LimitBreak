"""
seed_wmx_exercises.py — Cadastra os exercícios do protocolo WMX (Silvio Vieira).

Inclui:
  - Exercícios do Treino A, B e C
  - Alongamentos prescritos dentro dos treinos
  - Exercícios de mobilidade pré-treino do rodapé do protocolo

Idempotente: checa name_pt antes de inserir — não duplica se já existir.

Executar:
    python scripts/seed_wmx_exercises.py
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_PARAMS = dict(
    host=os.getenv("host"),
    port=os.getenv("port"),
    dbname=os.getenv("database"),
    user=os.getenv("user"),
    password=os.getenv("password"),
    sslmode="require",
)

# ---------------------------------------------------------------------------
# Catálogo de exercícios
# Cada entrada: (name_en, name_pt, target_muscles[], body_parts[], equipments[])
# ---------------------------------------------------------------------------
EXERCISES = [
    # ── TREINO A — Membros Inferiores + Core ────────────────────────────────
    (
        "Bird Dog",
        "Perdigueiro",
        ["Erector Spinae", "Glutes", "Core"],
        ["back", "waist"],
        ["body weight"],
    ),
    (
        "Box Plank",
        "Prancha Isométrica no Caixote",
        ["Core", "Rectus Abdominis", "Transverse Abdominis"],
        ["waist"],
        ["box"],
    ),
    (
        "Hip Thrust with Miniband",
        "Elevação Pélvica no Solo com Miniband",
        ["Glutes", "Hamstrings", "Hip Abductors"],
        ["upper legs"],
        ["band"],
    ),
    (
        "Lying Leg Curl with Ankle Weight",
        "Flexão de Joelho com Caneleira",
        ["Hamstrings"],
        ["upper legs"],
        ["ankle weights"],
    ),
    (
        "Box Step-Up",
        "Step-Up no Caixote",
        ["Quadriceps", "Glutes", "Hamstrings"],
        ["upper legs"],
        ["box"],
    ),
    (
        "Knee Extension with Band",
        "Extensão de Joelho com Miniband",
        ["Quadriceps"],
        ["upper legs"],
        ["band"],
    ),
    (
        "Goblet Squat with Miniband",
        "Agachamento Taça com Miniband",
        ["Quadriceps", "Glutes", "Hip Abductors"],
        ["upper legs"],
        ["dumbbell", "band"],
    ),
    (
        "Hip Hinge",
        "Hip Hinge",
        ["Hamstrings", "Glutes", "Erector Spinae"],
        ["upper legs", "back"],
        ["body weight"],
    ),
    (
        "Side Plank",
        "Prancha Lateral",
        ["Obliques", "Core"],
        ["waist"],
        ["body weight"],
    ),

    # ── TREINO B — Costas + Bíceps + Core ───────────────────────────────────
    (
        "Cable High Row with Rope",
        "Remada na Polia Alta com Corda",
        ["Rhomboids", "Trapezius", "Rear Deltoid"],
        ["back"],
        ["cable"],
    ),
    (
        "Face Pull with Band",
        "Face Pull com Band",
        ["Rear Deltoid", "Rotator Cuff", "Trapezius"],
        ["shoulders"],
        ["band"],
    ),
    (
        "Shoulder Adduction with Band",
        "Adução de Ombros com Band",
        ["Trapezius", "Rhomboids"],
        ["back", "shoulders"],
        ["band"],
    ),
    (
        "T Raise",
        "Elevação T no Solo",
        ["Rear Deltoid", "Rhomboids", "Trapezius"],
        ["back", "shoulders"],
        ["body weight"],
    ),
    (
        "Lat Pulldown with Medium Bar",
        "Puxada Frontal com Barra Média",
        ["Latissimus Dorsi", "Biceps Brachii"],
        ["back"],
        ["cable"],
    ),
    (
        "Unilateral Dead Bug",
        "Dead-Bug Unilateral",
        ["Core", "Rectus Abdominis", "Transverse Abdominis"],
        ["waist"],
        ["body weight"],
    ),
    (
        "Alternating Oblique Crunch",
        "Abdominal Oblíquo Alternado",
        ["Obliques"],
        ["waist"],
        ["body weight"],
    ),

    # ── TREINO C — Ombros + Peito + Tríceps + Panturrilha ──────────────────
    (
        "Dumbbell Lateral Raise",
        "Elevação Lateral com Halter",
        ["Lateral Deltoid"],
        ["shoulders"],
        ["dumbbell"],
    ),
    (
        "Y Raise with Band",
        "Elevação Y com Band",
        ["Lower Trapezius", "Rear Deltoid"],
        ["back", "shoulders"],
        ["band"],
    ),
    (
        "Reverse Fly with Band",
        "Crucifixo Inverso com Band",
        ["Rear Deltoid", "Rhomboids"],
        ["back", "shoulders"],
        ["band"],
    ),
    (
        "Lateral Walk with Miniband",
        "Deslocamento Lateral com Miniband",
        ["Glutes", "Hip Abductors"],
        ["upper legs"],
        ["band"],
    ),
    (
        "Donkey Calf Raise",
        "Panturrilha no Burrinho",
        ["Gastrocnemius", "Soleus"],
        ["lower legs"],
        ["machine"],
    ),
    (
        "Tibialis Raise Machine",
        "Tibial na Máquina",
        ["Tibialis Anterior"],
        ["lower legs"],
        ["machine"],
    ),
    (
        "Chest Fly with Band",
        "Crucifixo com Elástico",
        ["Pectoralis Major"],
        ["chest"],
        ["band"],
    ),
    (
        "French Press with Plate",
        "Tríceps Francês com Anilha",
        ["Triceps Brachii"],
        ["upper arms"],
        ["weighted"],
    ),
    (
        "Dumbbell Bench Press on Step",
        "Supino com Halter no Step",
        ["Pectoralis Major", "Anterior Deltoid", "Triceps Brachii"],
        ["chest"],
        ["dumbbell"],
    ),
    (
        "Dumbbell Pullover on Step",
        "Pull-Over no Step",
        ["Pectoralis Major", "Latissimus Dorsi"],
        ["chest", "back"],
        ["dumbbell"],
    ),
    (
        "Upper Crunch",
        "Abdominal Supra",
        ["Rectus Abdominis"],
        ["waist"],
        ["body weight"],
    ),

    # ── ALONGAMENTOS prescritos nos treinos ─────────────────────────────────
    (
        "Lying Unilateral Hamstring Stretch",
        "Alongamento de Posterior Unilateral Deitado",
        ["Hamstrings"],
        ["upper legs"],
        ["body weight"],
    ),
    (
        "L-Shaped Glute Stretch",
        "Alongamento de Glúteo em L",
        ["Glutes", "Piriformis"],
        ["upper legs"],
        ["body weight"],
    ),
    (
        "Sphinx Stretch",
        "Alongamento Esfinge",
        ["Erector Spinae", "Rectus Abdominis"],
        ["back"],
        ["body weight"],
    ),
    (
        "Bow Stretch",
        "Alongamento em Reverência",
        ["Latissimus Dorsi", "Erector Spinae"],
        ["back"],
        ["body weight"],
    ),

    # ── MOBILIDADE PRÉ-TREINO (rodapé do protocolo) ─────────────────────────
    (
        "Dead Hang",
        "Suspensão no Espaldar",
        ["Latissimus Dorsi", "Shoulder Girdle"],
        ["back", "shoulders"],
        ["body weight"],
    ),
    (
        "Wall Scapular Adduction",
        "Adução Escapular na Parede",
        ["Rhomboids", "Trapezius"],
        ["back"],
        ["body weight"],
    ),
    (
        "Shoulder Mobility with Bar",
        "Mobilidade de Ombros com Bastão",
        ["Rotator Cuff", "Shoulder Girdle"],
        ["shoulders"],
        ["barbell"],
    ),
    (
        "90/90 Hip Mobility",
        "Quadril 90/90",
        ["Hip Flexors", "Piriformis", "Glutes"],
        ["upper legs"],
        ["body weight"],
    ),
    (
        "Lat Stretch on Wall Bars",
        "Alongamento do Latíssimo no Espaldar",
        ["Latissimus Dorsi"],
        ["back"],
        ["body weight"],
    ),
    (
        "Thoracic Mobility",
        "Mobilidade Torácica",
        ["Thoracic Spine", "Erector Spinae"],
        ["back"],
        ["body weight"],
    ),
    (
        "Piriformis Stretch",
        "Alongamento do Piriforme",
        ["Piriformis", "Glutes"],
        ["upper legs"],
        ["body weight"],
    ),
]


def main():
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()

    # Carrega name_pt já existentes para evitar duplicatas
    cur.execute("SELECT name_pt FROM exercises;")
    existing = {row[0] for row in cur.fetchall()}

    inserted = 0
    skipped = 0

    for name_en, name_pt, target_muscles, body_parts, equipments in EXERCISES:
        if name_pt in existing:
            print(f"  [skip] {name_pt}")
            skipped += 1
            continue

        cur.execute(
            """
            INSERT INTO exercises (name, name_pt, target_muscles, body_parts, equipments)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (name_en, name_pt, target_muscles, body_parts, equipments),
        )
        new_id = cur.fetchone()[0]
        print(f"  [ok]   #{new_id} — {name_pt}")
        inserted += 1

    conn.commit()
    cur.close()
    conn.close()

    print(f"\nConcluído: {inserted} inserido(s), {skipped} ignorado(s).")


if __name__ == "__main__":
    main()
