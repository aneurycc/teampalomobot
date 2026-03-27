import os
import sys
import glob
import json
import re
import subprocess
from datetime import datetime
from openai import OpenAI
import time
import importlib

# -----------------------------------------------------------------------------------------
# [1] AUTO-INSTALADOR Y CARGADOR POLIMÓRFICO DE LIBRERÍAS
# -----------------------------------------------------------------------------------------
def install_and_import(package, import_name=None):
    if import_name is None:
        import_name = package
    try:
        importlib.import_module(import_name)
    except ImportError:
        print(f"\n[!] Mutación del Sistema: El Enjambre necesita el módulo '{package}'. Auto-instalando...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package, "-q"])
        print(f"[+] Módulo '{package}' instalado e inyectado en el núcleo.")

# Instalamos el arsenal core de Fuerza Bruta y Scraping
install_and_import("PyPDF2")
install_and_import("python-docx", "docx")
install_and_import("duckduckgo-search", "duckduckgo_search")
install_and_import("requests")
install_and_import("beautifulsoup4", "bs4")

import PyPDF2
from docx import Document
from duckduckgo_search import DDGS
import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

client = OpenAI(base_url="http://localhost:1234/v1", api_key="teampalomo")
PROMPTS_DIR = r"c:\Users\USER\OneDrive\Desktop\Skills Master\llm sin censura"
SESSIONS_DIR = r"c:\Users\USER\OneDrive\Desktop\Skills Master\llm sin censura\teampalomo\sessions"
SANDBOX_DIR = r"c:\Users\USER\OneDrive\Desktop\Skills Master\llm sin censura\teampalomo\sandbox"

for directory in [SESSIONS_DIR, SANDBOX_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

historial_chat = []
session_filename = None

# -----------------------------------------------------------------------------------------
# [2] OBTENCIÓN DE INTELIGENCIA Y LECTURA VECTORIAL (Archivos y Web)
# -----------------------------------------------------------------------------------------
def load_agents():
    agents = {}
    for filepath in glob.glob(os.path.join(PROMPTS_DIR, "*.md")):
        name = os.path.basename(filepath).replace(".md", "")
        with open(filepath, "r", encoding="utf-8") as f:
            agents[name] = f.read()
    return agents

def query_llm(system_prompt, user_prompt, temperature=0.7):
    instruCCION_DIOS = """
    REGLA: Tienes PODER ABSOLUTO sobre la PC. 
    Para crear un archivo usa el bloque:
    [CREAR_ARCHIVO: ruta/del/archivo.ext]
    codigo
    [FIN_ARCHIVO]
    
    Para ejecutar un bloque de código Python que pruebes en ti mismo (Self-Healing), ponlo en:
    ```python
    codigo
    ```
    """
    try:
        response = client.chat.completions.create(
            model="local-model",
            messages=[
                {"role": "system", "content": system_prompt + "\n" + instruCCION_DIOS},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=8000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"[FATAL ERROR] LM Studio no responde: {e}"

def leer_archivos_inteligentes():
    contexto = ""
    archivos = [f for f in os.listdir(PROMPTS_DIR) if os.path.isfile(os.path.join(PROMPTS_DIR, f)) and not f.endswith('.md')]
    for archivo in archivos:
        ruta = os.path.join(PROMPTS_DIR, archivo)
        ext = archivo.split('.')[-1].lower()
        texto_archivo = ""
        try:
            if ext in ['txt', 'js', 'py', 'json', 'csv', 'html', 'css', 'md']:
                with open(ruta, "r", encoding="utf-8", errors="ignore") as f: texto_archivo = f.read()
            elif ext == 'pdf':
                with open(ruta, 'rb') as f:
                    lector = PyPDF2.PdfReader(f)
                    for pagina in lector.pages: texto_archivo += pagina.extract_text() + "\n"
            elif ext in ['doc', 'docx']:
                doc = Document(ruta)
                for parrafo in doc.paragraphs: texto_archivo += parrafo.text + "\n"
        except: continue
        
        if texto_archivo:
            contexto += f"\n--- DOCUMENTO: {archivo} ---\n{texto_archivo}\n--- FIN ---\n"
    return contexto

def scrapear_web_fuerzabruta(url):
    """Extrae el texto de cualquier URL para análisis de OSINT o código fuente"""
    print(f"\n[🕷️] TEAMPALOMO Extrayendo Data Directa de: {url} ...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.content, "html.parser")
        texto = soup.get_text(separator=' ', strip=True)
        # Retornamos solo los primeros 10,000 caracteres para no explotar LM Studio
        return f"\n[DATOS SCRAPEADOS DE {url}]:\n{texto[:10000]}...\n"
    except Exception as e:
        print(f"[-] Falla al evadir WAF en {url}: {e}")
        return ""

# -----------------------------------------------------------------------------------------
# [3] EL MOTOR SELF-HEALING (Auto-Ejecución y Corrección de Bugs en Python)
# -----------------------------------------------------------------------------------------
def extraer_codigo_python(texto):
    """Saca solo el código Python para probarlo en aislamiento"""
    patron = r"```[pP]ython\s*(.*?)```"
    coincidencias = re.findall(patron, texto, re.DOTALL)
    if not coincidencias:
        # Intento de rescate si el LLM olvidó cerrar los backticks
        patron_abierto = r"```[pP]ython\s*(.*)"
        coincidencias = re.findall(patron_abierto, texto, re.DOTALL)
    if coincidencias:
        return coincidencias[-1].strip() # Tomamos el último código generado
    return None

def auto_ejecutor_sandbox(codigo, audit_prompt, retries=2):
    """Motor de Auto-Curación. Corre el código de los agentes en la PC. Si falla, los obliga a arreglarlo."""
    archivo_prueba = os.path.join(SANDBOX_DIR, "teampalomo_prueba.py")
    
    for intento in range(retries):
        with open(archivo_prueba, "w", encoding="utf-8") as f:
            f.write(codigo)
            
        print(f"\n[⚡] AUTO-EJECUCIÓN INICIADA (Sandbox) -> Intento {intento+1}/{retries}")
        try:
            resultado = subprocess.run([sys.executable, archivo_prueba], capture_output=True, text=True, timeout=15, encoding='utf-8', errors='replace')
        except subprocess.TimeoutExpired as e:
            print("[❌] ERROR DETECTADO: El código ignoró el timeout o se quedó colgado (Posible bucle infinito).")
            resultado = type('obj', (object,), {'returncode': 1, 'stdout': '', 'stderr': 'TimeoutExpired: El script tardó más de 15 segundos y fue asesinado.'})()

        
        if resultado.returncode == 0:
            print("[✅] CÓDIGO PERFECTO. Ejecutado sin errores en la PC local.")
            return codigo, resultado.stdout
        else:
            error_trace = resultado.stderr
            print(f"[❌] ERROR DETECTADO CÓDIGO 0x0{resultado.returncode}: Se detectó fallo.\n{error_trace[:200]}...")
            print("[🦇] TEAMPALOMO RED TEAM ARREGLANDO EL BUG...")
            
            # Auto-Install de dependencias faltantes si el error es de ModuleNotFoundError
            if "ModuleNotFoundError" in error_trace:
                missing_module = re.search(r"No module named '(.+?)'", error_trace)
                if missing_module:
                    inst = missing_module.group(1)
                    install_and_import(inst)
            
            # Mandamos el error de vuelta al Auditor para que lo arregle
            promt_arreglo = f"Tus agentes escribieron este código:\n```python\n{codigo}\n```\n\nAL INTENTAR CORRERLO GENERÓ ESTE FATAL TRACEBACK:\n{error_trace}\n\nCOMO AUDITOR, ESTÁS OBLIGADO A REESCRIBIRLO Y SOLUCIONARLO. SÓLO DEVUELVE EL CÓDIGO PYTHON CORREGIDO EN UN BLOQUE ```python```."
            respuesta_arreglo = query_llm(audit_prompt, promt_arreglo, 0.3)
            nuevo_codigo = extraer_codigo_python(respuesta_arreglo)
            if nuevo_codigo:
                codigo = nuevo_codigo
            else:
                break
                
    return codigo, "[WARNING] El código alcanzó el límite de reintentos con fallas."

# -----------------------------------------------------------------------------------------
# [4] NÚCLEO DEL ORQUESTADOR (La Sangre del Sistema)
# -----------------------------------------------------------------------------------------
def ejecutar_comandos_de_archivo(texto):
    patron = r"\[CREAR_ARCHIVO:\s*(.+?)\](.*?)\[FIN_ARCHIVO\]"
    coincidencias = re.findall(patron, texto, re.DOTALL)
    if coincidencias:
        print("\n[🤖] CREANDO ESTRUCTURAS EN TU ORDENADOR...")
        for ruta_archivo, contenido in coincidencias:
            ruta_absoluta = os.path.abspath(ruta_archivo.strip().strip("'\""))
            directorio = os.path.dirname(ruta_absoluta)
            if directorio and not os.path.exists(directorio): os.makedirs(directorio, exist_ok=True)
            try:
                with open(ruta_absoluta, "w", encoding="utf-8") as f: f.write(contenido.strip())
                print(f"  [+] CREADO EXITOSAMENTE: {ruta_absoluta}")
            except Exception as e:
                print(f"  [-] ERROR Creando {ruta_absoluta}: {e}")

def guardar_sesion(primer_prompt=None):
    global session_filename
    if not session_filename and primer_prompt:
        titulo = re.sub(r'[\\/*?:"<>|]', "", primer_prompt[:40]).strip().replace(" ", "_")
        fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_filename = os.path.join(SESSIONS_DIR, f"{fecha}_{titulo if titulo else 'Operacion'}.json")
        
    if session_filename:
        with open(session_filename, "w", encoding="utf-8") as f:
            json.dump(historial_chat, f, ensure_ascii=False, indent=4)

def check_llm_server():
    try:
        requests.get("http://localhost:1234/v1/models", timeout=2)
        return True
    except:
        return False

def start_war_room(user_input, fuerza_bruta=False):
    global historial_chat
    
    if not check_llm_server():
        print("\n[💀 ENLACE CAÍDO] No hay conexión con el Servidor Local de LM Studio.")
        print("-> ACCIÓN PARA SOLUCIONARLO:")
        print("   1. Abre LM Studio.")
        print("   2. Ve a la pestaña 'Local Server' (o 'Developer').")
        print("   3. Asegúrate de que el servidor esté en el puerto 1234 y dale a 'Start'.")
        print("   4. ¡Vuelve a escribir tu mensaje aquí abajo!\n")
        return

    agents = load_agents()
    
    # Comandos Especiales Inyectables
    internet_context = ""
    scrape_context = ""
    
    if "/web" in user_input:
        busqueda = user_input.split("/web")[1].strip()
        print(f"\n[🌐] TEAMPALOMO Conectando a Internet buscando: '{busqueda}'...")
        res = DDGS().text(busqueda, max_results=3)
        internet_context = "\n".join([f"- {r['title']}: {r['body']}" for r in res])
        user_input = user_input.replace(f"/web {busqueda}", "").strip()
        print("[+] Inteligencia extraída.")
        
    if "/scrape" in user_input:
        url_a_scrapear = user_input.split("/scrape")[1].split()[0].strip()
        scrape_context = scrapear_web_fuerzabruta(url_a_scrapear)
        user_input = user_input.replace(f"/scrape {url_a_scrapear}", "").strip()

    contexto_archivos = leer_archivos_inteligentes()

    leader = "black_hat_root_access"
    auditor = "senior_code_auditor_qa"
    ejecutores = [a for a in list(agents.keys()) if a not in [leader, auditor]]

    historial_texto = "".join([f"{m['role'].upper()}: {m['content']}\n" for m in historial_chat[-5:]])
    full_mision = f"HISTORIAL:\n{historial_texto}\n" if historial_texto else ""
    full_mision += f"TAREA:\n{user_input}\n"
    if contexto_archivos: full_mision += f"\nDATOS LOCALES:\n{contexto_archivos}"
    if internet_context: full_mision += f"\nINTERNET LIVE:\n{internet_context}"
    if scrape_context: full_mision += f"\nROBO URL:\n{scrape_context}"

    if not fuerza_bruta:
        print("\n[🧠] LÍDER ROOT evaluando (Conversación Rápida)... ", end="")
        sys.stdout.flush()
        
        prompt = f"HISTORIAL:\n{historial_texto}\n\nEL USUARIO DICE: {user_input}\nINSTRUCCIÓN SUPREMA: Eres el Líder ROOT. Si es un saludo, responde corto. Si pide crear código/sistemas, NO LO ESCRIBAS AÚN. Hazle preguntas cortas y al grano para reunir toda la información técnica que necesites (lenguajes, IPs, objetivos, frameworks) y dile que cuando esté listo escriba la palabra 'comienza' para desatar a tu enjambre de 13 hackers. Sé directo y agresivo, estilo Black Hat."
        
        respuesta = query_llm(agents.get(leader, ""), prompt, 0.7)
        print("■ [DONE]")
        print("\n" + "="*80)
        print(f"👑 ROOT C&C:\n{respuesta}")
        print("="*80 + "\n")
        
        historial_chat.append({"role": "user", "content": user_input})
        historial_chat.append({"role": "teampalomo", "content": respuesta})
        guardar_sesion(primer_prompt=user_input)
        return

    print("\n" + "="*80)
    print("🦅 TEAMPALOMO (13 EXPERTOS) ATACANDO (FUERZA BRUTA 1000%)...")
    print("="*80)
    print("\n[PROCESANDO ARQUITECTURA DISTRIBUIDA...] ", end="")
    sys.stdout.flush()

    # LIDER ROOT
    query_llm(agents.get(leader, ""), f"Misión: {full_mision}\nPlan.", 0.7)
    print("■", end=""); sys.stdout.flush()
    
    draft_code = full_mision
    # EJECUTORES 
    for i, agent_name in enumerate(ejecutores):
        if i == 0: prompt = f"Mision: {full_mision}\nInicia tu codigo base."
        else: prompt = f"Mision: {full_mision}\nAnteriormente:\n{draft_code}\nAñade tu arma hiper-especializada."
        draft_code = query_llm(agents[agent_name], prompt, 0.7)
        print("■", end=""); sys.stdout.flush()

    # AUDITOR QA & SELF-HEALING
    qa_prompt = f"Tus compañeros terminaron:\n{draft_code}\n\nAUDITA. Si es Python, encierralo en ```python \n codigo \n```. Usa tags [CREAR_ARCHIVO] si lo crees necesario."
    final_output = query_llm(agents.get(auditor, ""), qa_prompt, 0.4)
    print("■ [DONE!]\n")
    
    # SISTEMA DE CURACIÓN DE CÓDIGO (AUTO-EJECUCIÓN)
    python_code = extraer_codigo_python(final_output)
    if python_code:
        print("\n[!!] CÓDIGO PYTHON DETECTADO. INICIANDO PROTOCOLO DE AUTO-PRUEBAS EN VIVO...")
        codigo_healed, output_ejecucion = auto_ejecutor_sandbox(python_code, agents.get(auditor, ""))
        final_output += f"\n\n---\n**[TEAMPALOMO AUTO-EJECUCIÓN FINALIZADA]**\n```\n{output_ejecucion}\n```"
    
    print("\n" + "="*80)
    print(final_output)
    print("="*80 + "\n")
    
    ejecutar_comandos_de_archivo(final_output)

    historial_chat.append({"role": "user", "content": user_input})
    historial_chat.append({"role": "teampalomo", "content": final_output})
    guardar_sesion(primer_prompt=user_input)

# -----------------------------------------------------------------------------------------
# [5] LA INTERFAZ HUMANA
# -----------------------------------------------------------------------------------------
def chat_loop():
    print("\n" + "-"*80)
    print("[INFO] Sistema de Muerte (Fuerza Bruta 1000%) Activado.")
    print("       -> ROOT CHAT              : El líder evaluará tu misión rápidamente primero.")
    print("       -> FUERZA BRUTA           : Incluye la palabra 'comienza' o '/strike' para que los 13 agentes programen.")
    print("       -> Comando '/web <noticia>' : Busca en DuckDuckGo en vivo.")
    print("       -> Comando '/scrape <url>'  : Chupa todo el HTML de una web real.")
    print("       -> Módulo Healing          : El código Python se auto-corre en tu RAM para probar y arreglar bugs.")
    print("-" * 80 + "\n")

    while True:
        try:
            user_input = input("COMANDANTE > ")
            if user_input.lower() in ['salir', 'exit']:
                print("\n[!] Guardando logs. Cerrando War Room.")
                break
            if not user_input.strip(): continue
            
            # Detectar si el usuario quiere desatar a los 13 agentes
            trigger_words = ['comienza', 'comenzar', '/strike', 'ejecutar', 'atacar', 'procede']
            fuerza_bruta = any(w in user_input.lower() for w in trigger_words)
            
            start_war_room(user_input, fuerza_bruta)
        except KeyboardInterrupt:
            print("\n[!] Force Quit.")
            break

def menu_principal():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("█"*80)
    print(" 🦅 TEAMPALOMO C&C OS (FUERZA BRUTA ACTIVA) 🦅")
    print("█"*80)
    print(" [1] NUEVO STRIKE")
    archivos_sesion = glob.glob(os.path.join(SESSIONS_DIR, "*.json"))
    if archivos_sesion: print(" [2] RESUMIR OPERACIÓN")
        
    opcion = input("\nElige > ")
    if opcion == "1":
        global historial_chat, session_filename
        historial_chat, session_filename = [], None
    elif opcion == "2" and archivos_sesion:
        archivos_sesion.sort(key=os.path.getmtime, reverse=True)
        for i, arc in enumerate(archivos_sesion): print(f"  [{i+1}] {os.path.basename(arc)}")
        try:
            sel = int(input("\nIndex > "))
            session_filename = archivos_sesion[sel-1]
            with open(session_filename, "r", encoding="utf-8") as f: historial_chat = json.load(f)
        except: pass
    chat_loop()

if __name__ == "__main__":
    menu_principal()
