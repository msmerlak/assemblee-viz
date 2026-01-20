"""
Optimized data loader using Polars and Parquet caching.
This provides much faster loading compared to JSON caching.
"""

import polars as pl
import time
import json
import zipfile
import io
import requests
from pathlib import Path
from typing import Optional


class OptimizedDataLoader:
    """Fast data loader with Parquet caching and Polars processing"""

    BASE_URL = "https://data.assemblee-nationale.fr/static/openData/repository"
    CACHE_DIR = Path(".cache/parquet_data")
    JSON_CACHE_DIR = Path(".cache/assemblee_data")  # Existing JSON cache
    CACHE_TTL = 86400  # 24 hours

    def __init__(self, legislature: int = 17):
        self.legislature = legislature
        self.session = requests.Session()
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, name: str, limit: Optional[int] = None) -> Path:
        """Generate cache path for processed data"""
        suffix = f"_{limit}" if limit else ""
        return self.CACHE_DIR / f"{self.legislature}_{name}{suffix}.parquet"

    def _get_json_cache_path(self, url: str) -> Path:
        """Get path to existing JSON cache"""
        import hashlib

        url_hash = hashlib.md5(url.encode()).hexdigest()
        return self.JSON_CACHE_DIR / f"{url_hash}.json"

    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cache exists and is fresh"""
        if not cache_path.exists():
            return False
        file_age = time.time() - cache_path.stat().st_mtime
        return file_age < self.CACHE_TTL

    def _load_from_json_cache(self, url: str) -> Optional[list]:
        """Load from existing JSON cache if available (with progress)"""
        json_path = self._get_json_cache_path(url)
        if json_path.exists():
            size_mb = json_path.stat().st_size / (1024 * 1024)
            print(f"Loading from JSON cache: {json_path.name} ({size_mb:.0f} MB)...")
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def _download_zip(self, url: str) -> list:
        """Download and extract ZIP file"""
        print(f"Downloading from: {url}")
        response = self.session.get(url, timeout=120)
        response.raise_for_status()

        data = []
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            for name in zf.namelist():
                if name.endswith(".json"):
                    with zf.open(name) as f:
                        data.append(json.loads(f.read()))
        return data

    def get_amendments_df(self, limit: Optional[int] = None) -> pl.DataFrame:
        """
        Get amendments as a Polars DataFrame with Parquet caching.
        Much faster than JSON for large datasets.

        Args:
            limit: Max number of amendments to process. None = all amendments.
        """
        cache_path = self._get_cache_path("amendments", limit if limit else "all")

        # Try loading from Parquet cache
        if self._is_cache_valid(cache_path):
            print("Loading amendments from Parquet cache...")
            return pl.read_parquet(cache_path)

        # Try existing JSON cache first, then download
        url = f"{self.BASE_URL}/{self.legislature}/loi/amendements_div_legis/Amendements.json.zip"
        print("Fetching amendments data...")

        raw_data = self._load_from_json_cache(url)
        if raw_data is None:
            raw_data = self._download_zip(url)

        # Helper to safely extract string value
        def safe_str(val):
            if val is None:
                return ""
            if isinstance(val, str):
                return val
            if isinstance(val, dict):
                return val.get("#text", val.get("libelle", str(val)))
            return str(val)

        # Process amendments
        items_to_process = raw_data if limit is None else raw_data[:limit]
        print(f"Processing {len(items_to_process)} amendments...")
        amendments = []
        for item in items_to_process:
            if "amendement" not in item:
                continue

            amdt = item["amendement"]
            signataires = amdt.get("signataires", {}) or {}
            auteur = signataires.get("auteur", {}) or {}
            cosignataires = signataires.get("cosignataires", {}) or {}
            cosig_refs = cosignataires.get("acteurRef", [])
            if not isinstance(cosig_refs, list):
                cosig_refs = [cosig_refs] if cosig_refs else []

            cycle = amdt.get("cycleDeVie", {}) or {}
            etat = cycle.get("etatDesTraitements", {})
            if isinstance(etat, dict):
                etat = etat.get("etat", {}) or {}
            else:
                etat = {}

            # sort can be a string or a dict
            sort_raw = cycle.get("sort", "")
            if isinstance(sort_raw, dict):
                sort_libelle = safe_str(sort_raw.get("libelle", ""))
                sort_code = safe_str(sort_raw.get("code", ""))
            else:
                sort_libelle = safe_str(sort_raw)
                sort_code = safe_str(sort_raw)

            amendments.append(
                {
                    "uid": safe_str(amdt.get("uid", "")),
                    "numero": safe_str(
                        amdt.get("identification", {}).get("numeroLong", "")
                    ),
                    "dateDepot": safe_str(cycle.get("dateDepot", "")),
                    "auteur": safe_str(auteur.get("acteurRef", "")),
                    "nombreCosignataires": len(cosig_refs),
                    "etat": (
                        safe_str(etat.get("libelle", ""))
                        if isinstance(etat, dict)
                        else ""
                    ),
                    "etatCode": (
                        safe_str(etat.get("code", "")) if isinstance(etat, dict) else ""
                    ),
                    "sort": sort_libelle,
                    "sortCode": sort_code,
                    "texteLegislatifRef": safe_str(amdt.get("texteLegislatifRef", "")),
                }
            )

        # Create DataFrame and save to Parquet
        df = pl.DataFrame(amendments)

        # Save to Parquet cache
        df.write_parquet(cache_path)
        print(f"Cached {len(df)} amendments to Parquet ({cache_path.name})")

        return df

    def get_deputies_df(self) -> pl.DataFrame:
        """Get deputies as a Polars DataFrame with Parquet caching."""
        cache_path = self._get_cache_path("deputies")

        if self._is_cache_valid(cache_path):
            print("Loading deputies from Parquet cache...")
            return pl.read_parquet(cache_path)

        url = f"{self.BASE_URL}/{self.legislature}/amo/deputes_actifs_mandats_actifs_organes/AMO10_deputes_actifs_mandats_actifs_organes.json.zip"
        print("Fetching deputies data...")

        raw_data = self._load_from_json_cache(url)
        if raw_data is None:
            raw_data = self._download_zip(url)

        # Build organe lookup
        organe_map = {}
        for item in raw_data:
            if "organe" in item:
                organe = item["organe"]
                uid = organe.get("uid", "")
                if uid:
                    organe_map[uid] = organe

        # Process deputies
        deputies = []
        for item in raw_data:
            if "acteur" not in item:
                continue

            acteur = item["acteur"]
            uid = acteur.get("uid", {})
            if isinstance(uid, dict):
                uid = uid.get("#text", "")

            deputy = {
                "uid": uid,
                "civ": acteur.get("etatCivil", {}).get("ident", {}).get("civ", ""),
                "prenom": acteur.get("etatCivil", {})
                .get("ident", {})
                .get("prenom", ""),
                "nom": acteur.get("etatCivil", {}).get("ident", {}).get("nom", ""),
                "profession": acteur.get("profession", {}).get("libelleCourant", ""),
                "groupe_sigle": "",
                "groupe_libelle": "",
                "departement": "",
                "circonscription": "",
            }

            # Extract from mandats
            mandats = acteur.get("mandats", {}).get("mandat", [])
            if not isinstance(mandats, list):
                mandats = [mandats]

            for mandat in mandats:
                type_organe = mandat.get("typeOrgane", "")

                if type_organe == "ASSEMBLEE":
                    election = mandat.get("election", {})
                    lieu = election.get("lieu", {})
                    deputy["departement"] = lieu.get("departement", "")
                    deputy["circonscription"] = lieu.get("numCirco", "")

                elif type_organe == "GP":
                    organe_ref = mandat.get("organes", {}).get("organeRef", "")
                    if organe_ref and organe_ref in organe_map:
                        organe = organe_map[organe_ref]
                        deputy["groupe_sigle"] = organe.get("libelleAbrev", "")
                        deputy["groupe_libelle"] = organe.get("libelle", "")

            deputies.append(deputy)

        df = pl.DataFrame(deputies)
        df = df.with_columns(
            [(pl.col("prenom") + " " + pl.col("nom")).alias("nom_complet")]
        )

        df.write_parquet(cache_path)
        print(f"Cached {len(df)} deputies to Parquet")

        return df

    def get_bills_df(self) -> pl.DataFrame:
        """Get legislative dossiers as a Polars DataFrame with Parquet caching."""
        cache_path = self._get_cache_path("bills")

        if self._is_cache_valid(cache_path):
            print("Loading bills from Parquet cache...")
            return pl.read_parquet(cache_path)

        url = f"{self.BASE_URL}/{self.legislature}/loi/dossiers_legislatifs/Dossiers_Legislatifs.json.zip"
        print("Fetching bills data...")

        raw_data = self._load_from_json_cache(url)
        if raw_data is None:
            raw_data = self._download_zip(url)

        bills = []
        for item in raw_data:
            if "dossierParlementaire" not in item:
                continue

            dossier = item["dossierParlementaire"]
            actes = dossier.get("actesLegislatifs", {}).get("acteLegislatif")

            # Find first date
            date_depot = self._find_first_date(actes)

            # Find last acte for status
            statut = self._find_last_acte(actes)

            procedure = dossier.get("procedureParlementaire", {})
            type_texte = procedure.get("libelle", "")

            bills.append(
                {
                    "uid": dossier.get("uid", ""),
                    "titre": dossier.get("titreDossier", {}).get("titre", ""),
                    "type": type_texte,
                    "date_depot": date_depot.split("T")[0] if date_depot else "",
                    "statut": statut,
                    "legislature": dossier.get("legislature", self.legislature),
                }
            )

        df = pl.DataFrame(bills)

        # Convert date column
        df = df.with_columns(
            [
                pl.col("date_depot")
                .str.to_date(format="%Y-%m-%d", strict=False)
                .alias("date_depot")
            ]
        )

        df.write_parquet(cache_path)
        print(f"Cached {len(df)} bills to Parquet")

        return df

    def get_bills_in_discussion(self, limit: int = 10) -> list:
        """
        Get bills currently being discussed in session.
        Uses the cached bills DataFrame and filters for discussion status.
        """
        df = self.get_bills_df()

        # Filter for bills in discussion (statut contains "séance" or "discussion")
        in_discussion = df.filter(
            pl.col("statut").str.to_lowercase().str.contains("séance|discussion")
        ).head(limit)

        return in_discussion.to_dicts()

    def _find_first_date(self, actes) -> str:
        """Recursively find the first date in legislative acts."""
        if actes is None:
            return ""
        if isinstance(actes, list):
            for acte in actes:
                date = self._find_first_date(acte)
                if date:
                    return date
        elif isinstance(actes, dict):
            if "dateActe" in actes:
                return actes["dateActe"]
            nested = actes.get("actesLegislatifs", {})
            if isinstance(nested, dict):
                nested = nested.get("acteLegislatif")
            return self._find_first_date(nested)
        return ""

    def _find_last_acte(self, actes) -> str:
        """Find the last act name (current status)."""
        if actes is None:
            return ""

        result = []

        def extract(a):
            if isinstance(a, list):
                for item in a:
                    extract(item)
            elif isinstance(a, dict):
                libelle = a.get("libelleActe", {})
                if isinstance(libelle, dict):
                    name = libelle.get("nomCanonique", "") or libelle.get(
                        "libelleCourt", ""
                    )
                    if name:
                        result.append(name)
                nested = a.get("actesLegislatifs", {})
                if isinstance(nested, dict):
                    nested = nested.get("acteLegislatif")
                extract(nested)

        extract(actes)
        return result[-1] if result else ""

    def get_votes_df(self) -> pl.DataFrame:
        """Get votes/scrutins as a Polars DataFrame with Parquet caching."""
        cache_path = self._get_cache_path("votes")

        if self._is_cache_valid(cache_path):
            print("Loading votes from Parquet cache...")
            return pl.read_parquet(cache_path)

        url = f"{self.BASE_URL}/{self.legislature}/loi/scrutins/Scrutins.json.zip"
        print("Fetching votes data...")

        raw_data = self._load_from_json_cache(url)
        if raw_data is None:
            raw_data = self._download_zip(url)

        votes = []
        for item in raw_data:
            if "scrutin" not in item:
                continue

            scrutin = item["scrutin"]
            synthese = scrutin.get("syntheseVote", {})
            decompte = synthese.get("decompte", {})

            votes.append(
                {
                    "uid": scrutin.get("uid", ""),
                    "numero": scrutin.get("numero", ""),
                    "dateScrutin": scrutin.get("dateScrutin", ""),
                    "titre": scrutin.get("titre", ""),
                    "sort": scrutin.get("sort", {}).get("libelle", ""),
                    "nombreVotants": int(synthese.get("nombreVotants", 0)),
                    "pour": int(decompte.get("pour", 0)),
                    "contre": int(decompte.get("contre", 0)),
                    "abstention": int(decompte.get("abstentions", 0)),
                }
            )

        df = pl.DataFrame(votes)
        df.write_parquet(cache_path)
        print(f"Cached {len(df)} votes to Parquet")

        return df

    def get_debates_df(self, limit: Optional[int] = None) -> pl.DataFrame:
        """
        Get debates as a Polars DataFrame with Parquet caching.
        
        Args:
            limit: Max number of debates to return. None = all debates.
        """
        cache_path = self._get_cache_path("debates", limit if limit else "all")

        # Check Parquet cache first
        if self._is_cache_valid(cache_path):
            print("Loading debates from Parquet cache...")
            df = pl.read_parquet(cache_path)
            return df.head(limit) if limit else df

        print("Processing debates data...")
        
        url = f"{self.BASE_URL}/{self.legislature}/vp/syceronbrut/syseron.xml.zip"
        
        # Check for cached ZIP file
        zip_cache_path = self.JSON_CACHE_DIR / f"syseron_{self.legislature}.xml.zip"
        
        if zip_cache_path.exists():
            file_age = time.time() - zip_cache_path.stat().st_mtime
            if file_age < self.CACHE_TTL:
                print("Loading debates from cached ZIP...")
                with open(zip_cache_path, 'rb') as f:
                    zip_content = f.read()
            else:
                zip_content = None
        else:
            zip_content = None
        
        # Download if not cached
        if zip_content is None:
            print("Downloading debates XML (this may take a while)...")
            response = self.session.get(url, timeout=300)
            response.raise_for_status()
            zip_content = response.content
            # Cache for future use
            zip_cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(zip_cache_path, 'wb') as f:
                f.write(zip_content)
            print(f"Cached debates ZIP ({len(zip_content) / 1024 / 1024:.1f} MB)")

        import xml.etree.ElementTree as ET
        
        debates = []
        ns = {"cr": "http://schemas.assemblee-nationale.fr/referentiel"}
        
        with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_file:
            xml_files = [f for f in zip_file.namelist() if f.endswith(".xml")]
            print(f"Processing {len(xml_files)} debate files...")
            
            for file_name in xml_files:
                try:
                    with zip_file.open(file_name) as xml_file:
                        tree = ET.parse(xml_file)
                        root = tree.getroot()
                        
                        meta = root.find("cr:metadonnees", ns)
                        if meta is None:
                            meta = root.find(".//metadonnees")
                        if meta is None:
                            continue
                        
                        date_seance = meta.findtext("cr:dateSeanceJour", "", ns) or meta.findtext("dateSeanceJour", "")
                        num_seance = meta.findtext("cr:numSeance", "", ns) or meta.findtext("numSeance", "")
                        session_txt = meta.findtext("cr:session", "", ns) or meta.findtext("session", "")
                        
                        # Extract sommaire
                        sommaire_items = []
                        sommaire_elem = meta.find("cr:sommaire", ns) or meta.find(".//sommaire")
                        if sommaire_elem is not None:
                            for titre_struct in sommaire_elem.findall(".//cr:titreStruct", ns) or sommaire_elem.findall(".//titreStruct"):
                                intitule = titre_struct.find("cr:intitule", ns) or titre_struct.find("intitule")
                                if intitule is not None and intitule.text:
                                    titre_txt = "".join(intitule.itertext()).strip().replace("\xa0", " ")
                                    if titre_txt and titre_txt != "0":
                                        sommaire_items.append(titre_txt)
                        
                        # Count speakers and paragraphs
                        orateurs_set = set()
                        for orateur in root.findall(".//cr:orateur", ns) or root.findall(".//orateur"):
                            nom = orateur.findtext("cr:nom", "", ns) or orateur.findtext("nom", "")
                            if nom:
                                orateurs_set.add(nom)
                        
                        contenu = root.find("cr:contenu", ns) or root.find(".//contenu")
                        nb_paragraphes = 0
                        if contenu is not None:
                            all_text_elems = contenu.findall(".//cr:texte", ns) or contenu.findall(".//texte")
                            nb_paragraphes = len(all_text_elems)
                        
                        uid = file_name.split("/")[-1].replace(".xml", "")
                        
                        debates.append({
                            "uid": uid,
                            "date": date_seance,
                            "numSeance": num_seance,
                            "session": session_txt,
                            "sommaire": json.dumps(sommaire_items[:10]),  # Store as JSON string for Parquet
                            "nbOrateurs": len(orateurs_set),
                            "nbParagraphes": nb_paragraphes,
                            "legislature": self.legislature,
                        })
                        
                except Exception:
                    continue
        
        df = pl.DataFrame(debates)
        
        # Sort by date descending
        df = df.sort("date", descending=True)
        
        df.write_parquet(cache_path)
        print(f"Cached {len(df)} debates to Parquet")
        
        return df.head(limit) if limit else df

    def get_debates_list(self, limit: Optional[int] = None) -> list:
        """
        Get debates as a list of dicts (for compatibility with existing code).
        Converts sommaire back from JSON string.
        """
        df = self.get_debates_df(limit=limit)
        debates = df.to_dicts()
        
        # Convert sommaire back from JSON string to list
        for d in debates:
            if isinstance(d.get("sommaire"), str):
                try:
                    d["sommaire"] = json.loads(d["sommaire"])
                except Exception:
                    d["sommaire"] = []
        
        return debates

    def compute_activity_stats(
        self, df_deputies: pl.DataFrame, df_amendments: pl.DataFrame
    ) -> pl.DataFrame:
        """
        Compute deputy activity statistics using Polars.
        This is MUCH faster than pandas for this type of aggregation.
        """
        # Add boolean columns for outcomes (vectorized)
        df_amendments = df_amendments.with_columns(
            [
                pl.col("sort").str.contains("(?i)adopté").alias("is_adopted"),
                pl.col("sort").str.contains("(?i)rejet").alias("is_rejected"),
                pl.col("etat").str.contains("(?i)retiré").alias("is_withdrawn"),
                pl.col("etat").str.contains("(?i)irrecevable").alias("is_inadmissible"),
            ]
        )

        # Aggregate by author
        stats = df_amendments.group_by("auteur").agg(
            [
                pl.len().alias("total_amendements"),
                pl.col("is_adopted").sum().alias("adoptes"),
                pl.col("is_rejected").sum().alias("rejetes"),
                pl.col("is_withdrawn").sum().alias("retires"),
                pl.col("is_inadmissible").sum().alias("irrecevables"),
            ]
        )

        # Calculate derived columns
        stats = stats.with_columns(
            [(pl.col("adoptes") + pl.col("rejetes")).alias("examines")]
        ).with_columns(
            [
                (pl.col("adoptes") / pl.col("examines") * 100)
                .fill_null(0)
                .alias("taux_succes")
            ]
        )

        # Join with deputies
        result = df_deputies.join(
            stats, left_on="uid", right_on="auteur", how="inner"
        ).sort("total_amendements", descending=True)

        return result

    def clear_cache(self):
        """Clear Parquet cache"""
        import shutil

        if self.CACHE_DIR.exists():
            shutil.rmtree(self.CACHE_DIR)
            self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
            print("Parquet cache cleared")
