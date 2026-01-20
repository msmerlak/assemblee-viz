"""
Main Streamlit application for Assemblée Nationale visualization
"""

import streamlit as st

st.set_page_config(
    page_title="Assemblée Nationale - Visualisations",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src.utils.data_loader import OptimizedDataLoader


@st.cache_data(ttl=3600, show_spinner=False)
def load_homepage_data(legislature):
    """Load all data for homepage"""
    loader = OptimizedDataLoader(legislature=legislature)
    df_deputies = loader.get_deputies_df()
    df_amendments = loader.get_amendments_df(limit=None)
    df_stats = loader.compute_activity_stats(df_deputies, df_amendments)
    return df_deputies, df_amendments, df_stats


@st.cache_data(ttl=3600, show_spinner=False)
def load_bills_in_discussion(legislature):
    """Load bills currently being discussed"""
    loader = OptimizedDataLoader(legislature=legislature)
    return loader.get_bills_in_discussion(limit=5)


@st.cache_data(ttl=3600, show_spinner=False)
def load_recent_debates(legislature):
    """Load recent debates"""
    loader = OptimizedDataLoader(legislature=legislature)
    return loader.get_debates_list(limit=3)


# Custom CSS
st.markdown(
    """
<style>
.main-header {
    font-size: 3rem;
    font-weight: bold;
    color: #1f77b4;
    text-align: center;
    margin-bottom: 2rem;
}
.subtitle {
    font-size: 1.2rem;
    text-align: center;
    color: #666;
    margin-bottom: 3rem;
}
</style>
""",
    unsafe_allow_html=True,
)

# Main header
st.markdown(
    '<div class="main-header">🏛️ Assemblée Nationale</div>', unsafe_allow_html=True
)
st.markdown(
    '<div class="subtitle">Visualisations du travail législatif français</div>',
    unsafe_allow_html=True,
)

# Sidebar
with st.sidebar:
    st.title("Navigation")
    st.info(
        """
    Explorez les différentes facettes du travail législatif:
    
    - **Députés**: Informations et statistiques
    - **Activité**: Métriques de succès et amendements
    - **Législation**: Projets et propositions de loi
    - **Scrutins**: Analyse des votes
    """
    )

    st.divider()

    legislature = st.selectbox(
        "Législature",
        options=[17, 16, 15],
        index=0,
        help="Sélectionnez la législature à explorer",
    )

    st.divider()

    st.markdown(
        """
    ### À propos
    
    **Source des données**: [data.assemblee-nationale.fr](https://data.assemblee-nationale.fr/)
    """
    )

# Main content - Quick statistics
st.markdown("## 📊 En chiffres")

try:
    df_deputies, df_amendments, df_stats = load_homepage_data(legislature)

    # Build deputy lookup for author names
    deputy_lookup = {}
    for row in df_deputies.to_dicts():
        uid = row.get("uid", "")
        nom = (
            row.get("nom_complet", "")
            or f"{row.get('prenom', '')} {row.get('nom', '')}"
        )
        groupe = row.get("groupe_sigle", "")
        if uid:
            deputy_lookup[uid] = {"nom": nom.strip(), "groupe": groupe}

    # Calculate stats
    total_deputies = len(df_deputies)
    total_amendments = len(df_amendments)
    groups = df_deputies["groupe_sigle"].unique().to_list()
    total_groups = len([g for g in groups if g])

    # Success rate
    adopted = df_amendments.filter(
        df_amendments["sort"].str.contains("(?i)adopt")
    ).height
    examined = df_amendments.filter(
        df_amendments["sort"].str.contains("(?i)adopt|rejet")
    ).height
    success_rate = (adopted / examined * 100) if examined > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Députés", f"{total_deputies:,}")
    with col2:
        st.metric("Amendements", f"{total_amendments:,}")
    with col3:
        st.metric("Groupes politiques", total_groups)
    with col4:
        st.metric("Taux d'adoption", f"{success_rate:.1f}%")

except Exception as e:
    st.error(f"Erreur lors du chargement: {str(e)}")
    df_stats = None
    deputy_lookup = {}

st.divider()

# Most active/successful MP
st.markdown("## 🏆 Député le plus actif")

try:
    if df_stats is not None and not df_stats.is_empty():
        top = df_stats.row(0, named=True)

        col1, col2 = st.columns([1, 2])

        with col1:
            st.markdown(f"### {top.get('nom_complet', 'N/A')}")
            groupe = top.get("groupe_sigle", "")
            if groupe:
                st.caption(f"Groupe: **{groupe}**")

        with col2:
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Amendements", top.get("total_amendements", 0))
            with m2:
                st.metric("Adoptés", top.get("adoptes", 0))
            with m3:
                st.metric("Taux de succès", f"{top.get('taux_succes', 0):.1f}%")

        # Top 5 table
        with st.expander("Voir le Top 5"):
            top5 = (
                df_stats.head(5)
                .select(
                    [
                        "nom_complet",
                        "groupe_sigle",
                        "total_amendements",
                        "adoptes",
                        "taux_succes",
                    ]
                )
                .to_pandas()
            )
            top5.columns = ["Député", "Groupe", "Amendements", "Adoptés", "Taux (%)"]
            st.dataframe(top5, hide_index=True, width="stretch")
    else:
        st.info("Chargement des statistiques d'activité...")
except Exception as e:
    st.warning(f"Statistiques d'activité non disponibles: {e}")

st.divider()

# Bills in discussion
st.markdown("## 📜 Textes en cours de discussion")

try:
    bills_in_discussion = load_bills_in_discussion(legislature)

    if bills_in_discussion:
        for bill in bills_in_discussion[:5]:
            titre = bill.get("titre", "Sans titre")
            type_texte = bill.get("type", "")
            statut = bill.get("statut", "")
            uid = bill.get("uid", "")
            acteur_ref = bill.get("acteurRef")
            leg = bill.get("legislature", legislature)

            # Get author name
            author_name = None
            if acteur_ref and acteur_ref in deputy_lookup:
                author_info = deputy_lookup[acteur_ref]
                author_name = author_info.get("nom")
                author_groupe = author_info.get("groupe", "")

            url = f"https://www.assemblee-nationale.fr/dyn/{leg}/dossiers/{uid}"

            with st.container():
                st.markdown(
                    f"**[{titre[:80]}{'...' if len(titre) > 80 else ''}]({url})**"
                )

                col1, col2, col3 = st.columns([2, 2, 2])
                with col1:
                    st.caption(f"📋 {type_texte}" if type_texte else "")
                with col2:
                    st.caption(f"📍 {statut}" if statut else "")
                with col3:
                    if author_name:
                        st.caption(
                            f"👤 {author_name}"
                            + (f" ({author_groupe})" if author_groupe else "")
                        )
                    else:
                        st.caption("👤 Gouvernement" if not acteur_ref else "")

                st.markdown("---")
    else:
        st.info("Aucun texte en cours de discussion en séance publique.")

except Exception as e:
    st.warning(f"Impossible de charger les textes en discussion: {e}")

st.divider()

# Navigation links
st.markdown("## 🔍 Explorer")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.page_link("pages/1_Députés.py", label="Députés", icon="👥")
    st.caption("Profils et groupes")

with col2:
    st.page_link("pages/4_Activité.py", label="Activité", icon="📊")
    st.caption("Amendements et succès")

with col3:
    st.page_link("pages/2_Législation.py", label="Législation", icon="📜")
    st.caption("Tous les dossiers")

with col4:
    st.page_link("pages/3_Scrutins.py", label="Scrutins", icon="🗳️")
    st.caption("Votes et résultats")

with col5:
    st.page_link("pages/5_Débats.py", label="Débats", icon="🎤")
    st.caption("Séances publiques")

st.divider()

# Recent debates section
st.markdown("## 🎤 Dernières séances")

try:
    recent_debates = load_recent_debates(legislature)

    if recent_debates:
        for debate in recent_debates:
            date = debate.get("date", "Date inconnue")
            sommaire = debate.get("sommaire", [])
            nb_orateurs = debate.get("nbOrateurs", 0)

            with st.container():
                st.markdown(f"**📅 {date}**")

                if sommaire:
                    # Show first 2 agenda items
                    for titre in sommaire[:2]:
                        st.caption(f"• {titre[:60]}{'...' if len(titre) > 60 else ''}")

                st.caption(f"👥 {nb_orateurs} intervenants")
                st.markdown("---")

        st.page_link("pages/5_Débats.py", label="Voir tous les débats →", icon="🎤")
    else:
        st.info("Aucun débat récent disponible.")

except Exception as e:
    st.warning(f"Impossible de charger les débats récents: {e}")

st.divider()

st.markdown(
    """
<div style="text-align: center; color: #888; font-size: 0.9rem;">
    Données: <a href="https://data.assemblee-nationale.fr/" target="_blank">Assemblée Nationale Open Data</a>
</div>
""",
    unsafe_allow_html=True,
)
