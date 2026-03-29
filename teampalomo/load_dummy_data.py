import sys
import os

# Agregamos la ruta del proyecto base
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.mdie_engine import mdie

def load_test_data():
    csv_file = "dummy_leak.csv"
    if not os.path.exists(csv_file):
        print(f"[!] Archivo {csv_file} no encontrado.")
        return
        
    print("[+] Inyectando datos de prueba en la base de datos MDIE (DuckDB)...")
    success = mdie.ingest_bulk_csv(csv_file, "DUMMY-LEAK-2026")
    if success:
        print("[+] Prueba Finalizada: MDIE Engine listo para búsquedas.")
    else:
        print("[-] Error inyectando datos de prueba.")
        
    mdie.close()

if __name__ == "__main__":
    load_test_data()
