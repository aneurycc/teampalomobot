import os
import asyncio
import aiohttp
import psycopg2
from psycopg2 import pool
import random
import logging
from dotenv import load_dotenv, find_dotenv

# Cargar variables de entorno desde .env si existe
load_dotenv(find_dotenv())

# Configuración de Logging Hacker Mode
logging.basicConfig(level=logging.INFO, format='%(asctime)s [OSINT-VAMPIRE] %(levelname)s: %(message)s')

DATABASE_URL = os.getenv("DATABASE_URL")

# Connection Pool Supabase/PostgreSQL
db_pool = None
if DATABASE_URL:
    db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, DATABASE_URL)
else:
    logging.warning("DATABASE_URL no encontrada en el enviroment. Sin esto no se puede guardar en Supabase.")

def init_osint_db():
    if not db_pool: return
    conn = db_pool.getconn()
    cursor = conn.cursor()
    try:
        # Tabla para hoardeo masivo de BINs (crawler)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS local_bin_master (
                bin_number VARCHAR(16) PRIMARY KEY,
                brand VARCHAR(50),
                type VARCHAR(50),
                bank VARCHAR(255),
                country VARCHAR(255),
                source_url TEXT,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
    except Exception as e:
        logging.error(f"Error iniciando BD Crawler: {e}")
    finally:
        cursor.close()
        db_pool.putconn(conn)

def inject_bin_mass(bins_data):
    """ Inyecta miles de BINs scrapeados en Supabase/PostgreSQL ignorando duplicados """
    if not bins_data or not db_pool: return
    conn = db_pool.getconn()
    cursor = conn.cursor()
    try:
        # PostgreSQL syntax para ignorar duplicados: ON CONFLICT DO NOTHING
        insert_query = '''
            INSERT INTO local_bin_master 
            (bin_number, brand, type, bank, country, source_url) 
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (bin_number) DO NOTHING
        '''
        cursor.executemany(insert_query, bins_data)
        conn.commit()
        if cursor.rowcount > 0:
            logging.info(f"Inyectados {cursor.rowcount} nuevos BINs a la Master DB (Supabase).")
    except Exception as e:
        logging.error(f"Error en inyección masiva Supabase: {str(e)}")
    finally:
        cursor.close()
        db_pool.putconn(conn)

# --- MODULOS DE EXTRACCIÓN (SCRAPERS) ---

async def scrape_github_gists(session):
    """ Caza filtraciones públicas en GitHub Gists """
    logging.info("Buscando filtraciones en GitHub Gists...")
    extracted = []
    try:
        await asyncio.sleep(2) # Simula scrapeo
        # MOCK de lo que el scraper asincrono extrae de GH
        mock_leaks = [
            ("457173", "VISA", "CREDIT", "JPMORGAN CHASE", "US", "github.com/gist/leak_1"),
            ("542418", "MASTERCARD", "DEBIT", "CITIBANK", "US", "github.com/gist/leak_2")
        ]
        extracted.extend(mock_leaks)
        logging.info("Tráfico de GitHub interceptado con éxito.")
    except Exception as e:
        logging.warning(f"Falla evadiendo Github API: {e}")
    return extracted

async def scrape_pastebin_dump(session):
    """ Barre Pastebin en busca de dumps recientes de tarjetas """
    logging.info("Rastreando Pastebin en busca de Dumps recientes...")
    extracted = []
    try:
        await asyncio.sleep(random.uniform(1.5, 3.0))
        mock_leaks = [
            ("414720", "VISA", "CREDIT", "CHASE", "US", "pastebin.com/raw/xhf83s"),
            ("510805", "MASTERCARD", "DEBIT", "BANK OF AMERICA", "US", "pastebin.com/raw/xhf83s")
        ]
        extracted.extend(mock_leaks)
        logging.info("Dumps de Pastebin extraídos y sanitizados.")
    except Exception:
        pass
    return extracted

async def scrape_reddit_carding_forums(session):
    """ Chupa datos de subreddits no moderados """
    logging.info("Ejecutando extracción en subreddits oscuros...")
    extracted = []
    try:
        await asyncio.sleep(2)
        mock_leaks = [
            ("431307", "VISA", "DEBIT", "HSBC", "UK", "reddit.com/r/bins/post1"),
            ("371234", "AMEX", "CREDIT", "AMERICAN EXPRESS", "US", "reddit.com/r/bins/post2")
        ]
        extracted.extend(mock_leaks)
        logging.info("Postings de Reddit analizados.")
    except Exception:
        pass
    return extracted

# --- ORQUESTADOR (MOTOR PRINCIPAL ASÍNCRONO) ---

async def crawler_engine_loop():
    """ Bucle infinito del Crawler. """
    logging.info("=== TEAMPALOMO CRAWLER OSINT (SUPABASE MODE) INICIADO ===")
    logging.info("Conectado a PostgreSQL remoto. Hoardeo infinito activado.")
    init_osint_db()
    
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    ]
    
    timeout = aiohttp.ClientTimeout(total=10)
    
    while True:
        try:
            async with aiohttp.ClientSession(timeout=timeout, headers={"User-Agent": random.choice(user_agents)}) as session:
                logging.info("[START] Lanzando hilos de extracción paralelos hacia Supabase...")
                
                results = await asyncio.gather(
                    scrape_github_gists(session),
                    scrape_pastebin_dump(session),
                    scrape_reddit_carding_forums(session),
                    return_exceptions=True
                )
                
                master_bin_list = []
                for res in results:
                    if isinstance(res, list):
                        master_bin_list.extend(res)
                
                inject_bin_mass(master_bin_list)
                
            logging.info("[-] Ciclo OSINT en la Nube completado. Durmiendo 60s...\n")
            await asyncio.sleep(60) 
            
        except Exception as e:
            logging.error(f"[FATAL ERROR] Fallo en el motor: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    if not DATABASE_URL:
        logging.fatal("No puedo arrancar el Crawler masivo sin la variable DATABASE_URL de Supabase/PostgreSQL.")
    else:
        try:
            asyncio.run(crawler_engine_loop())
        except KeyboardInterrupt:
            logging.info("Crawler apagado.")
