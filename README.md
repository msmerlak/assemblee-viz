# Assemblée Nationale - Visualisations

Une application web interactive pour explorer et visualiser le travail législatif de l'Assemblée Nationale française.

## Fonctionnalités

### 👥 Députés
- Liste complète des députés avec informations détaillées
- Répartition par groupe politique et département
- Analyse de la parité femmes-hommes
- Statistiques démographiques
- Recherche et filtrage avancés

### 📜 Législation
- Vue d'ensemble des dossiers législatifs
- Classification par type de texte
- Suivi chronologique des dépôts
- Analyse des statuts
- Export des données en CSV

### 🗳️ Scrutins
- Historique complet des votes
- Analyse des résultats (adoptés/rejetés)
- Statistiques de participation
- Évolution temporelle des scrutins
- Répartition détaillée des votes (pour/contre/abstentions)

## Installation

### Prérequis
- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)

### Étape 1: Créer un environnement virtuel

```bash
# Créer l'environnement virtuel
python3 -m venv venv

# Activer l'environnement virtuel
# Sur macOS/Linux:
source venv/bin/activate

# Sur Windows:
# venv\Scripts\activate
```

### Étape 2: Installer les dépendances

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Étape 3 (Optionnel mais recommandé): Pré-charger les données

Pour des performances optimales, pré-chargez les données en cache:
```bash
python cache_manager.py warm --legislature 17
```

Cette étape télécharge toutes les données une fois (~740 MB). Les prochains lancements seront **20x plus rapides** !

## Utilisation

### Lancer l'application

```bash
# S'assurer que l'environnement virtuel est activé
source venv/bin/activate  # ou venv\Scripts\activate sur Windows

# Lancer l'application
streamlit run app.py
```

L'application sera accessible à l'adresse : `http://localhost:8501`

### Navigation

L'application utilise une structure multi-pages :
- **Page d'accueil** : Vue d'ensemble et statistiques rapides
- **Députés** : Visualisations et analyses des députés
- **Législation** : Exploration des dossiers législatifs
- **Scrutins** : Analyse des votes

Utilisez le menu de navigation dans la barre latérale ou les boutons de la page d'accueil pour accéder aux différentes sections.

### Gestion du cache

L'application utilise un système de cache local pour des performances optimales (20x plus rapide) :

```bash
# Voir les informations du cache
python cache_manager.py info

# Vider le cache (pour forcer le téléchargement de nouvelles données)
python cache_manager.py clear

# Pré-charger toutes les données
python cache_manager.py warm --legislature 17
```

Le cache expire automatiquement après 24 heures. Voir `CACHING_SYSTEM.md` pour plus de détails.

## Structure du projet

```
assemblee-viz/
├── app.py                          # Application principale
├── requirements.txt                # Dépendances Python
├── README.md                       # Ce fichier
│
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   └── assemblee_client.py    # Client API Assemblée Nationale
│   │
│   └── utils/
│       ├── __init__.py
│       └── data_processing.py     # Fonctions de traitement des données
│
└── pages/
    ├── 1_Députés.py               # Page des députés
    ├── 2_Législation.py           # Page de la législation
    └── 3_Scrutins.py              # Page des scrutins
```

## Source des données

Les données proviennent de l'API officielle de l'Assemblée Nationale :
- **URL** : https://data.assemblee-nationale.fr/
- **Format** : JSON
- **Mise à jour** : Régulière

L'application utilise un système de cache pour optimiser les performances et réduire les requêtes API.

## Fonctionnalités techniques

### Cache des données
- Durée de vie du cache : 1 heure (3600 secondes)
- Réduction de la charge sur l'API
- Amélioration des performances de l'application

### Visualisations interactives
- Graphiques réalisés avec Plotly
- Tableaux de données avec Pandas
- Interface responsive adaptée aux différents écrans

### Export de données
- Téléchargement des données filtrées en CSV
- Formats prêts pour l'analyse externe

## Configuration

### Sélection de la législature

La législature peut être modifiée dans la barre latérale de l'application.
Législatures disponibles :
- **17** : Législature actuelle (2024-)
- **16** : Législature précédente (2022-2024)
- **15** : Législature 2017-2022

### Limite de chargement

Pour les pages Législation et Scrutins, vous pouvez ajuster le nombre d'éléments chargés via les contrôles de la barre latérale :
- Minimum : 50 éléments
- Maximum : 500 éléments
- Par défaut : 200 éléments

## Développement

### Ajouter une nouvelle page

1. Créer un nouveau fichier dans le dossier `pages/` avec le préfixe numérique (ex: `4_Nouvelle_Page.py`)
2. Importer les modules nécessaires
3. Utiliser `st.set_page_config()` pour configurer la page
4. Implémenter la logique et les visualisations

### Ajouter un nouvel endpoint API

1. Ouvrir `src/api/assemblee_client.py`
2. Ajouter une nouvelle méthode dans la classe `AssembleeNationaleAPI`
3. Documenter les paramètres et le retour attendu

### Ajouter une fonction de traitement

1. Ouvrir `src/utils/data_processing.py`
2. Créer une nouvelle fonction avec docstring
3. L'exporter dans `src/utils/__init__.py`

## Dépendances principales

- **streamlit** : Framework web pour l'application
- **pandas** : Manipulation et analyse de données
- **plotly** : Visualisations interactives
- **requests** : Requêtes HTTP vers l'API

## Licence

Ce projet utilise des données publiques fournies par l'Assemblée Nationale française.

## Support

Pour toute question ou problème :
- Consulter la documentation de l'API : https://data.assemblee-nationale.fr/
- Vérifier les issues sur le dépôt du projet

## Améliorations futures

Fonctionnalités potentielles à développer :
- Analyse des amendements
- Visualisations des débats parlementaires
- Comparaisons inter-législatures
- Analyse des thématiques par traitement du langage naturel
- Export de rapports PDF
- Filtres de dates avancés
- Graphiques de réseau des co-signatures
