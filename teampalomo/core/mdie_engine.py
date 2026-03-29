import duckdb
import os
import logging
import json
from datetime import datetime

# [🦅 MDIE CORE: MASSIVE DATA INTELLIGENCE ENGINE]
# Motor central de búsqueda e indexación de TEAMPALOMO.
# Diseñado para latencia sub-segundo en miles de millones de registros.

class MDIEEngine:
    def __init__(self, db_path='mdie_production.db'):
        self.db_path = db_path
        # No usamos ':memory:' para persistir la indexación de brechas grandes
        self.conn = duckdb.connect(self.db_path)
        self._setup_logging()
        self._initialize_schema()
        self.logger.info("MDIE Engine iniciado y listo para la guerra.")

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='[%(levelname)s] %(asctime)s - %(message)s'
        )
        self.logger = logging.getLogger("MDIE")

    def _initialize_schema(self):
        """Prepara las tablas base para datos de PII (Personally Identifiable Information)"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS pii_records (
                id VARCHAR,
                full_name VARCHAR,
                ssn VARCHAR,
                dob DATE,
                address VARCHAR,
                city VARCHAR,
                state VARCHAR,
                zip VARCHAR,
                email VARCHAR,
                phone VARCHAR,
                source_leak VARCHAR,
                ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def ingest_bulk_csv(self, csv_path, source_name):
        """Carga masiva desde CSV con mapeo inteligente"""
        self.logger.info(f"Iniciando ingesta masiva desde: {csv_path}")
        try:
            # DuckDB infiere tipos y carga GBs en segundos
            temp_table = f"temp_leak_{int(datetime.now().timestamp())}"
            self.conn.execute(f"CREATE TABLE {temp_table} AS SELECT * FROM read_csv_auto('{csv_path}')")
            
            # Aquí se realizaría el mapeo de columnas dinámico si fuera necesario
            # Por simplicidad, asumimos un append a la tabla principal
            self.conn.execute(f"INSERT INTO pii_records SELECT *, '{source_name}', CURRENT_TIMESTAMP FROM {temp_table}")
            self.conn.execute(f"DROP TABLE {temp_table}")
            
            count = self.conn.execute("SELECT count(*) FROM pii_records").fetchone()[0]
            self.logger.info(f"Ingesta exitosa. Total registros en DB: {count}")
            return True
        except Exception as e:
            self.logger.error(f"Error en ingesta: {str(e)}")
            return False

    def search_multi_vector(self, query_params: dict):
        """
        Búsqueda avanzada multi-vector (SSN, Email, Teléfono o Nombre)
        Retorna lista de diccionarios (JSON ready para el bot)
        """
        if not query_params:
            return []

        conditions = []
        values = []
        for key, value in query_params.items():
            if key in ['ssn', 'email', 'phone', 'full_name']:
                conditions.append(f"{key} ILIKE ?")
                values.append(f"%{value}%")

        if not conditions:
            return []

        where_clause = " WHERE " + " AND ".join(conditions)
        query = f"SELECT * FROM pii_records {where_clause} LIMIT 10"
        
        try:
            res = self.conn.execute(query, values).df() # Retorna DataFrame para manejo fácil
            return res.to_dict('records')
        except Exception as e:
            self.logger.error(f"Fallo en búsqueda multi-vector: {str(e)}")
            return []

    def close(self):
        self.conn.close()

# Singleton para uso global en el sistema
mdie = MDIEEngine()
