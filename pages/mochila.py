import streamlit as st

from utils.bag_ui import (
    ensure_bag_session_state,
    render_bag_header,
    render_bag_styles,
    render_bag_view,
)


if not st.session_state.get("user"):
    st.warning("Faça login para acessar esta página.")
    st.stop()

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Sessão inválida. Faça login novamente.")
    st.stop()

ensure_bag_session_state()
render_bag_styles()
render_bag_header(show_shop_button=True)
render_bag_view(user_id)
