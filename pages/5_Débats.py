"""
Page de visualisation des débats en séance publique avec analyse NLP
"""

import streamlit as st
from src.api import AssembleeNationaleAPI
from src.utils.data_loader import OptimizedDataLoader
from src.nlp import DebateAnalyzer

st.set_page_config(
    page_title="Débats - Assemblée Nationale",
    page_icon="🎤",
    layout="wide",
)

st.title("🎤 Débats en séance publique")
st.markdown("Compte-rendus des séances de l'Assemblée Nationale avec analyse NLP")


# Initialize NLP analyzer
@st.cache_resource
def get_analyzer():
    return DebateAnalyzer()


analyzer = get_analyzer()

# Sidebar
with st.sidebar:
    legislature = st.selectbox(
        "Législature",
        options=[17, 16, 15],
        index=0,
        help="Sélectionnez la législature",
    )

    st.divider()

    analysis_mode = st.radio(
        "Mode d'affichage",
        options=["📋 Liste des débats", "🔬 Analyse NLP"],
        index=0,
    )

    st.divider()

    st.info(
        """
    **Analyse NLP disponible:**
    - Analyse de sentiment
    - Détection de thèmes
    - Extraction de mots-clés
    - Entités nommées
    - Analyse par orateur
    """
    )


@st.cache_data(ttl=3600, show_spinner="Chargement des débats...")
def load_debates(legislature):
    """Load debates data"""
    loader = OptimizedDataLoader(legislature=legislature)
    return loader.get_debates_list()


@st.cache_data(ttl=3600, show_spinner="Chargement du texte intégral...")
def load_debate_text(debate_uid, legislature):
    """Load full debate text"""
    api = AssembleeNationaleAPI(legislature=legislature)
    return api.get_debate_full_text(debate_uid, legislature)


def render_sentiment_badge(sentiment: dict) -> str:
    """Render a sentiment badge."""
    label = sentiment.get("label", "neutre")
    score = sentiment.get("score", 0)

    if label == "positif":
        return f"🟢 Positif ({score:+.2f})"
    elif label == "négatif":
        return f"🔴 Négatif ({score:+.2f})"
    else:
        return f"🟡 Neutre ({score:+.2f})"


def render_topic_tags(topics: dict) -> None:
    """Render topic tags."""
    if not topics:
        st.caption("Aucun thème détecté")
        return

    topic_icons = {
        "économie": "💰",
        "santé": "🏥",
        "éducation": "📚",
        "environnement": "🌱",
        "sécurité": "🔒",
        "immigration": "🌍",
        "social": "🤝",
        "international": "🌐",
        "agriculture": "🌾",
        "numérique": "💻",
    }

    tags = []
    for topic, score in list(topics.items())[:5]:
        icon = topic_icons.get(topic, "📌")
        tags.append(f"{icon} {topic.capitalize()} ({score:.0%})")

    st.markdown(" • ".join(tags))


def render_keyword_cloud(keywords: list) -> None:
    """Render keywords as a simple visualization."""
    if not keywords:
        return

    # Create a simple frequency display
    max_count = keywords[0][1] if keywords else 1

    html_parts = []
    for word, count in keywords[:15]:
        size = 14 + int((count / max_count) * 16)
        opacity = 0.5 + (count / max_count) * 0.5
        html_parts.append(
            f'<span style="font-size:{size}px;opacity:{opacity};margin:3px;display:inline-block">{word}</span>'
        )

    st.markdown(
        f'<div style="line-height:2.5">{"  ".join(html_parts)}</div>',
        unsafe_allow_html=True,
    )


# Load data
try:
    with st.spinner("Chargement des débats..."):
        debates = load_debates(legislature)

    if not debates:
        st.warning("Aucun débat trouvé pour cette législature.")
        st.stop()

    # Stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Séances", len(debates))
    with col2:
        total_speakers = sum(d.get("nbOrateurs", 0) for d in debates)
        st.metric("Interventions totales", f"{total_speakers:,}")
    with col3:
        total_paragraphs = sum(d.get("nbParagraphes", 0) for d in debates)
        st.metric("Paragraphes", f"{total_paragraphs:,}")

    st.divider()

    # =====================
    # LIST MODE
    # =====================
    if analysis_mode == "📋 Liste des débats":
        # Search and filter
        col1, col2 = st.columns([2, 1])

        with col1:
            search_query = st.text_input(
                "🔍 Rechercher dans les titres",
                placeholder="ex: budget, immigration, santé...",
            )

        with col2:
            # Get unique sessions
            sessions = sorted(
                set(d.get("session", "") for d in debates if d.get("session"))
            )
            selected_session = st.selectbox(
                "Session",
                options=["Toutes"] + sessions,
                index=0,
            )

        # Filter debates
        filtered_debates = debates

        if search_query:
            search_lower = search_query.lower()
            filtered_debates = [
                d
                for d in filtered_debates
                if any(search_lower in titre.lower() for titre in d.get("sommaire", []))
                or search_lower in d.get("preview", "").lower()
            ]

        if selected_session != "Toutes":
            filtered_debates = [
                d for d in filtered_debates if d.get("session") == selected_session
            ]

        st.markdown(f"**{len(filtered_debates)}** séances trouvées")

        st.divider()

        # Display debates
        for debate in filtered_debates[:50]:  # Show first 50
            uid = debate.get("uid", "")
            date = debate.get("date", "Date inconnue")
            num_seance = debate.get("numSeance", "")
            session = debate.get("session", "")
            sommaire = debate.get("sommaire", [])
            nb_orateurs = debate.get("nbOrateurs", 0)
            nb_paragraphes = debate.get("nbParagraphes", 0)
            preview = debate.get("preview", "")

            with st.container():
                col1, col2 = st.columns([4, 1])

                with col1:
                    st.markdown(f"### 📅 {date}")
                    if num_seance:
                        st.caption(f"Séance n°{num_seance} • {session}")

                with col2:
                    if st.button("🔬 Analyser", key=f"analyze_{uid}", type="secondary"):
                        st.session_state.selected_debate = uid
                        st.session_state.analysis_mode = "🔬 Analyse NLP"
                        st.rerun()

                # Sommaire (agenda)
                if sommaire:
                    st.markdown("**Ordre du jour:**")
                    for i, titre in enumerate(sommaire[:5], 1):
                        st.markdown(f"- {titre}")
                    if len(sommaire) > 5:
                        st.caption(f"... et {len(sommaire) - 5} autres points")

                # Stats
                col1, col2 = st.columns(2)
                with col1:
                    st.caption(f"👥 {nb_orateurs} intervenants")
                with col2:
                    st.caption(f"📝 {nb_paragraphes} paragraphes")

                # Preview with quick sentiment
                if preview:
                    with st.expander("Aperçu et analyse rapide"):
                        st.markdown(f"*{preview}...*")

                        # Quick sentiment analysis of preview
                        quick_sentiment = analyzer.analyze_sentiment(preview)
                        quick_topics = analyzer.detect_topics(preview)

                        st.markdown("---")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(
                                f"**Sentiment:** {render_sentiment_badge(quick_sentiment)}"
                            )
                        with col2:
                            if quick_topics:
                                top_topic = list(quick_topics.keys())[0]
                                st.markdown(
                                    f"**Thème principal:** {top_topic.capitalize()}"
                                )

                st.markdown("---")

        if len(filtered_debates) > 50:
            st.info(
                f"Affichage limité aux 50 premières séances. {len(filtered_debates) - 50} autres disponibles."
            )

    # =====================
    # NLP ANALYSIS MODE
    # =====================
    else:
        st.subheader("🔬 Analyse NLP des débats")

        # Debate selector
        debate_options = {
            f"{d.get('date', 'N/A')} - {(d.get('sommaire') or ['Sans titre'])[0][:50]}...": d.get(
                "uid"
            )
            for d in debates[:100]
        }

        # Check if a debate was selected from list mode
        default_index = 0
        if hasattr(st.session_state, "selected_debate"):
            for i, (label, uid) in enumerate(debate_options.items()):
                if uid == st.session_state.selected_debate:
                    default_index = i
                    break

        selected_label = st.selectbox(
            "Sélectionner un débat à analyser",
            options=list(debate_options.keys()),
            index=default_index,
        )

        selected_uid = debate_options[selected_label]

        if st.button("🚀 Lancer l'analyse complète", type="primary"):
            with st.spinner("Chargement du texte intégral du débat..."):
                debate_text = load_debate_text(selected_uid, legislature)

            if debate_text and debate_text.get("paragraphes"):
                paragraphes = debate_text["paragraphes"]

                with st.spinner("Analyse NLP en cours..."):
                    analysis = analyzer.analyze_debate(paragraphes)

                # Store in session
                st.session_state.current_analysis = analysis
                st.session_state.current_paragraphes = paragraphes
                st.success(
                    f"Analyse terminée! {analysis['stats']['total_words']:,} mots analysés."
                )
            else:
                st.error("Impossible de charger le texte du débat.")

        # Display analysis if available
        if hasattr(st.session_state, "current_analysis"):
            analysis = st.session_state.current_analysis

            st.divider()

            # Overview metrics
            st.subheader("📊 Vue d'ensemble")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Mots", f"{analysis['stats']['total_words']:,}")
            with col2:
                st.metric("Paragraphes", f"{analysis['stats']['total_paragraphs']:,}")
            with col3:
                st.metric("Orateurs", analysis["stats"]["unique_speakers"])
            with col4:
                sentiment = analysis["sentiment"]
                st.metric(
                    "Sentiment",
                    sentiment["label"].capitalize(),
                    delta=f"{sentiment['score']:+.2f}",
                )

            st.divider()

            # Tabs for different analyses
            tab1, tab2, tab3, tab4, tab5 = st.tabs(
                [
                    "😊 Sentiment",
                    "📌 Thèmes",
                    "🔑 Mots-clés",
                    "🏛️ Entités",
                    "👥 Orateurs",
                ]
            )

            with tab1:
                st.subheader("Analyse de sentiment")

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown(f"### {render_sentiment_badge(analysis['sentiment'])}")
                    st.markdown(
                        f"""
                    - **Mots positifs:** {analysis['sentiment']['positive_count']}
                    - **Mots négatifs:** {analysis['sentiment']['negative_count']}
                    """
                    )

                    if analysis["sentiment"]["positive_words"]:
                        st.markdown(
                            "**Exemples positifs:** "
                            + ", ".join(analysis["sentiment"]["positive_words"][:10])
                        )
                    if analysis["sentiment"]["negative_words"]:
                        st.markdown(
                            "**Exemples négatifs:** "
                            + ", ".join(analysis["sentiment"]["negative_words"][:10])
                        )

                with col2:
                    st.markdown("### Évolution du sentiment")

                    # Create sentiment timeline chart
                    timeline = analysis.get("sentiment_timeline", [])
                    if timeline:
                        import plotly.graph_objects as go

                        fig = go.Figure()
                        positions = [t["position"] * 100 for t in timeline]
                        scores = [t["score"] for t in timeline]
                        colors = [
                            "green" if s > 0.1 else "red" if s < -0.1 else "gray"
                            for s in scores
                        ]

                        fig.add_trace(
                            go.Scatter(
                                x=positions,
                                y=scores,
                                mode="lines+markers",
                                marker=dict(color=colors, size=10),
                                line=dict(color="lightgray"),
                                fill="tozeroy",
                                fillcolor="rgba(100,100,100,0.1)",
                            )
                        )

                        fig.add_hline(y=0, line_dash="dash", line_color="gray")
                        fig.update_layout(
                            xaxis_title="Progression du débat (%)",
                            yaxis_title="Score de sentiment",
                            yaxis=dict(range=[-1, 1]),
                            height=300,
                            margin=dict(l=20, r=20, t=20, b=40),
                        )
                        st.plotly_chart(fig, use_container_width=True)

            with tab2:
                st.subheader("Thèmes détectés")

                topics = analysis.get("topics", {})
                if topics:
                    import plotly.express as px

                    # Bar chart of topics
                    topic_names = list(topics.keys())
                    topic_scores = list(topics.values())

                    fig = px.bar(
                        x=topic_scores,
                        y=topic_names,
                        orientation="h",
                        labels={"x": "Score de pertinence", "y": "Thème"},
                        color=topic_scores,
                        color_continuous_scale="Viridis",
                    )
                    fig.update_layout(
                        height=400,
                        showlegend=False,
                        yaxis={"categoryorder": "total ascending"},
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Topic details
                    st.markdown("### Détail par thème")

                    selected_topic = st.selectbox(
                        "Explorer un thème", options=list(topics.keys())
                    )

                    if selected_topic and hasattr(
                        st.session_state, "current_paragraphes"
                    ):
                        all_text = " ".join(
                            p.get("texte", "")
                            for p in st.session_state.current_paragraphes
                        )
                        topic_detail = analyzer.get_topic_summary(
                            all_text, selected_topic
                        )

                        st.markdown(
                            f"**Mots-clés trouvés:** {', '.join(topic_detail.get('keywords_found', []))}"
                        )
                        st.markdown(
                            f"**Phrases pertinentes:** {topic_detail.get('relevant_sentences', 0)}"
                        )

                        if topic_detail.get("sample_sentences"):
                            st.markdown("**Extraits:**")
                            for sent in topic_detail["sample_sentences"][:3]:
                                st.markdown(f"> {sent[:200]}...")
                else:
                    st.info("Aucun thème majeur détecté dans ce débat.")

            with tab3:
                st.subheader("Mots-clés extraits")

                keywords = analysis.get("keywords", [])
                if keywords:
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.markdown("### Nuage de mots")
                        render_keyword_cloud(keywords)

                    with col2:
                        st.markdown("### Top 15")
                        for i, (word, count) in enumerate(keywords[:15], 1):
                            st.markdown(f"{i}. **{word}** ({count})")
                else:
                    st.info("Pas assez de contenu pour extraire des mots-clés.")

            with tab4:
                st.subheader("Entités nommées")

                entities = analysis.get("entities", {})

                col1, col2 = st.columns(2)

                with col1:
                    if entities.get("institutions"):
                        st.markdown("### 🏛️ Institutions")
                        for e in entities["institutions"]:
                            st.markdown(f"- {e}")

                    if entities.get("parties"):
                        st.markdown("### 🗳️ Partis politiques")
                        for e in entities["parties"]:
                            st.markdown(f"- {e}")

                with col2:
                    if entities.get("ministries"):
                        st.markdown("### 🏢 Ministères")
                        for e in entities["ministries"]:
                            st.markdown(f"- {e}")

                    if entities.get("laws"):
                        st.markdown("### 📜 Références légales")
                        for e in entities["laws"][:10]:
                            st.markdown(f"- {e}")

                if entities.get("dates"):
                    st.markdown("### 📅 Dates mentionnées")
                    st.markdown(", ".join(entities["dates"][:10]))

            with tab5:
                st.subheader("Analyse par orateur")

                speaker_analyses = analysis.get("speaker_analyses", {})

                if speaker_analyses:
                    # Overview chart
                    speakers = list(speaker_analyses.keys())[:10]
                    interventions = [
                        speaker_analyses[s]["nb_interventions"] for s in speakers
                    ]
                    sentiments = [
                        speaker_analyses[s]["sentiment"]["score"] for s in speakers
                    ]

                    import plotly.graph_objects as go

                    fig = go.Figure()

                    colors = [
                        "green" if s > 0.1 else "red" if s < -0.1 else "gray"
                        for s in sentiments
                    ]

                    fig.add_trace(
                        go.Bar(
                            x=speakers,
                            y=interventions,
                            marker_color=colors,
                            text=[f"{s:+.2f}" for s in sentiments],
                            textposition="outside",
                            name="Interventions",
                        )
                    )

                    fig.update_layout(
                        title="Top 10 intervenants (couleur = sentiment)",
                        xaxis_title="Orateur",
                        yaxis_title="Nombre d'interventions",
                        xaxis_tickangle=-45,
                        height=400,
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Detailed speaker analysis
                    st.markdown("### Détail par orateur")

                    selected_speaker = st.selectbox(
                        "Sélectionner un orateur", options=list(speaker_analyses.keys())
                    )

                    if selected_speaker:
                        sa = speaker_analyses[selected_speaker]

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Interventions", sa["nb_interventions"])
                        with col2:
                            st.metric("Mots total", f"{sa['total_words']:,}")
                        with col3:
                            st.metric(
                                "Mots/intervention", sa["avg_words_per_intervention"]
                            )

                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(
                                f"**Sentiment:** {render_sentiment_badge(sa['sentiment'])}"
                            )
                        with col2:
                            if sa["top_topics"]:
                                st.markdown("**Thèmes abordés:**")
                                render_topic_tags(sa["top_topics"])

                        if sa["top_keywords"]:
                            st.markdown("**Mots-clés:**")
                            kw_str = ", ".join(
                                [f"{w} ({c})" for w, c in sa["top_keywords"][:10]]
                            )
                            st.markdown(kw_str)
                else:
                    st.info("Aucune donnée d'orateur disponible.")

except Exception as e:
    st.error(f"Erreur lors du chargement des débats: {str(e)}")
    st.exception(e)
