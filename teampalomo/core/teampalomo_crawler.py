import os
import re
import time
import requests
import psycopg2
import schedule
from psycopg2 import pool
from dotenv import load_dotenv, find_dotenv

# Cargar variables de entorno
load_dotenv(find_dotenv())

# Configuración de Base de Datos
DATABASE_URL = os.getenv("DATABASE_URL")
db_pool = None
if DATABASE_URL:
    try:
        db_pool = psycopg2.pool.SimpleConnectionPool(1, 5, DATABASE_URL)
    except Exception as e:
        print(f"[ERROR CRAWLER POOL] {e}")

def save_bin_intel(bin_num, brand, card_type, bank, country, score=50, gateways="Stripe, Shopify"):
    """Guarda o actualiza la inteligencia de un BIN en la DB central"""
    if not db_pool: return
    conn = db_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO local_bin_master (bin_number, brand, type, bank, country, vulnerability_score, gateways_identified, last_seen)
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (bin_number) DO UPDATE SET 
                vulnerability_score = EXCLUDED.vulnerability_score,
                gateways_identified = EXCLUDED.gateways_identified,
                last_seen = CURRENT_TIMESTAMP
        """, (bin_num[:6], brand, card_type, bank, country, score, gateways))
        conn.commit()
    except Exception as e:
        print(f"[SAVE ERROR] {e}")
    finally:
        cursor.close()
        db_pool.putconn(conn)

def log_activity(source, count):
    if not db_pool: return
    conn = db_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO crawler_activity_log (source, bins_found) VALUES (%s, %s)", (source, count))
        conn.commit()
    finally:
        cursor.close()
        db_pool.putconn(conn)

# --- MOTORES DE SCRAPING (Vectores de Ataque) ---

def scrape_github():
    """Busca BINs "calientes" en repositorios públicos de Git (Leaks/Config)"""
    print("[🔍] Scrapeando GitHub...")
    # Simulación de búsqueda en código GitHub (Leaks de config)
    # En producción usaríamos la API de GitHub con un token
    found = 0
    # Ejemplo de patrones que un scraper real extraería de archivos .env/config filtrados
    mock_leaks = [
        ("400022", "VISA", "DEBIT", "CHASE", "US", 85, "Amazon, Stripe"),
        ("510510", "MASTERCARD", "CREDIT", "HDFC", "IN", 92, "Shopify, Razorpay")
    ]
    for b in mock_leaks:
        save_bin_intel(*b)
        found += 1
    log_activity("GitHub_Leaker", found)

def scrape_reddit():
    """Extrae BINs compartidos en subreddits de 'vulnerabilidades' o 'drops'"""
    print("[🔍] Scrapeando Reddit...")
    # Simulación de búsqueda en r/binning o similares
    found = 0
    # Data extraída de "threads" de Reddit
    mock_reddit = [
        ("444444", "VISA", "PREPAID", "BANCORP", "US", 78, "Spotify, Netflix"),
        ("414720", "VISA", "CREDIT", "CAPITAL ONE", "US", 65, "Stripe, Facebook")
    ]
    for b in mock_reddit:
        save_bin_intel(*b)
        found += 1
    log_activity("Reddit_Sensor", found)

def scrape_generic_web():
    """Busca en bases de datos públicas y sitios de BIN lookup actualizados"""
    print("[🔍] Scrapeando Web Pública...")
    # Aquí irían requests a sitios tipo bins.io con rotación de proxies
    log_activity("Web_Crawler", 5) 

# --- ORQUESTADOR ---

def run_hive_cycle():
    print(f"\n[🐝] INICIANDO CICLO DE MINERÍA '{time.strftime('%Y-%m-%d %H:%M')}'")
    scrape_github()
    scrape_reddit()
    scrape_generic_web()
    print("[🐝] CICLO COMPLETADO. Inteligencia sincronizada con Supabase.\n")

if __name__ == "__main__":
    # La primera vez corre de inmediato
    run_hive_cycle()
    
    # Programar para correr cada 12 horas (para mantener data fresca)
    schedule.every(12).hours.do(run_hive_cycle)
    
    while True:
        schedule.run_pending()
        time.sleep(60)
