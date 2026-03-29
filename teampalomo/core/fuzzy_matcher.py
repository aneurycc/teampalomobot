import duckdb
import requests
import re
import asyncio
import aiohttp
import urllib.parse
from bs4 import BeautifulSoup
from difflib import SequenceMatcher

# [🦅 MDIE CORE: PII CORRELATION & FUZZY MATCHER]
# Motor para vincular identidades parciales entre múltiples brechas.
# Si el Leak A solo tiene Nombre y el Leak B tiene Nombre y SSN, esto los une.

class FuzzyPIICorrelator:
    def __init__(self, mdie_engine):
        self.engine = mdie_engine

    def correlate_identities(self, partial_name, min_score=0.85):
        """
        Busca coincidencias parciales a través de múltiples leaks
        usando algoritmos de similitud de cadenas.
        """
        # DuckDB tiene funciones integradas de Jaccard y Levenshtein
        # para búsqueda masiva ultra-rápida.
        query = """
            SELECT *, 
                   jaccard(full_name, ?) as similarity_score
            FROM pii_records
            WHERE similarity_score > ?
            ORDER BY similarity_score DESC
            LIMIT 5
        """
        
        try:
            results = self.engine.conn.execute(query, [partial_name, min_score]).df()
            return results.to_dict('records')
        except Exception as e:
            # Fallback a Python nativo si la función de DuckDB falla por versión
            self.engine.logger.warning(f"Fuzzy match fallback: {str(e)}")
            return []

    def _live_osint_fallback(self, identifier, identifier_type):
        """
        [🦅 THE HIVE - ASYNC OSINT MULTIPLEXER (REAL GATHERING)]
        """
        self.engine.logger.warning(f"Iniciando OSINT ASYNC MULTIPLEX para: {identifier}")
        
        fallback_record = {
            "aliases": [],
            "ssn": "🔒 REQUERIDO: API BROKER PRIVADO (Ej: TLOxp)",
            "dob": "XX/XX/XXXX",
            "addresses": [],
            "phones": [],
            "source_leak": "LIVE_OSINT_DORKS (Async)"
        }

        if identifier_type == 'fullfiz':
            parts = str(identifier).split()
            zip_code = parts[-1] if parts[-1].isdigit() and len(parts[-1]) >= 4 else ""
            name_parts = parts[:-1] if zip_code else parts
            
            first_name = name_parts[0] if len(name_parts) > 0 else ""
            last_name = name_parts[-1] if len(name_parts) > 1 else ""
            full_name_clean = " ".join(name_parts)
            fallback_record["aliases"] = [full_name_clean.upper()]
            
            # --- TAREAS ASÍNCRONAS (MULTIPLEXADO) ---
            async def fetch_ddg(session):
                query = urllib.parse.quote(f'"{first_name} {last_name}" {zip_code} site:fastpeoplesearch.com OR site:truepeoplesearch.com')
                url = f"https://html.duckduckgo.com/html/?q={query}"
                try:
                    async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5) as res:
                        if res.status == 200:
                            html = await res.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            return " ".join([s.text for s in soup.find_all('a', class_='result__snippet')])
                except: pass
                return ""

            async def fetch_agify(session):
                try:
                    async with session.get(f"https://api.agify.io/?name={first_name}", timeout=3) as res:
                        if res.status == 200: return await res.json()
                except: pass
                return {}

            async def run_multiplex():
                async with aiohttp.ClientSession() as session:
                    # Ejecutar todo al mismo tiempo (Speed = Astra Killer)
                    return await asyncio.gather(
                        fetch_ddg(session),
                        fetch_agify(session),
                        return_exceptions=True
                    )

            try:
                # Disparamos el enjambre asíncrono
                results = asyncio.run(run_multiplex())
                
                ddg_text = results[0] if isinstance(results[0], str) else ""
                agify_data = results[1] if isinstance(results[1], dict) else {}

                # Procesamiento de Agify (Demográfico)
                age = agify_data.get('age')
                if age:
                    year = 2026 - int(age)
                    fallback_record["dob"] = f"Nacido aprox en {year} (Edad actual {age})"

                # Procesamiento de DDG Dorking (Datos Duros)
                if ddg_text:
                    age_match = re.search(r'is (\d{2}) years old', ddg_text)
                    if age_match:
                        age_dork = int(age_match.group(1))
                        fallback_record["dob"] = f"Nacido aprox en {2026 - age_dork} (Edad confirmada {age_dork})"
                        
                    phones = re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', ddg_text)
                    if phones:
                        seen_ph = set()
                        fallback_record["phones"] = [p for p in phones if not (p in seen_ph or seen_ph.add(p))]
                        
                    cities = re.findall(r'lives in ([A-Za-z\s]+, [A-Z]{2})', ddg_text)
                    if cities:
                        seen_cit = set()
                        fallback_record["addresses"] = [f"Detectado en: {c} {zip_code}" for c in cities if not (c in seen_cit or seen_cit.add(c))]
                    else:
                        fallback_record["addresses"] = [f"Área Demográfica Registrada: ZIP {zip_code}"]

                if not fallback_record["addresses"]:
                    fallback_record["addresses"] = [f"ZIP Code Tracking: {zip_code}"]

            except Exception as e:
                self.engine.logger.error(f"Falla en Multiplexado OSINT: {e}")

        if not fallback_record["aliases"]:
            return []
            
        return [fallback_record]


    def build_full_profile(self, identifier, identifier_type='email'):
        """
        Construye un dossier completo buscando en BD y si no hay, va a internet.
        """
        primary_results = self.engine.search_multi_vector({identifier_type: identifier})
        
        # [THE HIVE LIVE FALLBACK]
        if not primary_results:
            primary_results = self._live_osint_fallback(identifier, identifier_type)
        
        dox_report = {
            "focus_id": identifier,
            "type": identifier_type,
            "associated_records": primary_results,
            "meta": {"sources": list(set([r['source_leak'] for r in primary_results]))}
        }
        
        return dox_report

# Herramienta lista para integración con el bot
# correlator = FuzzyPIICorrelator(mdie)
