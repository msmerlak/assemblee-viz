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

from src.api import AssembleeNationaleAPI


@st.cache_data(ttl=3600, show_spinner=False)
def load_homepage_stats(legislature):
    """Load basic stats for homepage - just counts, not all data"""
    api = AssembleeNationaleAPI(legislature=legislature)
    deputies = api.get_deputies()
    # For homepage we just need the count, load a sample for speed
    votes = api.get_votes(limit=100)
    return deputies, votes, api.get_vote_count()


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

# Main content
st.markdown("## Bienvenue")

st.markdown(
    """
Cette application vous permet d'explorer et de visualiser le travail législatif 
à l'Assemblée Nationale française.

### Fonctionnalités principales
"""
)

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 👥 Députés")
    st.markdown(
        """
    - Liste complète des députés
    - Répartition par groupe politique
    - Statistiques démographiques
    - Analyse par département
    """
    )

with col2:
    st.markdown("### 📊 Activité des Députés")
    st.markdown(
        """
    - Nombre d'amendements par député
    - Taux de succès des amendements
    - Analyse par groupe politique
    - Classements et statistiques
    """
    )

col3, col4 = st.columns(2)

with col3:
    st.markdown("### 📜 Législation")
    st.markdown(
        """
    - Dossiers législatifs
    - Projets et propositions de loi
    - Suivi du processus législatif
    - Analyse des thématiques
    """
    )

with col4:
    st.markdown("### 🗳️ Scrutins")
    st.markdown(
        """
    - Liste des votes
    - Résultats détaillés
    - Analyse des tendances
    - Participation
    """
    )

st.divider()

# Quick statistics
st.markdown("## Statistiques rapides")

with st.spinner("Chargement des données..."):
    try:
        deputies, votes, total_votes = load_homepage_stats(legislature)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                label="Nombre de députés", value=len(deputies) if deputies else "—"
            )

        with col2:
            groups = set()
            for dep in deputies or []:
                if isinstance(dep.get("groupe"), dict):
                    sigle = dep["groupe"].get("sigle", "")
                    if sigle:
                        groups.add(sigle)
            st.metric(label="Groupes politiques", value=len(groups) if groups else "—")

        with col3:
            st.metric(label="Scrutins", value=total_votes if total_votes else "—")
    except Exception as e:
        st.error(f"Erreur lors du chargement des statistiques: {str(e)}")

st.divider()

st.markdown(
    """
### Source des données

Les données proviennent de l'API officielle de l'Assemblée Nationale:
[data.assemblee-nationale.fr](https://data.assemblee-nationale.fr/)
"""
)
