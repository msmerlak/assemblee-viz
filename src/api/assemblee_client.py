"""
Client for the Assemblée Nationale Open Data
Documentation: https://data.assemblee-nationale.fr/
Note: Data is provided as downloadable ZIP files containing JSON, not as a REST API
"""

import requests
import json
import zipfile
import io
import os
import hashlib
import time
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
from pathlib import Path


class AssembleeNationaleAPI:
    """Client for interacting with the Assemblée Nationale Open Data"""

    BASE_URL = "https://data.assemblee-nationale.fr/static/openData/repository"
    CACHE_DIR = Path(".cache/assemblee_data")
    CACHE_TTL = 86400  # 24 hours in seconds

    def __init__(self, legislature: int = 17, use_cache: bool = True):
        """
        Initialize the API client

        Args:
            legislature: Legislature number (default: 17 for current legislature)
            use_cache: Whether to use local file caching (default: True)
        """
        self.legislature = legislature
        self.use_cache = use_cache
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

        # Create cache directory
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, url: str) -> Path:
        """Generate a cache file path for a URL"""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return self.CACHE_DIR / f"{url_hash}.json"

    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cache file exists and is not expired"""
        if not cache_path.exists():
            return False

        # Check age
        file_age = time.time() - cache_path.stat().st_mtime
        return file_age < self.CACHE_TTL

    def _load_from_cache(self, cache_path: Path) -> Optional[List[Dict]]:
        """Load data from cache file"""
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Cache load failed: {e}")
            return None

    def _save_to_cache(self, cache_path: Path, data: List[Dict]) -> None:
        """Save data to cache file"""
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception as e:
            print(f"Cache save failed: {e}")

    def _download_and_extract_zip(self, url: str) -> List[Dict]:
        """
        Download a ZIP file and extract JSON files (with caching)

        Args:
            url: URL to the ZIP file

        Returns:
            List of parsed JSON objects
        """
        # Check cache first
        if self.use_cache:
            cache_path = self._get_cache_path(url)
            if self._is_cache_valid(cache_path):
                print(f"Loading from cache: {cache_path.name}")
                cached_data = self._load_from_cache(cache_path)
                if cached_data is not None:
                    return cached_data

        # Download if not in cache or cache invalid
        try:
            print(f"Downloading from: {url}")
            response = self.session.get(url, timeout=60)
            response.raise_for_status()

            # Extract ZIP in memory
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
                data = []
                for file_name in zip_file.namelist():
                    if file_name.endswith(".json"):
                        with zip_file.open(file_name) as json_file:
                            content = json_file.read()
                            data.append(json.loads(content))

            # Save to cache
            if self.use_cache and data:
                cache_path = self._get_cache_path(url)
                self._save_to_cache(cache_path, data)
                print(f"Saved to cache: {cache_path.name}")

            return data

        except requests.exceptions.RequestException as e:
            print(f"Download failed: {e}")
            return []
        except Exception as e:
            print(f"Extraction failed: {e}")
            return []

    def get_deputies(self, legislature: Optional[int] = None) -> List[Dict]:
        """
        Get list of active deputies (députés)

        Args:
            legislature: Legislature number (uses instance default if not provided)

        Returns:
            List of deputy data dictionaries
        """
        leg = legislature or self.legislature

        # URL for active deputies with active mandates
        url = f"{self.BASE_URL}/{leg}/amo/deputes_actifs_mandats_actifs_organes/AMO10_deputes_actifs_mandats_actifs_organes.json.zip"

        print(f"Fetching deputies data...")
        raw_data = self._download_and_extract_zip(url)

        # Build organe lookup from the ZIP file
        organe_map = {}
        for item in raw_data:
            if "organe" in item:
                organe = item["organe"]
                uid = organe.get("uid", "")
                if uid:
                    organe_map[uid] = organe

        print(f"Loaded {len(organe_map)} organes")

        # Extract and simplify the structure
        deputies = []
        for item in raw_data:
            if "acteur" in item:
                acteur = item["acteur"]

                # Extract basic info
                deputy_info = {
                    "uid": acteur.get("uid", {}).get("#text", acteur.get("uid", "")),
                    "civ": acteur.get("etatCivil", {}).get("ident", {}).get("civ", ""),
                    "prenom": acteur.get("etatCivil", {})
                    .get("ident", {})
                    .get("prenom", ""),
                    "nom": acteur.get("etatCivil", {}).get("ident", {}).get("nom", ""),
                    "dateNaissance": acteur.get("etatCivil", {})
                    .get("infoNaissance", {})
                    .get("dateNais", ""),
                    "lieuNaissance": acteur.get("etatCivil", {})
                    .get("infoNaissance", {})
                    .get("villeNais", ""),
                    "profession": acteur.get("profession", {}).get(
                        "libelleCourant", ""
                    ),
                    "sexe": (
                        "F"
                        if acteur.get("etatCivil", {}).get("ident", {}).get("civ", "")
                        == "Mme"
                        else "M"
                    ),
                }

                # Extract mandates to find current info
                mandats = acteur.get("mandats", {}).get("mandat", [])
                if not isinstance(mandats, list):
                    mandats = [mandats]

                # Find deputy mandate and group
                for mandat in mandats:
                    type_organe = mandat.get("typeOrgane", "")

                    if type_organe == "ASSEMBLEE":
                        # Assembly mandate has election/circonscription info
                        election = mandat.get("election", {})
                        lieu = election.get("lieu", {})
                        deputy_info["circonscription"] = {
                            "numero": lieu.get("numCirco", "")
                        }
                        deputy_info["departement"] = {
                            "nom": lieu.get("departement", ""),
                            "numero": lieu.get("numDepartement", ""),
                        }

                    elif type_organe == "GP":
                        # Political group
                        organe_ref = mandat.get("organes", {}).get("organeRef", "")
                        if organe_ref and organe_ref in organe_map:
                            organe = organe_map[organe_ref]
                            deputy_info["groupe"] = {
                                "sigle": organe.get("libelleAbrev", ""),
                                "libelle": organe.get("libelle", ""),
                            }

                deputies.append(deputy_info)

        print(f"Loaded {len(deputies)} deputies")
        return deputies

    def get_deputy_details(self, deputy_uid: str) -> Dict:
        """
        Get detailed information about a specific deputy
        Note: This would require individual file access

        Args:
            deputy_uid: Unique identifier for the deputy

        Returns:
            Deputy details dictionary
        """
        # For now, return empty as individual access requires different approach
        return {}

    def _find_first_date(self, actes) -> str:
        """Recursively find the first date in nested actesLegislatifs"""
        if isinstance(actes, dict):
            date = actes.get("dateActe")
            if date:
                return date
            nested = actes.get("actesLegislatifs", {})
            if nested:
                return self._find_first_date(nested.get("acteLegislatif"))
        elif isinstance(actes, list):
            for a in actes:
                d = self._find_first_date(a)
                if d:
                    return d
        return ""

    def _find_last_acte(self, actes, result=None) -> str:
        """Recursively find the last acte (current stage) in nested actesLegislatifs"""
        if result is None:
            result = []
        if isinstance(actes, dict):
            libelle = actes.get("libelleActe", {})
            if isinstance(libelle, dict):
                libelle = libelle.get("nomCanonique", "") or libelle.get(
                    "libelleCourt", ""
                )
            if libelle:
                result.append(libelle)
            nested = actes.get("actesLegislatifs", {})
            if nested:
                self._find_last_acte(nested.get("acteLegislatif"), result)
        elif isinstance(actes, list):
            for a in actes:
                self._find_last_acte(a, result)
        return result[-1] if result else ""

    def get_bills(
        self, legislature: Optional[int] = None, limit: int = 100
    ) -> List[Dict]:
        """
        Get list of legislative dossiers

        Args:
            legislature: Legislature number (uses instance default if not provided)
            limit: Maximum number of results (not applicable for file downloads)

        Returns:
            List of bill data dictionaries
        """
        leg = legislature or self.legislature

        # URL for legislative dossiers
        url = f"{self.BASE_URL}/{leg}/loi/dossiers_legislatifs/Dossiers_Legislatifs.json.zip"

        print(f"Fetching legislative dossiers...")
        raw_data = self._download_and_extract_zip(url)

        bills = []
        items_to_process = raw_data if limit is None else raw_data[:limit]
        for item in items_to_process:
            if "dossierParlementaire" in item:
                dossier = item["dossierParlementaire"]

                # Extract date from nested actesLegislatifs
                actes = dossier.get("actesLegislatifs", {}).get("acteLegislatif")
                date_depot = self._find_first_date(actes)

                # Get procedure type (e.g., "Proposition de loi ordinaire")
                procedure = dossier.get("procedureParlementaire", {})
                type_texte = procedure.get("libelle", "")

                # Get current stage from last acte (e.g., "Renvoi en commission")
                statut = self._find_last_acte(actes)

                bill_info = {
                    "uid": dossier.get("uid", ""),
                    "titre": dossier.get("titreDossier", {}).get("titre", ""),
                    "type": type_texte,
                    "dateDepot": (
                        date_depot.split("T")[0] if date_depot else ""
                    ),  # Extract date part
                    "statut": statut,  # Current stage/status
                    "legislature": dossier.get("legislature", leg),
                }
                bills.append(bill_info)

        print(f"Loaded {len(bills)} legislative dossiers")
        return bills

    def get_bills_in_discussion(
        self, legislature: Optional[int] = None, limit: int = 10
    ) -> List[Dict]:
        """
        Get bills currently being discussed in session (séance publique)

        Args:
            legislature: Legislature number
            limit: Max number of results

        Returns:
            List of bills in discussion with author info
        """
        leg = legislature or self.legislature
        url = f"{self.BASE_URL}/{leg}/loi/dossiers_legislatifs/Dossiers_Legislatifs.json.zip"
        raw_data = self._download_and_extract_zip(url)

        in_discussion = []
        for item in raw_data:
            if len(in_discussion) >= limit:
                break
            if "dossierParlementaire" in item:
                dossier = item["dossierParlementaire"]
                actes = dossier.get("actesLegislatifs", {}).get("acteLegislatif")
                statut = self._find_last_acte(actes)

                # Check if in discussion/debate
                if "séance" in statut.lower() or "discussion" in statut.lower():
                    uid = dossier.get("uid", "")
                    titre = dossier.get("titreDossier", {}).get("titre", "")
                    procedure = dossier.get("procedureParlementaire", {})
                    type_texte = procedure.get("libelle", "")

                    # Get author reference
                    initiateur = dossier.get("initiateur", {})
                    acteurs = (
                        initiateur.get("acteurs", {}).get("acteur")
                        if initiateur
                        else None
                    )
                    acteur_ref = None
                    if isinstance(acteurs, dict):
                        acteur_ref = acteurs.get("acteurRef")
                    elif isinstance(acteurs, list) and acteurs:
                        acteur_ref = acteurs[0].get("acteurRef")

                    in_discussion.append(
                        {
                            "uid": uid,
                            "titre": titre,
                            "type": type_texte,
                            "statut": statut,
                            "acteurRef": acteur_ref,
                            "legislature": leg,
                        }
                    )

        return in_discussion

    def get_bill_details(self, bill_uid: str) -> Dict:
        """
        Get detailed information about a specific bill

        Args:
            bill_uid: Unique identifier for the bill

        Returns:
            Bill details dictionary
        """
        return {}

    def get_votes(
        self, legislature: Optional[int] = None, limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Get list of votes (scrutins)

        Args:
            legislature: Legislature number (uses instance default if not provided)
            limit: Maximum number of results. None = all votes.

        Returns:
            List of vote data dictionaries
        """
        leg = legislature or self.legislature

        # URL for votes/scrutins
        url = f"{self.BASE_URL}/{leg}/loi/scrutins/Scrutins.json.zip"

        print(f"Fetching votes data...")
        raw_data = self._download_and_extract_zip(url)

        votes = []
        items_to_process = raw_data if limit is None else raw_data[:limit]
        for item in items_to_process:
            if "scrutin" in item:
                scrutin = item["scrutin"]

                vote_info = {
                    "uid": scrutin.get("uid", ""),
                    "numero": scrutin.get("numero", ""),
                    "dateScrutin": scrutin.get("dateScrutin", ""),
                    "titre": scrutin.get("titre", ""),
                    "sort": scrutin.get("sort", {}).get("libelle", ""),
                    "nombreVotants": int(
                        scrutin.get("syntheseVote", {}).get("nombreVotants", 0)
                    ),
                    "decompte": {
                        "pour": int(
                            scrutin.get("syntheseVote", {})
                            .get("decompte", {})
                            .get("pour", 0)
                        ),
                        "contre": int(
                            scrutin.get("syntheseVote", {})
                            .get("decompte", {})
                            .get("contre", 0)
                        ),
                        "abstention": int(
                            scrutin.get("syntheseVote", {})
                            .get("decompte", {})
                            .get("abstentions", 0)
                        ),
                    },
                }
                votes.append(vote_info)

        print(f"Loaded {len(votes)} votes")
        return votes

    def get_vote_count(self, legislature: Optional[int] = None) -> int:
        """
        Get total count of votes without loading all data.
        Uses cached data if available.
        """
        leg = legislature or self.legislature
        url = f"{self.BASE_URL}/{leg}/loi/scrutins/Scrutins.json.zip"
        raw_data = self._download_and_extract_zip(url)
        count = sum(1 for item in raw_data if "scrutin" in item)
        return count

    def get_vote_details(self, vote_uid: str) -> Dict:
        """
        Get detailed information about a specific vote

        Args:
            vote_uid: Unique identifier for the vote

        Returns:
            Vote details dictionary
        """
        return {}

    def get_parliamentary_groups(self, legislature: Optional[int] = None) -> List[Dict]:
        """
        Get list of parliamentary groups

        Args:
            legislature: Legislature number (uses instance default if not provided)

        Returns:
            List of parliamentary group data dictionaries
        """
        # Groups are included in deputy data
        return []

    def get_sessions(self, legislature: Optional[int] = None) -> List[Dict]:
        """
        Get list of parliamentary sessions

        Args:
            legislature: Legislature number (uses instance default if not provided)

        Returns:
            List of session data dictionaries
        """
        return []

    def get_debates(
        self, legislature: Optional[int] = None, limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Get list of parliamentary debates (compte-rendus des séances)

        Args:
            legislature: Legislature number (uses instance default if not provided)
            limit: Maximum number of results

        Returns:
            List of debate data dictionaries
        """
        leg = legislature or self.legislature

        # URL for debates (XML format)
        url = f"{self.BASE_URL}/{leg}/vp/syceronbrut/syseron.xml.zip"

        # Check cache first
        cache_path = self._get_cache_path(url + "_debates")
        if self.use_cache and self._is_cache_valid(cache_path):
            print(f"Loading debates from cache: {cache_path.name}")
            cached_data = self._load_from_cache(cache_path)
            if cached_data is not None:
                return cached_data[:limit] if limit else cached_data

        print(f"Fetching debates data...")
        try:
            response = self.session.get(url, timeout=120)
            response.raise_for_status()

            debates = []
            ns = {"cr": "http://schemas.assemblee-nationale.fr/referentiel"}

            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
                xml_files = [f for f in zip_file.namelist() if f.endswith(".xml")]
                print(f"Found {len(xml_files)} debate files")

                for file_name in xml_files:
                    try:
                        with zip_file.open(file_name) as xml_file:
                            tree = ET.parse(xml_file)
                            root = tree.getroot()

                            # Extract metadata with namespace
                            meta = root.find("cr:metadonnees", ns)
                            if meta is None:
                                meta = root.find(".//metadonnees")
                            if meta is None:
                                continue

                            date_seance = meta.findtext(
                                "cr:dateSeanceJour", "", ns
                            ) or meta.findtext("dateSeanceJour", "")
                            num_seance = meta.findtext(
                                "cr:numSeance", "", ns
                            ) or meta.findtext("numSeance", "")
                            session_txt = meta.findtext(
                                "cr:session", "", ns
                            ) or meta.findtext("session", "")

                            # Extract sommaire (agenda items)
                            sommaire_items = []
                            sommaire_elem = meta.find("cr:sommaire", ns) or meta.find(
                                ".//sommaire"
                            )
                            if sommaire_elem is not None:
                                for titre_struct in sommaire_elem.findall(
                                    ".//cr:titreStruct", ns
                                ) or sommaire_elem.findall(".//titreStruct"):
                                    intitule = titre_struct.find(
                                        "cr:intitule", ns
                                    ) or titre_struct.find("intitule")
                                    if intitule is not None and intitule.text:
                                        titre_txt = "".join(intitule.itertext()).strip()
                                        titre_txt = titre_txt.replace("\xa0", " ")
                                        if titre_txt and titre_txt != "0":
                                            sommaire_items.append(titre_txt)

                            # Extract speakers
                            orateurs = []
                            for orateur in root.findall(
                                ".//cr:orateur", ns
                            ) or root.findall(".//orateur"):
                                nom = orateur.findtext(
                                    "cr:nom", "", ns
                                ) or orateur.findtext("nom", "")
                                orateur_id = orateur.findtext(
                                    "cr:id", "", ns
                                ) or orateur.findtext("id", "")
                                if nom and nom not in [o["nom"] for o in orateurs]:
                                    orateurs.append({"nom": nom, "id": orateur_id})

                            # Count text elements
                            contenu = root.find("cr:contenu", ns) or root.find(
                                ".//contenu"
                            )
                            nb_paragraphes = 0
                            preview_text = []

                            if contenu is not None:
                                all_text_elems = contenu.findall(
                                    ".//cr:texte", ns
                                ) or contenu.findall(".//texte")
                                nb_paragraphes = len(all_text_elems)
                                for elem in all_text_elems[:5]:
                                    if elem.text:
                                        preview_text.append(elem.text.strip())

                            uid = file_name.split("/")[-1].replace(".xml", "")

                            debate_info = {
                                "uid": uid,
                                "date": date_seance,
                                "numSeance": num_seance,
                                "session": session_txt,
                                "sommaire": sommaire_items[:10],
                                "orateurs": orateurs[:20],
                                "nbOrateurs": len(orateurs),
                                "nbParagraphes": nb_paragraphes,
                                "preview": " ".join(preview_text)[:500],
                                "legislature": leg,
                            }
                            debates.append(debate_info)

                    except ET.ParseError as e:
                        print(f"XML parse error for {file_name}: {e}")
                        continue

            debates.sort(key=lambda x: x.get("date", ""), reverse=True)

            if self.use_cache and debates:
                self._save_to_cache(cache_path, debates)
                print(f"Saved {len(debates)} debates to cache")

            print(f"Loaded {len(debates)} debates")
            return debates[:limit] if limit else debates

        except requests.exceptions.RequestException as e:
            print(f"Download failed: {e}")
            return []
        except Exception as e:
            print(f"Extraction failed: {e}")
            return []

    def get_debate_full_text(
        self, debate_uid: str, legislature: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Get the full text of a specific debate

        Args:
            debate_uid: The unique identifier of the debate
            legislature: Legislature number

        Returns:
            Full debate data with text content
        """
        leg = legislature or self.legislature
        url = f"{self.BASE_URL}/{leg}/vp/syceronbrut/syseron.xml.zip"

        # Cache the large XML ZIP file locally
        cache_file = self.CACHE_DIR / f"syseron_{leg}.xml.zip"

        try:
            # Check if we have a cached copy (valid for 24h)
            if cache_file.exists():
                file_age = time.time() - cache_file.stat().st_mtime
                if file_age < self.CACHE_TTL:
                    print(f"Loading debate XML from local cache...")
                    with open(cache_file, "rb") as f:
                        zip_content = f.read()
                else:
                    zip_content = None
            else:
                zip_content = None

            # Download if not cached
            if zip_content is None:
                print(f"Downloading debate XML (this may take a while)...")
                # Retry logic with increasing timeout
                for attempt in range(3):
                    try:
                        timeout = 120 * (attempt + 1)  # 120s, 240s, 360s
                        response = self.session.get(url, timeout=timeout)
                        response.raise_for_status()
                        zip_content = response.content
                        # Cache for future use
                        cache_file.parent.mkdir(parents=True, exist_ok=True)
                        with open(cache_file, "wb") as f:
                            f.write(zip_content)
                        print(
                            f"Cached debate XML ({len(zip_content) / 1024 / 1024:.1f} MB)"
                        )
                        break
                    except requests.exceptions.Timeout:
                        if attempt < 2:
                            print(f"Timeout on attempt {attempt + 1}, retrying...")
                            time.sleep(5)
                        else:
                            raise
                    except requests.exceptions.HTTPError as e:
                        if e.response.status_code in (502, 503, 504) and attempt < 2:
                            print(
                                f"Server error {e.response.status_code}, retrying in 10s..."
                            )
                            time.sleep(10)
                        else:
                            raise

            ns = {"cr": "http://schemas.assemblee-nationale.fr/referentiel"}

            with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_file:
                # Find the file - might be in subfolder
                target_file = None
                for name in zip_file.namelist():
                    if name.endswith(f"{debate_uid}.xml"):
                        target_file = name
                        break

                if target_file is None:
                    print(f"File {debate_uid}.xml not found in ZIP")
                    return None

                with zip_file.open(target_file) as xml_file:
                    tree = ET.parse(xml_file)
                    root = tree.getroot()

                    paragraphes = []
                    contenu = root.find("cr:contenu", ns) or root.find(".//contenu")

                    if contenu is not None:
                        # Look for paragraphe elements with namespace
                        paras = contenu.findall(".//cr:paragraphe", ns)
                        if not paras:
                            paras = contenu.findall(".//paragraphe")

                        for p in paras:
                            orateur = p.find("cr:orateur", ns) or p.find("orateur")
                            orateur_nom = ""
                            if orateur is not None:
                                orateur_nom = (
                                    orateur.findtext("cr:nom", "", ns)
                                    or orateur.findtext("nom", "")
                                    or "".join(orateur.itertext()).strip()
                                )

                            texte_elem = p.find("cr:texte", ns) or p.find("texte")
                            if texte_elem is not None:
                                texte = "".join(texte_elem.itertext()).strip()
                            else:
                                texte = "".join(p.itertext()).strip()
                                if orateur_nom and texte.startswith(orateur_nom):
                                    texte = texte[len(orateur_nom) :].strip()

                            if texte:
                                paragraphes.append(
                                    {"orateur": orateur_nom, "texte": texte}
                                )

                    # Fallback: extract from texte elements directly
                    if not paragraphes:
                        for texte_elem in root.findall(
                            ".//cr:texte", ns
                        ) or root.findall(".//texte"):
                            texte = "".join(texte_elem.itertext()).strip()
                            if texte and len(texte) > 20:
                                paragraphes.append({"orateur": "", "texte": texte})

                    print(f"Extracted {len(paragraphes)} paragraphs from {debate_uid}")

                    return {
                        "uid": debate_uid,
                        "paragraphes": paragraphes,
                        "nbParagraphes": len(paragraphes),
                    }

        except Exception as e:
            print(f"Error fetching debate text: {e}")
            import traceback

            traceback.print_exc()
            return None

    def get_amendments(
        self, legislature: Optional[int] = None, limit: int = 1000
    ) -> List[Dict]:
        """
        Get list of amendments

        Args:
            legislature: Legislature number (uses instance default if not provided)
            limit: Maximum number of results

        Returns:
            List of amendment data dictionaries
        """
        leg = legislature or self.legislature

        # URL for amendments
        url = f"{self.BASE_URL}/{leg}/loi/amendements_div_legis/Amendements.json.zip"

        print(f"Fetching amendments data...")
        raw_data = self._download_and_extract_zip(url)

        amendments = []
        for item in raw_data[:limit]:
            if "amendement" in item:
                amdt = item["amendement"]

                # Extract author
                signataires = amdt.get("signataires", {})
                auteur = signataires.get("auteur", {})
                author_ref = auteur.get("acteurRef", "")

                # Extract co-signatories count
                cosignataires = signataires.get("cosignataires", {})
                cosig_refs = cosignataires.get("acteurRef", [])
                if not isinstance(cosig_refs, list):
                    cosig_refs = [cosig_refs] if cosig_refs else []

                # Extract outcome
                cycle = amdt.get("cycleDeVie", {})
                etat = cycle.get("etatDesTraitements", {}).get("etat", {})
                sort = cycle.get("sort", {})

                # Determine if adopted
                sort_code = sort.get("code", "") if isinstance(sort, dict) else ""
                etat_code = etat.get("code", "")

                amendment_info = {
                    "uid": amdt.get("uid", ""),
                    "numero": amdt.get("identification", {}).get("numeroLong", ""),
                    "dateDepot": cycle.get("dateDepot", ""),
                    "auteur": author_ref,
                    "nombreCosignataires": len(cosig_refs),
                    "etat": etat.get("libelle", ""),
                    "etatCode": etat_code,
                    "sort": sort.get("libelle", "") if isinstance(sort, dict) else "",
                    "sortCode": sort_code,
                    "texteLegislatifRef": amdt.get("texteLegislatifRef", ""),
                    "legislature": leg,
                }
                amendments.append(amendment_info)

        print(f"Loaded {len(amendments)} amendments")
        return amendments

    def clear_cache(self) -> None:
        """Clear all cached data"""
        if self.CACHE_DIR.exists():
            import shutil

            shutil.rmtree(self.CACHE_DIR)
            self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
            print("Cache cleared")

    def get_cache_info(self) -> Dict:
        """Get information about the cache"""
        if not self.CACHE_DIR.exists():
            return {"files": 0, "size_mb": 0, "oldest": None, "newest": None}

        cache_files = list(self.CACHE_DIR.glob("*.json"))
        if not cache_files:
            return {"files": 0, "size_mb": 0, "oldest": None, "newest": None}

        total_size = sum(f.stat().st_size for f in cache_files)
        oldest = min(f.stat().st_mtime for f in cache_files)
        newest = max(f.stat().st_mtime for f in cache_files)

        import datetime

        return {
            "files": len(cache_files),
            "size_mb": round(total_size / (1024 * 1024), 2),
            "oldest": datetime.datetime.fromtimestamp(oldest).isoformat(),
            "newest": datetime.datetime.fromtimestamp(newest).isoformat(),
        }
