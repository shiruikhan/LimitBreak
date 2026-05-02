import os
import streamlit as st
import extra_streamlit_components as stx
from utils.app_cache import (
    clear_user_cache,
    get_cached_team_stat_boost_counts,
    get_cached_user_bench,
    get_cached_user_profile,
    get_cached_user_team,
    get_cached_xp_share_status,
)
from utils.db import (
    _MAX_STAT_BOOSTS_PER_STAT,
    swap_team_slots,
    remove_from_team, add_to_team, get_image_as_base64, sprite_img_tag,
    get_available_moves, get_active_moves, equip_move, unequip_move,
    get_user_eggs,
)
from utils.type_colors import get_type_color
from utils.abilities import get_ability_description as _get_ability_desc
from utils.quest_tracker import render_quest_sidebar

BASE_DIR   = os.getcwd()
XP_PER_LV  = 100   # XP needed = level * XP_PER_LV

_cookie_manager = stx.CookieManager(key="lb_cookies_logout")

user_id = st.session_state.get("user_id")
if not user_id:
    st.error("Sessão expirada. Faça login novamente.")
    st.stop()

# ── Helpers ────────────────────────────────────────────────────────────────────

def _thumb_path(pokemon_id: int) -> str:
    """Retorna o caminho local do thumbnail (pode não existir em produção)."""
    return os.path.join(BASE_DIR, "src", "Pokemon", "assets", "thumbnails",
                        f"{str(pokemon_id).zfill(4)}.png")

def _dmg_icon(damage_class: str | None) -> str:
    if not damage_class:
        return ""
    path = os.path.join(BASE_DIR, "src", "Pokemon", "assets", "Others",
                        "damage-category-icons", "1x", f"{damage_class.capitalize()}.png")
    b64 = get_image_as_base64(path)
    return f"<img src='data:image/png;base64,{b64}' width='18' style='vertical-align:middle'>" if b64 else ""

def _type_icon(type_name: str | None) -> str:
    if not type_name:
        return ""
    path = os.path.join(BASE_DIR, "src", "Pokemon", "assets", "Others",
                        "type-icons", "png", f"{type_name.lower()}.png")
    b64 = get_image_as_base64(path)
    return f"<img src='data:image/png;base64,{b64}' width='16' style='vertical-align:middle'>" if b64 else ""

def _xp_progress(level: int, xp: int) -> float:
    needed = level * XP_PER_LV
    return min(xp / needed, 1.0) if needed else 1.0


def _nature_html(member: dict, *, compact: bool = False, align: str = "center") -> str:
    nature = member.get("nature")
    if not nature:
        return ""

    chip_classes = "nature-chip neutral" if nature["is_neutral"] else "nature-chip"
    row_classes = "nature-row compact" if compact else "nature-row"
    effect = "Neutral" if nature["is_neutral"] else nature["summary"]
    effect_html = (
        f"<span class='nature-effect'>{effect}</span>"
        if not compact
        else ""
    )
    return (
        f"<div class='{row_classes}' style='justify-content:{align}'>"
        f"<span class='{chip_classes}'>{nature['name']} Nature</span>"
        f"{effect_html}"
        f"</div>"
    )

# Cores canônicas de cada stat (padrão Pokémon)
_STAT_COLORS = {
    "HP":     "#FF5959",
    "ATK":    "#F5AC78",
    "DEF":    "#FAE078",
    "SP.ATK": "#9DB7F5",
    "SP.DEF": "#A7DB8D",
    "SPD":    "#FA92B2",
}
_STAT_MAX = 255  # maior stat base possível

# Mapeamento de label de exibição → chave de stat no banco
_STAT_LABEL_TO_KEY = {
    "HP":     "hp",
    "ATK":    "attack",
    "DEF":    "defense",
    "SP.ATK": "sp_attack",
    "SP.DEF": "sp_defense",
    "SPD":    "speed",
}


def _stat_bars(member: dict, boost_counts: dict | None = None) -> str:
    """Retorna o HTML do mini-grid de stats para um card de Pokémon.

    boost_counts: {stat_key: count} para o Pokémon — exibe 🔒 quando capped.
    """
    stats = [
        ("HP",     member["stat_hp"]),
        ("ATK",    member["stat_attack"]),
        ("DEF",    member["stat_defense"]),
        ("SP.ATK", member["stat_sp_attack"]),
        ("SP.DEF", member["stat_sp_defense"]),
        ("SPD",    member["stat_speed"]),
    ]
    rows = ""
    for label, val in stats:
        pct   = min((val or 0) / _STAT_MAX * 100, 100)
        color = _STAT_COLORS[label]
        stat_key = _STAT_LABEL_TO_KEY[label]
        is_capped = (
            boost_counts is not None
            and boost_counts.get(stat_key, 0) >= _MAX_STAT_BOOSTS_PER_STAT
        )
        lock_html = (
            "<span style='font-size:0.55rem;color:#F8D030;margin-left:2px' "
            "title='Vitaminas no limite'>🔒</span>"
            if is_capped else ""
        )
        rows += (
            f"<div class='stat-row-mini'>"
            f"<span class='stat-lbl-mini'>{label}</span>"
            f"<div class='stat-bar-mini'>"
            f"<div class='stat-fill-mini' style='width:{pct:.0f}%;background:{color}'></div>"
            f"</div>"
            f"<span class='stat-val-mini'>{val or 0}{lock_html}</span>"
            f"</div>"
        )
    return f"<div class='stat-grid'>{rows}</div>"

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.stApp { background: #0d1117; color: #e6edf3; }
[data-testid="stSidebar"] { background-color: #0d1117 !important; border-right: 1px solid #21262d; }
[data-testid="stSidebar"] * { color: #e6edf3 !important; }

.page-title {
    font-family: "Bebas Neue", sans-serif;
    font-size: 2.4rem; font-weight: 400; letter-spacing: 4px;
    background: linear-gradient(90deg, #D4FC6B, #B8F82F);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 4px; text-transform: uppercase;
}
.page-sub { color: #8b949e; font-size: 0.85rem; margin-bottom: 20px; }

/* Team card */
.team-card {
    background: #161b22; border: 1px solid #30363d; border-radius: 16px;
    padding: 16px 12px; transition: all 0.2s ease; min-height: 200px;
}
.team-card.main-slot {
    border-color: #B8F82F;
    box-shadow: 0 0 0 1px #B8F82F, 0 8px 24px rgba(184,248,47,0.15);
}
.team-card.selected-slot {
    border-color: #58a6ff;
    box-shadow: 0 0 0 1px #58a6ff, 0 8px 24px rgba(88,166,255,0.15);
}
.team-card.empty-slot {
    border: 2px dashed #21262d; background: #0d1117;
    display: flex; align-items: center; justify-content: center;
}
.slot-label { font-size: 0.62rem; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: #8b949e; margin-bottom: 8px; }
.main-label { font-size: 0.62rem; font-weight: 700; letter-spacing: 2px; color: #B8F82F; text-transform: uppercase; }
.sel-label  { font-size: 0.62rem; font-weight: 700; letter-spacing: 2px; color: #58a6ff; text-transform: uppercase; }
.poke-card-name { font-size: 0.88rem; font-weight: 700; color: #e6edf3; margin: 4px 0 2px; text-align: center; }
.type-sm {
    display: inline-block; padding: 2px 7px; border-radius: 9999px;
    font-size: 0.58rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-right: 3px;
}
.xp-track { background: #21262d; border-radius: 9999px; height: 4px; margin-top: 8px; overflow: hidden; border: 1px solid #30363d; }
.xp-fill  { height: 100%; border-radius: 9999px; background: #58A6FF; }
.xp-label { font-size: 0.62rem; color: #8b949e; margin-top: 2px; font-family: "JetBrains Mono", monospace; }
.nature-row {
    margin-top: 6px; display: flex; align-items: center; gap: 6px;
    flex-wrap: wrap;
}
.nature-row.compact { margin-top: 4px; }
.nature-chip {
    display: inline-flex; align-items: center; justify-content: center;
    padding: 3px 8px; border-radius: 9999px;
    background: rgba(210,168,255,0.10); border: 1px solid rgba(210,168,255,0.35);
    color: #d2a8ff; font-size: 0.58rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.6px;
}
.nature-chip.neutral {
    background: rgba(88,166,255,0.10); border-color: rgba(88,166,255,0.35);
    color: #79c0ff;
}
.nature-effect {
    font-size: 0.62rem; color: #8b949e; font-weight: 600;
    letter-spacing: 0.2px;
}

/* Stats mini-grid */
.stat-grid { margin-top: 10px; display: flex; flex-direction: column; gap: 4px; }
.stat-row-mini {
    display: grid; grid-template-columns: 34px 1fr 32px;
    align-items: center; gap: 6px;
}
.stat-lbl-mini { font-size: 0.55rem; font-weight: 700; color: #8b949e;
                  text-transform: uppercase; letter-spacing: 0.5px; }
.stat-bar-mini { background: #21262d; border-radius: 3px; height: 6px; overflow: hidden; }
.stat-fill-mini { height: 100%; border-radius: 3px; transition: width 0.3s ease; }
.stat-val-mini {
    font-size: 0.62rem; font-weight: 700; color: #e6edf3; text-align: right;
    font-family: "JetBrains Mono", ui-monospace, monospace;
}
.coins-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: linear-gradient(135deg, #FFC531, #B38200);
    border-radius: 9999px; padding: 6px 14px;
    font-weight: 800; font-size: 0.85rem; color: #0d1117;
}

/* Ability badge (slot 1) */
.ability-badge {
    display: inline-flex; align-items: center; gap: 5px;
    background: rgba(168,85,247,0.12); border: 1px solid rgba(168,85,247,0.4);
    border-radius: 9999px; padding: 3px 10px;
    font-size: 0.6rem; font-weight: 700; color: #d8b4fe;
    text-transform: uppercase; letter-spacing: 0.5px; margin-top: 5px;
}

/* Egg section */
.egg-section-title {
    font-family: "Bebas Neue", sans-serif;
    font-size: 1.1rem; letter-spacing: 3px; color: #e6edf3;
    text-transform: uppercase; margin-bottom: 10px;
}
.egg-card {
    background: #161b22; border: 1px solid #30363d; border-radius: 14px;
    padding: 12px 14px; text-align: center;
}
.egg-card.rarity-uncommon { border-color: rgba(59,130,246,0.5); }
.egg-card.rarity-rare     { border-color: rgba(168,85,247,0.6); }
.egg-rarity {
    font-size: 0.58rem; font-weight: 700; letter-spacing: 1.5px;
    text-transform: uppercase; margin-bottom: 4px;
}
.egg-rarity.common   { color: #8b949e; }
.egg-rarity.uncommon { color: #58a6ff; }
.egg-rarity.rare     { color: #d2a8ff; }
.egg-progress-bg {
    background: #21262d; border-radius: 9999px; height: 6px;
    margin: 6px 0 4px; overflow: hidden;
}
.egg-progress-fill { height: 100%; border-radius: 9999px; }
.egg-progress-fill.common   { background: #4b5563; }
.egg-progress-fill.uncommon { background: #3b82f6; }
.egg-progress-fill.rare     { background: linear-gradient(90deg, #8b5cf6, #d946ef); }
.egg-remaining { font-size: 0.62rem; color: #8b949e; }

/* Move panel */
.move-panel {
    background: #0d1117; border: 1px solid #21262d; border-radius: 16px;
    padding: 20px 24px; margin-top: 16px;
}
.move-panel-title {
    font-family: "Bebas Neue", sans-serif;
    font-size: 1.2rem; font-weight: 400; letter-spacing: 3px;
    color: #e6edf3; margin-bottom: 16px; text-transform: uppercase;
}
.section-lbl {
    font-size: 0.65rem; font-weight: 700; letter-spacing: 2px;
    text-transform: uppercase; color: #8b949e; margin-bottom: 10px;
}

/* Active move slot */
.move-slot {
    background: #161b22; border: 1px solid #30363d; border-radius: 10px;
    padding: 10px 14px; margin-bottom: 8px;
    display: flex; align-items: center; gap: 10px;
    transition: border-color 0.15s ease;
}
.move-slot:hover { border-color: #484f58; }
.move-slot.empty-move {
    border: 1px dashed #30363d; background: #0d1117;
    justify-content: center; color: #8b949e; font-size: 0.8rem;
}
.move-slot-num {
    font-size: 0.62rem; font-weight: 700; color: #8b949e;
    min-width: 18px; text-align: center;
    font-family: "JetBrains Mono", monospace;
}
.move-slot-name { flex: 1; font-weight: 600; font-size: 0.88rem; color: #e6edf3; }
.move-stat {
    font-size: 0.65rem; color: #8b949e; text-align: center; min-width: 30px;
    font-family: "JetBrains Mono", monospace;
}
.move-stat span { display: block; font-size: 0.55rem; text-transform: uppercase; letter-spacing: 0.5px; }

/* Available move row */
.avail-move {
    display: flex; align-items: center; gap: 8px;
    background: #161b22; border-radius: 10px; padding: 8px 12px; margin-bottom: 6px;
    border-left: 3px solid #30363d;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.avail-move:hover { transform: translateX(4px); box-shadow: 0 4px 16px rgba(0,0,0,0.3); }
.avail-move-lv   { font-size: 0.62rem; font-weight: 700; color: #8b949e; min-width: 32px; font-family: "JetBrains Mono", monospace; }
.avail-move-name { flex: 1; font-weight: 600; font-size: 0.85rem; color: #e6edf3; }
.avail-scroll { max-height: 380px; overflow-y: auto; padding-right: 4px; }
.avail-scroll::-webkit-scrollbar { width: 4px; }
.avail-scroll::-webkit-scrollbar-thumb { background: #30363d; border-radius: 4px; }

/* Replace mode highlight */
.replace-mode { border-color: #F8D030 !important; background: rgba(248,208,48,0.06) !important; }

/* Banco de Pokémon */
.bench-title {
    font-size: 0.65rem; font-weight: 700; letter-spacing: 2px;
    text-transform: uppercase; color: #8b949e;
    border-bottom: 1px solid #21262d; padding-bottom: 6px; margin: 28px 0 16px;
}
.bench-card {
    background: #161b22; border: 1px solid #30363d; border-radius: 12px;
    padding: 12px 10px 10px; text-align: center;
    transition: border-color 0.2s ease, transform 0.15s ease;
}
.bench-card:hover { border-color: #484f58; transform: translateY(-1px); }
.bench-name { font-size: 0.78rem; font-weight: 700; color: #e6edf3; margin: 4px 0 2px; }
.bench-lv   { font-size: 0.65rem; color: #8b949e; margin-bottom: 4px; font-family: "JetBrains Mono", monospace; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    email = st.session_state.get("user")
    if hasattr(email, "email"):
        st.markdown(f"<small style='color:#8b949e'>👤 {email.email}</small>", unsafe_allow_html=True)
    render_quest_sidebar(user_id)
    st.markdown("---")
    if st.button("Sair", use_container_width=True):
        _cookie_manager.delete("lb_refresh_token", key="delete_on_logout")
        for k in ["user", "user_id", "access_token", "refresh_token", "needs_starter", "starter_checked"]:
            st.session_state[k] = None
        st.rerun()

# ── Session state defaults ─────────────────────────────────────────────────────
for k, v in [
    ("sel_team_slot", None),
    ("replacing_move_id", None),
    ("team_evo_notice", None),
    ("team_shed_notice", None),
    ("team_spawn_notice", None),
    ("xp_share_log", None),
]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Evolution notice banner ────────────────────────────────────────────────────
evo_notice = st.session_state.team_evo_notice
if evo_notice:
    _evo_b64   = None
    _evo_sprite = evo_notice.get("sprite_url", "")
    if _evo_sprite:
        _evo_full = os.path.join(BASE_DIR, _evo_sprite.lstrip("/\\"))
        _evo_hq   = _evo_full.replace("/images/", "/imagesHQ/").replace("\\images\\", "\\imagesHQ\\")
        _evo_b64  = get_image_as_base64(_evo_hq) or get_image_as_base64(_evo_full)

    _evo_img = (
        f"<img src='data:image/png;base64,{_evo_b64}' "
        f"style='width:72px;image-rendering:pixelated;filter:drop-shadow(0 0 10px #BC8CFF)'>"
        if _evo_b64 else "<div style='font-size:2.5rem'>🌟</div>"
    )
    st.markdown(
        f"<div style='background:#1f0f2e;border:1px solid #BC8CFF;border-radius:14px;"
        f"padding:16px 20px;margin-bottom:16px;display:flex;align-items:center;gap:16px'>"
        f"<div>{_evo_img}</div>"
        f"<div>"
        f"<div style='font-weight:800;color:#e6edf3;font-size:1rem'>🌟 Pokémon evoluiu!</div>"
        f"<div style='margin-top:4px'>"
        f"<span style='color:#8b949e;font-weight:700'>{evo_notice.get('from_name','')}</span>"
        f"<span style='color:#BC8CFF;margin:0 8px'>→</span>"
        f"<span style='color:#BC8CFF;font-size:1.05rem;font-weight:800'>{evo_notice.get('to_name','')}</span>"
        f"</div>"
        f"<div style='color:#8b949e;font-size:0.8rem;margin-top:4px'>"
        f"Stats recalculados para a nova forma!</div>"
        f"</div></div>",
        unsafe_allow_html=True,
    )
    st.session_state.team_evo_notice = None

# ── Shedinja capture banner ────────────────────────────────────────────────────
shed_notice = st.session_state.team_shed_notice
if shed_notice:
    _shed_b64    = None
    _shed_sprite = shed_notice.get("sprite_url", "")
    if _shed_sprite:
        _shed_full = os.path.join(BASE_DIR, _shed_sprite.lstrip("/\\"))
        _shed_hq   = _shed_full.replace("/images/", "/imagesHQ/").replace("\\images\\", "\\imagesHQ\\")
        _shed_b64  = get_image_as_base64(_shed_hq) or get_image_as_base64(_shed_full)

    _shed_img = (
        f"<img src='data:image/png;base64,{_shed_b64}' "
        f"style='width:72px;image-rendering:pixelated;filter:drop-shadow(0 0 10px #2ea043)'>"
        if _shed_b64 else "<div style='font-size:2.5rem'>👻</div>"
    )
    st.markdown(
        f"<div style='background:rgba(22,60,24,0.6);border:1px solid rgba(46,160,67,0.6);"
        f"border-radius:14px;padding:16px 20px;margin-bottom:16px;"
        f"display:flex;align-items:center;gap:16px'>"
        f"<div>{_shed_img}</div>"
        f"<div>"
        f"<div style='font-weight:800;color:#e6edf3;font-size:1rem'>👻 Shedinja capturado!</div>"
        f"<div style='margin-top:4px'>"
        f"<span style='color:#2ea043;font-size:1.05rem;font-weight:800'>"
        f"{shed_notice.get('name', 'Shedinja')}</span>"
        f"</div>"
        f"<div style='color:#8b949e;font-size:0.8rem;margin-top:4px'>"
        f"A muda de {shed_notice.get('from_name', 'Nincada')} ganhou vida e foi adicionada à equipe!"
        f"</div>"
        f"</div></div>",
        unsafe_allow_html=True,
    )
    st.session_state.team_shed_notice = None

# ── Exercise spawn banner ─────────────────────────────────────────────────────
spawn_notice = st.session_state.team_spawn_notice
if spawn_notice:
    _sp_sprite = spawn_notice.get("sprite_url", "")
    _sp_img = (
        sprite_img_tag(_sp_sprite, width=72,
                       extra_style="image-rendering:pixelated;filter:drop-shadow(0 0 10px #7038F8)")
        or "<div style='font-size:2.5rem'>❓</div>"
    )
    st.markdown(
        f"<div style='background:rgba(112,56,248,0.1);border:1px solid rgba(112,56,248,0.5);"
        f"border-radius:14px;padding:16px 20px;margin-bottom:16px;"
        f"display:flex;align-items:center;gap:16px'>"
        f"<div>{_sp_img}</div>"
        f"<div>"
        f"<div style='font-weight:800;color:#e6edf3;font-size:1rem'>✨ Pokémon apareceu no treino!</div>"
        f"<div style='margin-top:4px'>"
        f"<span style='color:#A27DFA;font-size:1.1rem;font-weight:800'>"
        f"{spawn_notice.get('name', '')}</span></div>"
        f"<div style='color:#8b949e;font-size:0.8rem;margin-top:4px'>"
        f"#{str(spawn_notice.get('id',0)).zfill(4)} foi capturado e adicionado à sua coleção!</div>"
        f"</div></div>",
        unsafe_allow_html=True,
    )
    st.session_state.team_spawn_notice = None

# ── XP Share distribution log ──────────────────────────────────────────────────
xp_share_log = st.session_state.xp_share_log
if xp_share_log:
    chips = "".join(
        f"<span style='background:#0f2030;border:1px solid #30363d;border-radius:8px;"
        f"padding:3px 10px;font-size:0.75rem;color:#e6edf3;font-weight:600'>"
        f"{entry['name']} <span style='color:#58A6FF'>+{entry['xp']} XP</span></span>"
        for entry in xp_share_log
    )
    st.markdown(
        f"<div style='background:#0f2030;border:1px solid #1c3a52;border-radius:12px;"
        f"padding:12px 16px;margin-bottom:16px'>"
        f"<div style='font-size:0.65rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;"
        f"color:#58A6FF;margin-bottom:8px'>📡 Última distribuição XP Share</div>"
        f"<div style='display:flex;gap:6px;flex-wrap:wrap'>{chips}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.session_state.xp_share_log = None

# ── Data ───────────────────────────────────────────────────────────────────────
with st.spinner("Carregando equipe..."):
    profile            = get_cached_user_profile(user_id)
    team               = get_cached_user_team(user_id)
    team_by_slot       = {m["slot"]: m for m in team}
    xp_share           = get_cached_xp_share_status(user_id)
    team_boost_counts  = get_cached_team_stat_boost_counts(user_id)

# ── Header ─────────────────────────────────────────────────────────────────────
col_title, col_coins = st.columns([3, 1])
with col_title:
    st.markdown("<div class='page-title'>MINHA EQUIPE</div>", unsafe_allow_html=True)
    trainer = profile["username"] if profile else "Treinador"
    xp_share_badge = ""
    if xp_share["active"]:
        xp_share_badge = (
            f" &nbsp;<span style='font-size:0.7rem;background:#0f2030;border:1px solid #58A6FF;"
            f"border-radius:10px;padding:2px 8px;color:#58A6FF;font-weight:700'>"
            f"📡 XP Share · {xp_share['days_left']}d</span>"
        )
    st.markdown(
        f"<div class='page-sub'>Treinador {trainer} · {len(team)}/6 Pokémon{xp_share_badge}</div>",
        unsafe_allow_html=True,
    )
with col_coins:
    coins = profile["coins"] if profile else 0
    st.markdown(
        f"<div style='text-align:right;margin-top:8px'>"
        f"<span class='coins-badge'>🪙 {coins:,} moedas</span></div>",
        unsafe_allow_html=True,
    )

# ── 6 Team slots ───────────────────────────────────────────────────────────────
slot_cols = st.columns(3)
for slot in range(1, 7):
    col    = slot_cols[(slot - 1) % 3]
    member = team_by_slot.get(slot)
    is_sel = st.session_state.sel_team_slot == slot

    with col:
        if member:
            is_main = slot == 1
            if is_sel:
                card_cls = "team-card selected-slot"
                lbl_html = "<div class='sel-label'>▶ Selecionado</div>"
            elif is_main:
                card_cls = "team-card main-slot"
                lbl_html = "<div class='main-label'>★ Principal</div>"
            else:
                card_cls = "team-card"
                lbl_html = f"<div class='slot-label'>Slot {slot}</div>"

            is_shiny   = member.get("is_shiny", False)
            shiny_src  = member.get("sprite_shiny_url") or ""

            # Prefer shiny sprite for shiny Pokémon; fall back to normal sprite with glow
            if is_shiny and shiny_src:
                _sprite_src = shiny_src
                _shiny_style = "display:block;margin:0 auto;filter:drop-shadow(0 0 8px gold) saturate(1.5)"
            else:
                _sprite_src = member.get("sprite_url") or ""
                if not _sprite_src.startswith("http"):
                    _local_thumb = _thumb_path(member["species_id"])
                    _sprite_src = _local_thumb if os.path.isfile(_local_thumb) else _sprite_src
                _shiny_style = ("display:block;margin:0 auto;filter:drop-shadow(0 0 8px gold) saturate(1.5)"
                                if is_shiny else "display:block;margin:0 auto")
            img_tag = (
                sprite_img_tag(_sprite_src, width=72, extra_style=_shiny_style)
                or "<div style='text-align:center;font-size:2.5rem'>❓</div>"
            )

            c1 = get_type_color(member["type1"])
            c2 = get_type_color(member["type2"])
            t1 = (f"<span class='type-sm' style='background:{c1['bg']};color:{c1['text']}'>"
                  f"{member['type1'].upper()}</span>") if member["type1"] else ""
            t2 = (f"<span class='type-sm' style='background:{c2['bg']};color:{c2['text']}'>"
                  f"{member['type2'].upper()}</span>") if member["type2"] else ""

            shiny_badge = (
                "<span style='background:#FFD700;color:#000;font-size:0.55rem;font-weight:800;"
                "padding:1px 6px;border-radius:8px;margin-left:5px;letter-spacing:1px'>✨SHINY</span>"
            ) if is_shiny else ""

            prog     = _xp_progress(member["level"], member["xp"])
            needed   = member["level"] * XP_PER_LV

            member_boost_counts = team_boost_counts.get(member["user_pokemon_id"])
            stat_html = _stat_bars(member, boost_counts=member_boost_counts)
            nature_html = _nature_html(member)

            ability_html = ""
            if slot == 1:
                ability_desc = _get_ability_desc(member.get("ability_slug"))
                if ability_desc:
                    aslug = member["ability_slug"]
                    ability_html = (
                        f"<div style='text-align:center'>"
                        f"<span class='ability-badge'>⚡ {aslug}</span>"
                        f"</div>"
                    )

            poke_name = member['name'].upper()
            species_id = member['species_id']
            level = member['level']
            st.markdown(
                f"<div class='{card_cls}'>{lbl_html}{img_tag}"
                f"<div class='poke-card-name'>#{species_id} {poke_name}{shiny_badge}</div>"
                f"<div style='text-align:center'>{t1}{t2}</div>"
                f"<div style='text-align:center;font-size:0.78rem;color:#8b949e;margin-top:4px'>Lv. {level}</div>"
                f"{nature_html}"
                f"{ability_html}"
                f"<div class='xp-track'><div class='xp-fill' style='width:{prog*100:.0f}%'></div></div>"
                f"<div class='xp-label'>{member['xp']} / {needed} XP</div>"
                f"{stat_html}"
                f"</div>",
                unsafe_allow_html=True,
            )

            b1, b2, b3 = st.columns(3)
            with b1:
                label = "✕ Fechar" if is_sel else "⚔ Golpes"
                if st.button(label, key=f"sel_{slot}", use_container_width=True):
                    st.session_state.sel_team_slot   = None if is_sel else slot
                    st.session_state.replacing_move_id = None
                    st.rerun()
            with b2:
                if slot > 1:
                    if st.button("↑ Main", key=f"promote_{slot}", use_container_width=True):
                        swap_team_slots(user_id, 1, slot)
                        clear_user_cache()
                        if st.session_state.sel_team_slot == slot:
                            st.session_state.sel_team_slot = 1
                        st.session_state.replacing_move_id = None
                        st.rerun()
            with b3:
                if st.button("🗑", key=f"remove_{slot}", use_container_width=True):
                    remove_from_team(user_id, slot)
                    clear_user_cache()
                    if st.session_state.sel_team_slot == slot:
                        st.session_state.sel_team_slot = None
                    st.rerun()
        else:
            st.markdown(
                f"<div class='team-card empty-slot'>"
                f"<div style='text-align:center'>"
                f"<div style='font-size:2rem;opacity:.2'>+</div>"
                f"<div style='color:#8b949e;font-size:0.72rem;margin-top:4px'>Slot {slot} vazio</div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

# ── Move management panel ──────────────────────────────────────────────────────
sel_slot = st.session_state.sel_team_slot
if sel_slot and sel_slot in team_by_slot:
    member        = team_by_slot[sel_slot]
    up_id         = member["user_pokemon_id"]
    species_id    = member["species_id"]
    level         = member["level"]
    active_moves  = get_active_moves(up_id)
    avail_moves   = get_available_moves(species_id, level)
    active_by_slot = {m["slot"]: m for m in active_moves}
    active_ids     = {m["id"] for m in active_moves}
    replacing_id   = st.session_state.replacing_move_id  # move_id waiting to be slotted

    st.markdown(
        f"<div class='move-panel'>"
        f"<div class='move-panel-title'>⚔ GOLPES — {member['name'].upper()} Lv.{level}</div>"
        f"{_nature_html(member, align='flex-start')}"
        f"</div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns([1, 1.6])

    # ── LEFT: active move slots ────────────────────────────────────────────────
    with left:
        st.markdown("<div class='section-lbl'>Golpes Ativos (máx. 4)</div>", unsafe_allow_html=True)

        if replacing_id:
            repl_name = next((m["name"] for m in avail_moves if m["id"] == replacing_id), "?")
            st.warning(f"Escolha o slot para **{repl_name}** ou clique em Cancelar.")
            if st.button("✕ Cancelar substituição", key="cancel_repl"):
                st.session_state.replacing_move_id = None
                st.rerun()

        for s in range(1, 5):
            mv = active_by_slot.get(s)
            is_replace_target = bool(replacing_id)

            if mv:
                tc        = get_type_color(mv["type_name"])
                type_ic   = _type_icon(mv["type_name"])
                dmg_ic    = _dmg_icon(mv["damage_class"])
                pow_str   = str(mv["power"]) if mv["power"] else "—"
                acc_str   = f"{mv['accuracy']}%" if mv["accuracy"] else "—"
                slot_cls  = "move-slot replace-mode" if is_replace_target else "move-slot"

                st.markdown(
                    f"<div class='{slot_cls}' style='border-left:3px solid {tc['bg']}'>"
                    f"<span class='move-slot-num'>{s}</span>"
                    f"<span class='move-slot-name'>{mv['name']}</span>"
                    f"{type_ic}"
                    f"<span class='move-stat'>{pow_str}<span>Pow</span></span>"
                    f"<span class='move-stat'>{acc_str}<span>Acc</span></span>"
                    f"{dmg_ic}</div>",
                    unsafe_allow_html=True,
                )
                btn_c1, btn_c2 = st.columns([1, 1])
                with btn_c1:
                    if is_replace_target:
                        if st.button(f"↩ Slot {s}", key=f"repl_{up_id}_{s}", use_container_width=True):
                            equip_move(up_id, s, replacing_id)
                            st.session_state.replacing_move_id = None
                            st.rerun()
                with btn_c2:
                    if st.button(f"✕", key=f"unequip_{up_id}_{s}", use_container_width=True):
                        unequip_move(up_id, s)
                        st.rerun()
            else:
                slot_cls = "move-slot empty-move replace-mode" if is_replace_target else "move-slot empty-move"
                st.markdown(
                    f"<div class='{slot_cls}'>"
                    f"<span style='font-size:0.7rem;color:#8b949e'>Slot {s} — vazio</span></div>",
                    unsafe_allow_html=True,
                )
                if is_replace_target:
                    if st.button(f"+ Colocar no Slot {s}", key=f"fill_{up_id}_{s}", use_container_width=True):
                        equip_move(up_id, s, replacing_id)
                        st.session_state.replacing_move_id = None
                        st.rerun()

    # ── RIGHT: available moves ─────────────────────────────────────────────────
    with right:
        st.markdown(
            f"<div class='section-lbl'>Golpes Disponíveis — Lv ≤ {level} "
            f"({len(avail_moves)} golpes)</div>",
            unsafe_allow_html=True,
        )

        if not avail_moves:
            st.markdown("<span style='color:#8b949e;font-size:0.85rem'>Nenhum golpe disponível neste nível.</span>",
                        unsafe_allow_html=True)
        else:
            html = "<div class='avail-scroll'>"
            for mv in avail_moves:
                tc       = get_type_color(mv["type_name"])
                type_ic  = _type_icon(mv["type_name"])
                dmg_ic   = _dmg_icon(mv["damage_class"])
                pow_str  = str(mv["power"]) if mv["power"] else "—"
                acc_str  = f"{mv['accuracy']}%" if mv["accuracy"] else "—"
                is_active = mv["id"] in active_ids
                opacity  = "opacity:0.4;" if is_active else ""
                html += (
                    f"<div class='avail-move' style='border-left-color:{tc['bg']};{opacity}'>"
                    f"<span class='avail-move-lv'>Lv.{mv['level_learned_at']}</span>"
                    f"<span class='avail-move-name'>{mv['name']}</span>"
                    f"{type_ic}"
                    f"<span class='move-stat'>{pow_str}<span>Pow</span></span>"
                    f"<span class='move-stat'>{acc_str}<span>Acc</span></span>"
                    f"{dmg_ic}</div>"
                )
            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)

            # Equip buttons rendered below the HTML block (Streamlit constraint)
            st.markdown("<div class='section-lbl' style='margin-top:12px'>Equipar golpe:</div>",
                        unsafe_allow_html=True)
            for mv in avail_moves:
                is_active = mv["id"] in active_ids
                col_name, col_btn = st.columns([3, 1])
                with col_name:
                    tc = get_type_color(mv["type_name"])
                    st.markdown(
                        f"<span style='font-size:0.82rem;color:{'#8b949e' if is_active else '#e6edf3'}'>"
                        f"Lv.{mv['level_learned_at']} {mv['name']}</span>",
                        unsafe_allow_html=True,
                    )
                with col_btn:
                    if is_active:
                        st.markdown("<small style='color:#8b949e'>✓ Ativo</small>", unsafe_allow_html=True)
                    else:
                        free_slot = next((s for s in range(1, 5) if s not in active_by_slot), None)
                        if free_slot:
                            if st.button("+ Equipar", key=f"eq_{up_id}_{mv['id']}", use_container_width=True):
                                equip_move(up_id, free_slot, mv["id"])
                                st.rerun()
                        else:
                            if st.button("↩ Trocar", key=f"repl_init_{up_id}_{mv['id']}", use_container_width=True):
                                st.session_state.replacing_move_id = mv["id"]
                                st.rerun()

# ── Ovos ──────────────────────────────────────────────────────────────────────
eggs = get_user_eggs(user_id)
if eggs:
    st.markdown("<div class='egg-section-title'>🥚 Ovos em Incubação</div>", unsafe_allow_html=True)
    _rarity_emoji = {"common": "⚪", "uncommon": "🔵", "rare": "🟣"}
    egg_cols = st.columns(min(len(eggs), 6))
    for idx, egg in enumerate(eggs):
        col = egg_cols[idx % 6]
        with col:
            rar   = egg["rarity"]
            done  = egg["workouts_done"]
            total = egg["workouts_to_hatch"]
            pct   = min(done / total, 1.0) if total else 1.0
            emoji = _rarity_emoji.get(rar, "⚪")
            st.markdown(
                f"<div class='egg-card rarity-{rar}'>"
                f"<div style='font-size:2.2rem'>🥚</div>"
                f"<div class='egg-rarity {rar}'>{emoji} {rar.upper()}</div>"
                f"<div class='egg-progress-bg'>"
                f"<div class='egg-progress-fill {rar}' style='width:{pct*100:.0f}%'></div>"
                f"</div>"
                f"<div class='egg-remaining'>{done}/{total} treinos</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

# ── Banco de Pokémon ───────────────────────────────────────────────────────────
with st.spinner("Carregando banco..."):
    bench = get_cached_user_bench(user_id)
team_full = len(team) >= 6

st.markdown("<div class='bench-title'>📦 Banco de Pokémon</div>", unsafe_allow_html=True)

if not bench:
    st.markdown(
        "<div style='color:#8b949e;font-size:0.82rem;padding:8px 0 4px'>"
        "Nenhum Pokémon no banco. Pokémons removidos da equipe aparecem aqui.</div>",
        unsafe_allow_html=True,
    )
else:
    if team_full:
        st.caption("⚠️ Equipe cheia — remova um Pokémon da equipe para poder adicionar outro.")

    # Grade responsiva de 6 colunas
    bench_cols = st.columns(6)
    for idx, pk in enumerate(bench):
        col = bench_cols[idx % 6]
        with col:
            _bshiny    = pk.get("is_shiny", False)
            _bshiny_src = pk.get("sprite_shiny_url") or ""
            if _bshiny and _bshiny_src:
                _bsrc = _bshiny_src
                _bstyle = "display:block;margin:0 auto;image-rendering:pixelated;filter:drop-shadow(0 0 6px gold) saturate(1.5)"
            else:
                _bsrc = pk.get("sprite_url") or ""
                if not _bsrc.startswith("http"):
                    _bpath = _thumb_path(pk["species_id"])
                    _bsrc = _bpath if os.path.isfile(_bpath) else _bsrc
                _bstyle = ("display:block;margin:0 auto;image-rendering:pixelated;filter:drop-shadow(0 0 6px gold) saturate(1.5)"
                           if _bshiny else "display:block;margin:0 auto;image-rendering:pixelated")
            img_tag = (
                sprite_img_tag(_bsrc, width=60, extra_style=_bstyle)
                or "<div style='font-size:2rem;text-align:center'>❓</div>"
            )
            c1   = get_type_color(pk["type1"])
            c2   = get_type_color(pk["type2"])
            bg1  = c1["bg"]
            bg2  = c2["bg"] if pk["type2"] else bg1
            t1 = (
                f"<span class='type-sm' style='background:{bg1};color:{c1['text']};font-size:0.5rem'>"
                f"{pk['type1'].upper()}</span>"
            ) if pk["type1"] else ""
            t2 = (
                f"<span class='type-sm' style='background:{bg2};color:{c2['text']};font-size:0.5rem'>"
                f"{pk['type2'].upper()}</span>"
            ) if pk["type2"] else ""

            bench_shiny_badge = (
                "<span style='background:#FFD700;color:#000;font-size:0.48rem;font-weight:800;"
                "padding:1px 4px;border-radius:6px;display:block;text-align:center;"
                "margin-bottom:2px;letter-spacing:1px'>✨ SHINY</span>"
            ) if _bshiny else ""

            stat_html = _stat_bars(pk)
            nature_html = _nature_html(pk, compact=True)
            pk_name_upper = pk['name'].upper()
            pk_level = pk['level']

            st.markdown(
                f"<div class='bench-card'>"
                f"{img_tag}"
                f"{bench_shiny_badge}"
                f"<div class='bench-name'>{pk_name_upper}</div>"
                f"<div class='bench-lv'>Lv. {pk_level}</div>"
                f"{nature_html}"
                f"<div style='text-align:center'>{t1}{t2}</div>"
                f"{stat_html}"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.write("")
            if st.button(
                "→ Equipe",
                key=f"bench_add_{pk['user_pokemon_id']}",
                disabled=team_full,
                use_container_width=True,
            ):
                ok, msg = add_to_team(user_id, pk["user_pokemon_id"])
                clear_user_cache()
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
                st.rerun()

if not team:
    st.markdown(
        "<div style='text-align:center;padding:24px;color:#8b949e'>"
        "<div style='font-size:3rem'>🎮</div>"
        "<div style='font-size:1rem;margin-top:8px'>Equipe vazia — adicione Pokémon do banco acima.</div>"
        "</div>",
        unsafe_allow_html=True,
    )
