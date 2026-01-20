"""
NLP Analysis for Parliamentary Debates

Provides sentiment analysis, topic modeling, keyword extraction,
and named entity recognition for French parliamentary debates.
"""

import re
from collections import Counter
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json
import hashlib

# French stopwords for keyword extraction
FRENCH_STOPWORDS = {
    "le",
    "la",
    "les",
    "un",
    "une",
    "des",
    "du",
    "de",
    "d",
    "l",
    "à",
    "au",
    "aux",
    "ce",
    "cette",
    "ces",
    "mon",
    "ma",
    "mes",
    "ton",
    "ta",
    "tes",
    "son",
    "sa",
    "ses",
    "notre",
    "nos",
    "votre",
    "vos",
    "leur",
    "leurs",
    "quel",
    "quelle",
    "quels",
    "quelles",
    "et",
    "ou",
    "mais",
    "donc",
    "or",
    "ni",
    "car",
    "que",
    "qui",
    "quoi",
    "dont",
    "où",
    "je",
    "tu",
    "il",
    "elle",
    "on",
    "nous",
    "vous",
    "ils",
    "elles",
    "me",
    "te",
    "se",
    "lui",
    "eux",
    "y",
    "en",
    "moi",
    "toi",
    "soi",
    "celui",
    "celle",
    "ceux",
    "celles",
    "être",
    "avoir",
    "faire",
    "pouvoir",
    "vouloir",
    "devoir",
    "falloir",
    "aller",
    "est",
    "sont",
    "était",
    "étaient",
    "a",
    "ont",
    "avait",
    "avaient",
    "fait",
    "fait",
    "peut",
    "peuvent",
    "veut",
    "veulent",
    "doit",
    "doivent",
    "faut",
    "va",
    "vont",
    "ne",
    "pas",
    "plus",
    "moins",
    "très",
    "bien",
    "mal",
    "peu",
    "beaucoup",
    "trop",
    "tout",
    "tous",
    "toute",
    "toutes",
    "même",
    "autre",
    "autres",
    "aucun",
    "aucune",
    "pour",
    "par",
    "avec",
    "sans",
    "sur",
    "sous",
    "dans",
    "entre",
    "vers",
    "chez",
    "avant",
    "après",
    "pendant",
    "depuis",
    "jusqu",
    "jusque",
    "contre",
    "selon",
    "si",
    "quand",
    "comme",
    "comment",
    "pourquoi",
    "parce",
    "car",
    "donc",
    "alors",
    "ainsi",
    "aussi",
    "encore",
    "déjà",
    "toujours",
    "jamais",
    "souvent",
    "parfois",
    "ici",
    "là",
    "maintenant",
    "hier",
    "aujourd",
    "demain",
    "oui",
    "non",
    "peut-être",
    "cela",
    "ceci",
    "ça",
    "voici",
    "voilà",
    "c",
    "n",
    "s",
    "qu",
    "j",
    "m",
    "t",
    "été",
    "sera",
    "serait",
    "suis",
    "es",
    "sommes",
    "êtes",
    "ai",
    "as",
    "avons",
    "avez",
    "monsieur",
    "madame",
    "mesdames",
    "messieurs",
    "président",
    "présidente",
    "ministre",
    "collègue",
    "collègues",
    "cher",
    "chère",
    "chers",
    "chères",
    "applaudissements",
    "bancs",
    "groupe",
    "exclamations",
    "rires",
}

# Sentiment lexicon for French political discourse
POSITIVE_WORDS = {
    "progrès",
    "amélioration",
    "succès",
    "réussite",
    "efficace",
    "efficacité",
    "soutien",
    "soutenir",
    "favorable",
    "positif",
    "avantage",
    "bénéfice",
    "croissance",
    "développement",
    "opportunité",
    "espoir",
    "confiance",
    "solidarité",
    "justice",
    "équité",
    "liberté",
    "égalité",
    "fraternité",
    "innovation",
    "modernisation",
    "protection",
    "sécurité",
    "stabilité",
    "excellence",
    "qualité",
    "réforme",
    "avancée",
    "victoire",
    "accord",
    "consensus",
    "dialogue",
    "coopération",
    "partenariat",
    "engagement",
    "responsable",
    "responsabilité",
    "transparence",
    "démocratie",
    "républicain",
}

NEGATIVE_WORDS = {
    "problème",
    "crise",
    "échec",
    "difficulté",
    "obstacle",
    "menace",
    "danger",
    "risque",
    "inquiétude",
    "préoccupation",
    "déficit",
    "dette",
    "chômage",
    "pauvreté",
    "inégalité",
    "injustice",
    "discrimination",
    "violence",
    "corruption",
    "scandale",
    "fraude",
    "abus",
    "gaspillage",
    "incompétence",
    "irresponsable",
    "irresponsabilité",
    "opacité",
    "refus",
    "blocage",
    "régression",
    "recul",
    "dégradation",
    "détérioration",
    "catastrophe",
    "désastre",
    "faillite",
    "effondrement",
    "rupture",
    "conflit",
    "tension",
    "opposition",
    "contestation",
    "protestation",
    "grève",
    "manifestation",
    "inacceptable",
    "inadmissible",
    "scandaleux",
    "honteux",
    "grave",
    "urgent",
}

# Political and parliamentary entities
POLITICAL_ENTITIES = {
    "institutions": [
        "Assemblée nationale",
        "Sénat",
        "Gouvernement",
        "Conseil constitutionnel",
        "Conseil d'État",
        "Cour des comptes",
        "Élysée",
        "Matignon",
        "Commission européenne",
        "Parlement européen",
        "Union européenne",
    ],
    "parties": [
        "Renaissance",
        "RN",
        "Rassemblement National",
        "LFI",
        "France Insoumise",
        "LR",
        "Les Républicains",
        "PS",
        "Parti Socialiste",
        "EELV",
        "Écologistes",
        "PCF",
        "Communistes",
        "MoDem",
        "Horizons",
        "LIOT",
        "UDI",
    ],
    "ministries": [
        "Intérieur",
        "Économie",
        "Finances",
        "Éducation",
        "Santé",
        "Travail",
        "Justice",
        "Défense",
        "Affaires étrangères",
        "Transition écologique",
        "Agriculture",
        "Culture",
        "Sports",
        "Logement",
        "Transports",
    ],
}

# Topic keywords for classification
TOPIC_KEYWORDS = {
    "économie": [
        "économie",
        "économique",
        "budget",
        "fiscal",
        "impôt",
        "taxe",
        "dette",
        "déficit",
        "croissance",
        "entreprise",
        "emploi",
        "chômage",
        "inflation",
        "pouvoir d'achat",
        "salaire",
        "retraite",
        "pension",
    ],
    "santé": [
        "santé",
        "hôpital",
        "médecin",
        "soins",
        "maladie",
        "patient",
        "sécurité sociale",
        "assurance maladie",
        "médicament",
        "vaccination",
        "pandémie",
        "covid",
        "épidémie",
        "urgence",
    ],
    "éducation": [
        "éducation",
        "école",
        "enseignant",
        "professeur",
        "élève",
        "étudiant",
        "université",
        "formation",
        "apprentissage",
        "diplôme",
        "baccalauréat",
        "lycée",
        "collège",
        "primaire",
    ],
    "environnement": [
        "environnement",
        "écologie",
        "climat",
        "carbone",
        "énergie",
        "renouvelable",
        "nucléaire",
        "pollution",
        "biodiversité",
        "transition",
        "vert",
        "durable",
        "réchauffement",
    ],
    "sécurité": [
        "sécurité",
        "police",
        "gendarmerie",
        "délinquance",
        "criminalité",
        "terrorisme",
        "attentat",
        "justice",
        "prison",
        "tribunal",
        "violence",
        "ordre",
        "protection",
    ],
    "immigration": [
        "immigration",
        "migrant",
        "étranger",
        "asile",
        "frontière",
        "régularisation",
        "intégration",
        "nationalité",
        "visa",
        "clandestin",
        "expulsion",
        "accueil",
    ],
    "social": [
        "social",
        "solidarité",
        "aide",
        "allocation",
        "RSA",
        "logement",
        "pauvreté",
        "précarité",
        "exclusion",
        "insertion",
        "famille",
        "handicap",
        "dépendance",
        "EHPAD",
    ],
    "international": [
        "international",
        "européen",
        "Europe",
        "diplomatie",
        "traité",
        "accord",
        "guerre",
        "paix",
        "défense",
        "armée",
        "OTAN",
        "ONU",
        "bilatéral",
        "coopération",
    ],
    "agriculture": [
        "agriculture",
        "agriculteur",
        "paysan",
        "exploitation",
        "PAC",
        "pesticide",
        "bio",
        "élevage",
        "culture",
        "rural",
        "alimentation",
        "agroalimentaire",
    ],
    "numérique": [
        "numérique",
        "digital",
        "internet",
        "données",
        "cybersécurité",
        "intelligence artificielle",
        "IA",
        "startup",
        "innovation",
        "technologie",
        "plateforme",
        "algorithme",
    ],
}


class DebateAnalyzer:
    """
    NLP Analyzer for French Parliamentary Debates

    Provides:
    - Sentiment analysis
    - Topic detection
    - Keyword extraction
    - Named entity recognition
    - Speaker analysis
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize the analyzer with optional cache directory."""
        self.cache_dir = cache_dir or Path("cache/nlp")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Compile regex patterns
        self._word_pattern = re.compile(
            r"\b[a-zA-ZàâäéèêëïîôùûüÿœæçÀÂÄÉÈÊËÏÎÔÙÛÜŸŒÆÇ-]+\b", re.UNICODE
        )
        self._sentence_pattern = re.compile(r"[.!?]+")

    def _get_cache_key(self, text: str) -> str:
        """Generate a cache key for text."""
        return hashlib.md5(text.encode()).hexdigest()

    def _load_from_cache(self, key: str, analysis_type: str) -> Optional[Dict]:
        """Load analysis result from cache."""
        cache_file = self.cache_dir / f"{analysis_type}_{key}.json"
        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def _save_to_cache(self, key: str, analysis_type: str, data: Dict):
        """Save analysis result to cache."""
        cache_file = self.cache_dir / f"{analysis_type}_{key}.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    def tokenize(self, text: str) -> List[str]:
        """Tokenize text into words."""
        text = text.lower()
        words = self._word_pattern.findall(text)
        return [w for w in words if len(w) > 2 and w not in FRENCH_STOPWORDS]

    def analyze_sentiment(self, text: str) -> Dict:
        """
        Analyze sentiment of text using lexicon-based approach.

        Returns:
            Dict with sentiment score, positive/negative word counts,
            and overall classification.
        """
        words = self.tokenize(text)
        word_set = set(words)

        positive_matches = word_set & POSITIVE_WORDS
        negative_matches = word_set & NEGATIVE_WORDS

        positive_count = sum(1 for w in words if w in POSITIVE_WORDS)
        negative_count = sum(1 for w in words if w in NEGATIVE_WORDS)

        total = positive_count + negative_count
        if total == 0:
            score = 0.0
            label = "neutre"
        else:
            score = (positive_count - negative_count) / total
            if score > 0.2:
                label = "positif"
            elif score < -0.2:
                label = "négatif"
            else:
                label = "neutre"

        return {
            "score": round(score, 3),
            "label": label,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "positive_words": list(positive_matches),
            "negative_words": list(negative_matches),
        }

    def extract_keywords(self, text: str, top_n: int = 20) -> List[Tuple[str, int]]:
        """
        Extract top keywords from text using frequency analysis.

        Returns:
            List of (keyword, count) tuples sorted by frequency.
        """
        words = self.tokenize(text)
        # Filter out very common parliamentary words
        parliamentary_common = {
            "article",
            "amendement",
            "alinéa",
            "vote",
            "séance",
            "texte",
        }
        words = [w for w in words if w not in parliamentary_common]

        counter = Counter(words)
        return counter.most_common(top_n)

    def detect_topics(self, text: str) -> Dict[str, float]:
        """
        Detect topics in text based on keyword matching.

        Returns:
            Dict mapping topic names to relevance scores (0-1).
        """
        text_lower = text.lower()
        words = set(self.tokenize(text))

        topic_scores = {}
        for topic, keywords in TOPIC_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in text_lower or kw in words)
            # Normalize by number of keywords
            score = min(matches / (len(keywords) * 0.3), 1.0)
            if score > 0.1:
                topic_scores[topic] = round(score, 3)

        # Sort by score
        return dict(sorted(topic_scores.items(), key=lambda x: x[1], reverse=True))

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract named entities from text.

        Returns:

            Dict with entity types and their occurrences.
        """
        entities = {
            "institutions": [],
            "parties": [],
            "ministries": [],
            "laws": [],
            "dates": [],
        }

        text_lower = text.lower()

        # Match predefined entities
        for entity_type, entity_list in POLITICAL_ENTITIES.items():
            for entity in entity_list:
                if entity.lower() in text_lower:
                    entities[entity_type].append(entity)

        # Extract law references (e.g., "loi n° 2024-123", "article L. 123-45")
        law_patterns = [
            r"loi\s+n[°o]\s*\d{4}-\d+",
            r"article\s+L\.?\s*\d+(?:-\d+)*",
            r"décret\s+n[°o]\s*\d{4}-\d+",
            r"ordonnance\s+n[°o]\s*\d{4}-\d+",
        ]
        for pattern in law_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities["laws"].extend(matches)

        # Extract dates
        date_patterns = [
            r"\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4}",
            r"\d{1,2}/\d{1,2}/\d{4}",
        ]
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities["dates"].extend(matches)

        # Remove duplicates
        for key in entities:
            entities[key] = list(set(entities[key]))

        return entities

    def analyze_speaker(self, interventions: List[Dict]) -> Dict:
        """
        Analyze a speaker's interventions.

        Args:
            interventions: List of dicts with 'texte' key

        Returns:
            Analysis of speaking patterns.
        """
        if not interventions:
            return {}

        all_text = " ".join(i.get("texte", "") for i in interventions)

        # Basic stats
        word_count = len(all_text.split())
        sentence_count = len(self._sentence_pattern.split(all_text))

        # Sentiment
        sentiment = self.analyze_sentiment(all_text)

        # Topics
        topics = self.detect_topics(all_text)

        # Keywords
        keywords = self.extract_keywords(all_text, top_n=10)

        return {
            "nb_interventions": len(interventions),
            "total_words": word_count,
            "avg_words_per_intervention": round(word_count / len(interventions), 1),
            "total_sentences": sentence_count,
            "sentiment": sentiment,
            "top_topics": dict(list(topics.items())[:5]),
            "top_keywords": keywords,
        }

    def analyze_debate(self, paragraphes: List[Dict], use_cache: bool = True) -> Dict:
        """
        Full analysis of a debate.

        Args:
            paragraphes: List of dicts with 'orateur' and 'texte' keys
            use_cache: Whether to use cached results

        Returns:
            Comprehensive debate analysis.
        """
        # Combine all text
        all_text = " ".join(p.get("texte", "") for p in paragraphes)

        # Check cache
        if use_cache:
            cache_key = self._get_cache_key(
                all_text[:1000]
            )  # Use first 1000 chars for key
            cached = self._load_from_cache(cache_key, "debate")
            if cached:
                return cached

        # Overall stats
        word_count = len(all_text.split())

        # Overall sentiment
        sentiment = self.analyze_sentiment(all_text)

        # Topics
        topics = self.detect_topics(all_text)

        # Keywords
        keywords = self.extract_keywords(all_text, top_n=30)

        # Entities
        entities = self.extract_entities(all_text)

        # Per-speaker analysis
        speakers = {}
        for p in paragraphes:
            orateur = p.get("orateur", "").strip()
            if (
                orateur
                and orateur != "M. le président"
                and orateur != "Mme la présidente"
            ):
                if orateur not in speakers:
                    speakers[orateur] = []
                speakers[orateur].append(p)

        speaker_analyses = {}
        for speaker, interventions in sorted(
            speakers.items(), key=lambda x: len(x[1]), reverse=True
        )[:20]:
            speaker_analyses[speaker] = self.analyze_speaker(interventions)

        # Sentiment timeline (divide into chunks)
        chunk_size = max(len(paragraphes) // 10, 1)
        sentiment_timeline = []
        for i in range(0, len(paragraphes), chunk_size):
            chunk = paragraphes[i : i + chunk_size]
            chunk_text = " ".join(p.get("texte", "") for p in chunk)
            chunk_sentiment = self.analyze_sentiment(chunk_text)
            sentiment_timeline.append(
                {
                    "position": i / len(paragraphes),
                    "score": chunk_sentiment["score"],
                    "label": chunk_sentiment["label"],
                }
            )

        result = {
            "stats": {
                "total_words": word_count,
                "total_paragraphs": len(paragraphes),
                "unique_speakers": len(speakers),
            },
            "sentiment": sentiment,
            "sentiment_timeline": sentiment_timeline,
            "topics": topics,
            "keywords": keywords,
            "entities": entities,
            "speaker_analyses": speaker_analyses,
        }

        # Save to cache
        if use_cache:
            self._save_to_cache(cache_key, "debate", result)

        return result

    def compare_debates(self, debates: List[Dict]) -> Dict:
        """
        Compare multiple debates.

        Args:
            debates: List of debate analysis results

        Returns:
            Comparison metrics.
        """
        if not debates:
            return {}

        # Aggregate topics
        topic_counts = Counter()
        for d in debates:
            for topic in d.get("topics", {}).keys():
                topic_counts[topic] += 1

        # Average sentiment
        sentiments = [d.get("sentiment", {}).get("score", 0) for d in debates]
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0

        # Sentiment distribution
        sentiment_dist = Counter(
            d.get("sentiment", {}).get("label", "neutre") for d in debates
        )

        # Most common keywords across all debates
        keyword_counts = Counter()
        for d in debates:
            for kw, count in d.get("keywords", []):
                keyword_counts[kw] += count

        return {
            "total_debates": len(debates),
            "avg_sentiment": round(avg_sentiment, 3),
            "sentiment_distribution": dict(sentiment_dist),
            "topic_frequency": dict(topic_counts.most_common(10)),
            "common_keywords": keyword_counts.most_common(20),
        }

    def get_topic_summary(self, text: str, topic: str) -> Dict:
        """
        Get analysis focused on a specific topic.

        Args:
            text: The debate text
            topic: Topic name from TOPIC_KEYWORDS

        Returns:
            Topic-specific analysis.
        """
        if topic not in TOPIC_KEYWORDS:
            return {"error": f"Unknown topic: {topic}"}

        keywords = TOPIC_KEYWORDS[topic]

        # Find sentences containing topic keywords
        sentences = re.split(r"[.!?]+", text)
        relevant_sentences = []
        for sent in sentences:
            sent_lower = sent.lower()
            if any(kw in sent_lower for kw in keywords):
                relevant_sentences.append(sent.strip())

        # Analyze just the relevant content
        relevant_text = " ".join(relevant_sentences)

        return {
            "topic": topic,
            "keywords_found": [kw for kw in keywords if kw in text.lower()],
            "relevant_sentences": len(relevant_sentences),
            "sample_sentences": relevant_sentences[:5],
            "sentiment": (
                self.analyze_sentiment(relevant_text) if relevant_text else None
            ),
        }
