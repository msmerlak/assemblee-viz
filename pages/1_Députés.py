"""
Deputies (Députés) visualization page
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.utils.data_loader import OptimizedDataLoader
from src.utils import calculate_deputy_statistics

st.set_page_config(
    page_title="Députés - Assemblée Nationale",
    page_icon="👥",
    layout="wide"
)

# Initialize loader
legislature = 17

st.title("👥 Députés de l'Assemblée Nationale")
st.markdown(f"**Législature**: {legislature}")

# Load data
@st.cache_data(ttl=3600)
def load_deputies(legislature):
    """Load deputies data with Parquet caching"""
    loader = OptimizedDataLoader(legislature=legislature)
    df = loader.get_deputies_df()
    return df.to_pandas(), df.to_dicts()

with st.spinner("Chargement des données des députés..."):
    try:
        df_deputies, raw_deputies = load_deputies(legislature)

        if df_deputies.empty:
            st.warning("Aucune donnée disponible pour cette législature.")
            st.stop()

        # Calculate statistics
        stats = calculate_deputy_statistics(df_deputies)

        # Display key metrics
        st.markdown("## Statistiques générales")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Nombre total de députés", stats.get('total_deputies', 0))

        with col2:
            if 'average_age' in stats:
                st.metric("Âge moyen", f"{stats['average_age']} ans")

        with col3:
            if stats.get('by_gender'):
                gender_counts = stats['by_gender']
                women_count = gender_counts.get('F', 0)
                st.metric("Femmes députées", women_count)

        with col4:
            st.metric("Groupes politiques", len(stats.get('by_group', {})))

        st.divider()

        # Create tabs for different visualizations
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Répartition par groupe",
            "🚻 Parité",
            "🗺️ Par département",
            "📋 Liste complète"
        ])

        with tab1:
            st.markdown("### Répartition des députés par groupe politique")

            if stats.get('by_group'):
                # Prepare data for visualization
                group_data = pd.DataFrame([
                    {'Groupe': k, 'Nombre': v}
                    for k, v in stats['by_group'].items()
                ]).sort_values('Nombre', ascending=False)

                col1, col2 = st.columns([2, 1])

                with col1:
                    # Bar chart
                    fig = px.bar(
                        group_data,
                        x='Nombre',
                        y='Groupe',
                        orientation='h',
                        title="Nombre de députés par groupe politique",
                        color='Nombre',
                        color_continuous_scale='Blues'
                    )
                    fig.update_layout(height=500, showlegend=False)
                    st.plotly_chart(fig, width="stretch")

                with col2:
                    # Pie chart
                    fig = px.pie(
                        group_data,
                        values='Nombre',
                        names='Groupe',
                        title="Proportions"
                    )
                    st.plotly_chart(fig, width="stretch")

                # Display table
                st.dataframe(
                    group_data.style.format({'Nombre': '{:,.0f}'}),
                    width="stretch",
                    hide_index=True
                )
            else:
                st.info("Données de groupe non disponibles")

        with tab2:
            st.markdown("### Parité femmes-hommes")

            if stats.get('by_gender'):
                gender_data = pd.DataFrame([
                    {'Sexe': 'Femmes' if k == 'F' else 'Hommes', 'Nombre': v}
                    for k, v in stats['by_gender'].items()
                ])

                col1, col2 = st.columns([1, 1])

                with col1:
                    # Pie chart
                    fig = px.pie(
                        gender_data,
                        values='Nombre',
                        names='Sexe',
                        title="Répartition par sexe",
                        color='Sexe',
                        color_discrete_map={'Femmes': '#ff7f0e', 'Hommes': '#1f77b4'}
                    )
                    st.plotly_chart(fig, width="stretch")

                with col2:
                    # Calculate percentages
                    total = gender_data['Nombre'].sum()
                    gender_data['Pourcentage'] = (gender_data['Nombre'] / total * 100).round(1)

                    st.markdown("#### Détails")
                    for _, row in gender_data.iterrows():
                        st.metric(
                            label=row['Sexe'],
                            value=f"{row['Nombre']} députés",
                            delta=f"{row['Pourcentage']}%"
                        )

                # Display table
                st.dataframe(
                    gender_data.style.format({'Nombre': '{:,.0f}', 'Pourcentage': '{:.1f}%'}),
                    width="stretch",
                    hide_index=True
                )
            else:
                st.info("Données de sexe non disponibles")

        with tab3:
            st.markdown("### Répartition par département")

            if 'departement' in df_deputies.columns:
                dept_counts = df_deputies['departement'].value_counts().head(20)
                dept_data = pd.DataFrame({
                    'Département': dept_counts.index,
                    'Nombre': dept_counts.values
                })

                # Bar chart
                fig = px.bar(
                    dept_data,
                    x='Nombre',
                    y='Département',
                    orientation='h',
                    title="Top 20 départements par nombre de députés",
                    color='Nombre',
                    color_continuous_scale='Greens'
                )
                fig.update_layout(height=600, showlegend=False)
                st.plotly_chart(fig, width="stretch")

                # Display full table
                with st.expander("Voir tous les départements"):
                    all_dept = df_deputies['departement'].value_counts().reset_index()
                    all_dept.columns = ['Département', 'Nombre']
                    st.dataframe(all_dept, width="stretch", hide_index=True)
            else:
                st.info("Données de département non disponibles")

        with tab4:
            st.markdown("### Liste complète des députés")

            # Add search and filter options
            col1, col2 = st.columns([2, 1])

            with col1:
                search_term = st.text_input(
                    "Rechercher un député",
                    placeholder="Nom, prénom, département..."
                )

            with col2:
                if 'groupe_sigle' in df_deputies.columns:
                    groups = ['Tous'] + sorted(df_deputies['groupe_sigle'].dropna().unique().tolist())
                    selected_group = st.selectbox("Filtrer par groupe", groups)
                else:
                    selected_group = 'Tous'

            # Apply filters
            filtered_df = df_deputies.copy()

            if search_term:
                mask = (
                    filtered_df['nom_complet'].str.contains(search_term, case=False, na=False) |
                    filtered_df['departement'].str.contains(search_term, case=False, na=False) |
                    filtered_df['groupe'].str.contains(search_term, case=False, na=False)
                )
                filtered_df = filtered_df[mask]

            if selected_group != 'Tous':
                filtered_df = filtered_df[filtered_df['groupe_sigle'] == selected_group]

            # Display results count
            st.caption(f"Affichage de {len(filtered_df)} députés sur {len(df_deputies)}")

            # Select columns to display
            display_columns = ['nom_complet', 'sexe', 'departement', 'circonscription', 'groupe_sigle', 'profession']
            available_columns = [col for col in display_columns if col in filtered_df.columns]

            if available_columns:
                # Rename columns for better display
                column_names = {
                    'nom_complet': 'Nom',
                    'sexe': 'Sexe',
                    'departement': 'Département',
                    'circonscription': 'Circonscription',
                    'groupe_sigle': 'Groupe',
                    'profession': 'Profession'
                }

                display_df = filtered_df[available_columns].rename(columns=column_names)

                st.dataframe(
                    display_df,
                    width="stretch",
                    hide_index=True,
                    height=600
                )

                # Download button
                csv = display_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Télécharger les données (CSV)",
                    data=csv,
                    file_name=f"deputes_legislature_{legislature}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("Aucune colonne à afficher")

    except Exception as e:
        st.error(f"Erreur lors du chargement des données: {str(e)}")
        st.exception(e)
