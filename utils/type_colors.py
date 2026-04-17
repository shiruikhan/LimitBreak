TYPE_COLORS: dict[str, dict[str, str]] = {
    "normal":   {"bg": "#A8A878", "light": "#C6C6A7", "dark": "#6D6D4E", "text": "#fff"},
    "fire":     {"bg": "#F08030", "light": "#F5AC78", "dark": "#9C531F", "text": "#fff"},
    "water":    {"bg": "#6890F0", "light": "#9DB7F5", "dark": "#445E9C", "text": "#fff"},
    "electric": {"bg": "#F8D030", "light": "#FAE078", "dark": "#A1871F", "text": "#333"},
    "grass":    {"bg": "#78C850", "light": "#A7DB8D", "dark": "#4E8234", "text": "#fff"},
    "ice":      {"bg": "#98D8D8", "light": "#BCE6E6", "dark": "#638D8D", "text": "#333"},
    "fighting": {"bg": "#C03028", "light": "#D67873", "dark": "#7D1F1A", "text": "#fff"},
    "poison":   {"bg": "#A040A0", "light": "#C183C1", "dark": "#682A68", "text": "#fff"},
    "ground":   {"bg": "#E0C068", "light": "#EBD69D", "dark": "#927D44", "text": "#333"},
    "flying":   {"bg": "#A890F0", "light": "#C6B7F5", "dark": "#6D5E9C", "text": "#fff"},
    "psychic":  {"bg": "#F85888", "light": "#FA92B2", "dark": "#A13959", "text": "#fff"},
    "bug":      {"bg": "#A8B820", "light": "#C6D16E", "dark": "#6D7815", "text": "#fff"},
    "rock":     {"bg": "#B8A038", "light": "#D1C17D", "dark": "#786824", "text": "#fff"},
    "ghost":    {"bg": "#705898", "light": "#A292BC", "dark": "#493963", "text": "#fff"},
    "dragon":   {"bg": "#7038F8", "light": "#A27DFA", "dark": "#4924A1", "text": "#fff"},
    "dark":     {"bg": "#705848", "light": "#A29288", "dark": "#49392F", "text": "#fff"},
    "steel":    {"bg": "#B8B8D0", "light": "#D1D1E0", "dark": "#787887", "text": "#333"},
    "fairy":    {"bg": "#EE99AC", "light": "#F4BDC9", "dark": "#9B6470", "text": "#333"},
}

_DEFAULT = {"bg": "#68A090", "light": "#8FC6B5", "dark": "#436B5E", "text": "#fff"}


def get_type_color(type_name: str | None) -> dict[str, str]:
    if not type_name:
        return _DEFAULT
    return TYPE_COLORS.get(type_name.lower(), _DEFAULT)
