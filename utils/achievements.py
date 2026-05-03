"""Achievement catalog and badge URL helpers."""
import urllib.parse

# Category display metadata
CATEGORY_META: dict[str, dict] = {
    "treino":   {"label": "TREINO",   "display": "Treino",    "icon": "🏋️", "color": "22c55e"},
    "colecao":  {"label": "DEX",      "display": "Coleção",   "icon": "📦", "color": "3b82f6"},
    "checkin":  {"label": "CHECK-IN", "display": "Check-in",  "icon": "📅", "color": "f97316"},
    "batalha":  {"label": "ARENA",    "display": "Arena",     "icon": "⚔️", "color": "ef4444"},
    "especial": {"label": "ESPECIAL", "display": "Especial",  "icon": "✨", "color": "a855f7"},
    "ginasio":  {"label": "GINASIO",  "display": "Ginásio",   "icon": "🏅", "color": "f59e0b"},
}

# Gym badge metadata: slug → {name, icon, color, description}
# Used to render the badge rack independently of the full CATALOG.
GYM_BADGES: list[dict] = [
    {"slug": "badge_pedra",     "name": "Pedra",     "icon": "🪨", "color": "#6b7280", "desc": "10 sessões de treino"},
    {"slug": "badge_cascata",   "name": "Cascata",   "icon": "💧", "color": "#0ea5e9", "desc": "Streak de 7 dias de check-in"},
    {"slug": "badge_trovao",    "name": "Trovão",    "icon": "⚡", "color": "#eab308", "desc": "5 vitórias em batalha"},
    {"slug": "badge_arco_iris", "name": "Arco-íris", "icon": "🌈", "color": "#a855f7", "desc": "25 Pokémon capturados"},
    {"slug": "badge_alma",      "name": "Alma",      "icon": "👻", "color": "#8b5cf6", "desc": "Streak de 30 dias de treino"},
    {"slug": "badge_pantano",   "name": "Pântano",   "icon": "🌿", "color": "#16a34a", "desc": "10 PRs detectados"},
    {"slug": "badge_vulcao",    "name": "Vulcão",    "icon": "🌋", "color": "#ef4444", "desc": "10 Pokémon evoluídos"},
    {"slug": "badge_terra",     "name": "Terra",     "icon": "🌍", "color": "#92400e", "desc": "100 sessões de treino"},
]

# Full achievement catalog
# Each entry: slug → {name, description, category, icon, badge_color, check: stats→bool}
CATALOG: dict[str, dict] = {

    # ── Treino ────────────────────────────────────────────────────────────────
    "first_workout": {
        "name": "Primeiro Treino",
        "description": "Complete sua primeira sessão de treino",
        "category": "treino", "icon": "🏋️", "badge_color": "22c55e",
        "check": lambda s: s["workout_count"] >= 1,
    },
    "workouts_10": {
        "name": "Iniciante",
        "description": "Complete 10 sessões de treino",
        "category": "treino", "icon": "💪", "badge_color": "22c55e",
        "check": lambda s: s["workout_count"] >= 10,
    },
    "workouts_50": {
        "name": "Dedicado",
        "description": "Complete 50 sessões de treino",
        "category": "treino", "icon": "💪", "badge_color": "16a34a",
        "check": lambda s: s["workout_count"] >= 50,
    },
    "workouts_100": {
        "name": "Elite",
        "description": "Complete 100 sessões de treino",
        "category": "treino", "icon": "🏆", "badge_color": "15803d",
        "check": lambda s: s["workout_count"] >= 100,
    },
    "workout_streak_7": {
        "name": "Semana de Ferro",
        "description": "7 dias consecutivos de treino",
        "category": "treino", "icon": "🔥", "badge_color": "22c55e",
        "check": lambda s: s["workout_streak"] >= 7,
    },
    "workout_streak_30": {
        "name": "Mes de Ferro",
        "description": "30 dias consecutivos de treino",
        "category": "treino", "icon": "🔥", "badge_color": "16a34a",
        "check": lambda s: s["workout_streak"] >= 30,
    },
    "pr_first": {
        "name": "Novo Recorde",
        "description": "Quebre seu primeiro recorde pessoal em um exercício",
        "category": "treino", "icon": "🏅", "badge_color": "ca8a04",
        "check": lambda s: s.get("pr_count", 0) >= 1,
    },
    "pr_10": {
        "name": "Máquina de PRs",
        "description": "Quebre 10 recordes pessoais",
        "category": "treino", "icon": "⚡", "badge_color": "a16207",
        "check": lambda s: s.get("pr_count", 0) >= 10,
    },

    # ── Coleção ───────────────────────────────────────────────────────────────
    "first_capture": {
        "name": "Primeira Captura",
        "description": "Capture seu primeiro Pokemon",
        "category": "colecao", "icon": "🎮", "badge_color": "3b82f6",
        "check": lambda s: s["pokemon_count"] >= 1,
    },
    "dex_10": {
        "name": "Colecionador",
        "description": "Tenha 10 Pokemon diferentes",
        "category": "colecao", "icon": "📦", "badge_color": "3b82f6",
        "check": lambda s: s["pokemon_count"] >= 10,
    },
    "dex_50": {
        "name": "Grande Colecionador",
        "description": "Tenha 50 Pokemon diferentes",
        "category": "colecao", "icon": "📦", "badge_color": "2563eb",
        "check": lambda s: s["pokemon_count"] >= 50,
    },
    "dex_100": {
        "name": "Centuria",
        "description": "Tenha 100 Pokemon diferentes",
        "category": "colecao", "icon": "🌟", "badge_color": "1d4ed8",
        "check": lambda s: s["pokemon_count"] >= 100,
    },
    "dex_200": {
        "name": "Enciclopedia",
        "description": "Tenha 200 Pokemon diferentes",
        "category": "colecao", "icon": "🌟", "badge_color": "1e40af",
        "check": lambda s: s["pokemon_count"] >= 200,
    },
    "dex_500": {
        "name": "Mestre Pokemon",
        "description": "Tenha 500 Pokemon diferentes",
        "category": "colecao", "icon": "👑", "badge_color": "1e3a8a",
        "check": lambda s: s["pokemon_count"] >= 500,
    },
    "dex_complete": {
        "name": "Lenda",
        "description": "Complete a Pokedex Nacional com 1025 especies",
        "category": "colecao", "icon": "🏆", "badge_color": "172554",
        "check": lambda s: s["pokemon_count"] >= 1025,
    },

    # ── Check-in ──────────────────────────────────────────────────────────────
    "checkin_streak_7": {
        "name": "Pontual",
        "description": "7 dias consecutivos de check-in",
        "category": "checkin", "icon": "📅", "badge_color": "f97316",
        "check": lambda s: s["checkin_streak_max"] >= 7,
    },
    "checkin_streak_30": {
        "name": "Assiduo",
        "description": "30 dias consecutivos de check-in",
        "category": "checkin", "icon": "🗓️", "badge_color": "ea580c",
        "check": lambda s: s["checkin_streak_max"] >= 30,
    },
    "checkin_streak_100": {
        "name": "Centuriao",
        "description": "100 dias consecutivos de check-in",
        "category": "checkin", "icon": "🔥", "badge_color": "c2410c",
        "check": lambda s: s["checkin_streak_max"] >= 100,
    },
    "checkin_streak_365": {
        "name": "Imortal",
        "description": "365 dias consecutivos de check-in",
        "category": "checkin", "icon": "⚡", "badge_color": "9a3412",
        "check": lambda s: s["checkin_streak_max"] >= 365,
    },

    # ── Batalha ───────────────────────────────────────────────────────────────
    "first_win": {
        "name": "Primeira Vitoria",
        "description": "Venca sua primeira batalha PvP",
        "category": "batalha", "icon": "⚔️", "badge_color": "ef4444",
        "check": lambda s: s["battle_wins"] >= 1,
    },
    "wins_10": {
        "name": "Gladiador",
        "description": "Venca 10 batalhas PvP",
        "category": "batalha", "icon": "🥊", "badge_color": "dc2626",
        "check": lambda s: s["battle_wins"] >= 10,
    },
    "wins_50": {
        "name": "Campeao",
        "description": "Venca 50 batalhas PvP",
        "category": "batalha", "icon": "🏆", "badge_color": "b91c1c",
        "check": lambda s: s["battle_wins"] >= 50,
    },

    # ── Ginásio ───────────────────────────────────────────────────────────────
    "badge_pedra": {
        "name": "Insígnia Pedra",
        "description": "Complete 10 sessões de treino",
        "category": "ginasio", "icon": "🪨", "badge_color": "6b7280",
        "check": lambda s: s["workout_count"] >= 10,
    },
    "badge_cascata": {
        "name": "Insígnia Cascata",
        "description": "Alcance um streak de 7 dias de check-in",
        "category": "ginasio", "icon": "💧", "badge_color": "0ea5e9",
        "check": lambda s: s["checkin_streak_max"] >= 7,
    },
    "badge_trovao": {
        "name": "Insígnia Trovão",
        "description": "Vença 5 batalhas PvP",
        "category": "ginasio", "icon": "⚡", "badge_color": "eab308",
        "check": lambda s: s["battle_wins"] >= 5,
    },
    "badge_arco_iris": {
        "name": "Insígnia Arco-íris",
        "description": "Capture 25 Pokémon diferentes",
        "category": "ginasio", "icon": "🌈", "badge_color": "a855f7",
        "check": lambda s: s["pokemon_count"] >= 25,
    },
    "badge_alma": {
        "name": "Insígnia Alma",
        "description": "Alcance um streak de 30 dias consecutivos de treino",
        "category": "ginasio", "icon": "👻", "badge_color": "8b5cf6",
        "check": lambda s: s["workout_streak"] >= 30,
    },
    "badge_pantano": {
        "name": "Insígnia Pântano",
        "description": "Quebre 10 recordes pessoais",
        "category": "ginasio", "icon": "🌿", "badge_color": "16a34a",
        "check": lambda s: s.get("pr_count", 0) >= 10,
    },
    "badge_vulcao": {
        "name": "Insígnia Vulcão",
        "description": "Tenha 10 Pokémon evoluídos na sua coleção",
        "category": "ginasio", "icon": "🌋", "badge_color": "ef4444",
        "check": lambda s: s.get("evolved_count", 0) >= 10,
    },
    "badge_terra": {
        "name": "Insígnia Terra",
        "description": "Complete 100 sessões de treino",
        "category": "ginasio", "icon": "🌍", "badge_color": "92400e",
        "check": lambda s: s["workout_count"] >= 100,
    },

    # ── Especial ──────────────────────────────────────────────────────────────
    "first_evolution": {
        "name": "Evolucao",
        "description": "Tenha um Pokemon evoluido na sua colecao",
        "category": "especial", "icon": "✨", "badge_color": "a855f7",
        "check": lambda s: s["has_evolved_pokemon"],
    },
    "shiny_catch": {
        "name": "Astro Raro",
        "description": "Capture um Pokemon shiny",
        "category": "especial", "icon": "⭐", "badge_color": "eab308",
        "check": lambda s: s["has_shiny"],
    },
    "regional_form": {
        "name": "Explorador",
        "description": "Capture uma forma regional (Alola, Galar ou Hisui)",
        "category": "especial", "icon": "🌏", "badge_color": "8b5cf6",
        "check": lambda s: s["has_regional"],
    },
    "stone_evolution": {
        "name": "Alquimista",
        "description": "Evolua um Pokemon usando uma pedra",
        "category": "especial", "icon": "💎", "badge_color": "7c3aed",
        "check": lambda s: s["has_stone_evolved"],
    },
}


def _encode(text: str) -> str:
    """Encode text for shields.io path segment (spaces→_, -→--, _→__, then URL-encode)."""
    text = text.replace("_", "__").replace("-", "--").replace(" ", "_")
    return urllib.parse.quote(text, safe="_-")


def badge_url(slug: str, unlocked: bool) -> str:
    """Return a shields.io badge URL for the given achievement."""
    ach = CATALOG[slug]
    cat_label = CATEGORY_META[ach["category"]]["label"]
    name = ach["name"]
    color = ach["badge_color"] if unlocked else "555555"
    return (
        f"https://img.shields.io/badge/{_encode(cat_label)}-{_encode(name)}-{color}"
        f"?style=for-the-badge"
    )
