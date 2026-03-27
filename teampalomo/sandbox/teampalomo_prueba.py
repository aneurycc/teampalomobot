import requests
import pymongo

# Configuración inicial del bot y la base de datos
TELEGRAM_BOT_TOKEN = 'YOUR_BOT_TOKEN'
bot_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/"

client = pymongo.MongoClient('localhost', 27017)
db = client['bin_db']
collection = db['bins']

# Función para responder al usuario
def send_response(chat_id, response_text):
    data = {
        "chat_id": chat_id,
        "text": response_text
    }
    requests.post(bot_url + "sendMessage", json=data)

# Función para verificar el BIN a través de la API externa
def verify_bin(bin_number: str):
    try:
        api_url = f'https://api.example.com/check/{bin_number}'
        response = requests.get(api_url, timeout=5)
        
        if response.status_code == 200:
            return "El BIN es seguro para transacciones."
        else:
            return "Advertencia: El BIN presenta riesgos de fraude o no es válido."
    except requests.RequestException as e:
        return f"Error al verificar el BIN: {str(e)}"

# Handler para mensajes del bot
def verify_bin_command(bin_number):
    result_in_db = collection.find_one({"bin_number": bin_number})
    
    if not result_in_db:
        response_text = "BIN no encontrado. Por favor, verifica otro número."
    elif result_in_db['response_code'] == 200:
        response_text = f"El BIN {bin_number} es seguro para transacciones."
    else:
        response_text = f"Advertencia: El BIN {bin_number} presenta riesgos de fraude o no es válido."

    send_response(result_in_db['chat_id'], response_text)

# Ejemplo de uso (deberías reemplazar con la lógica real para obtener el chat_id)
def main():
    # Suponiendo que tienes el chat_id del usuario
    chat_id = 123456789  # Reemplaza con el verdadero ID del chat
    
    verify_bin_command(chat_number)

if __name__ == '__main__':
    main()