import requests
import os

def send_telegram(message):
    """Envoie un message Telegram si les tokens sont présents."""
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    
    if not token or not chat_id:
        print("⚠️ Pas de config Telegram trouvée.")
        return
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        # Pas de proxy spécifique ici, on utilise le NAT du serveur
        requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}, timeout=5)
    except Exception as e:
        print(f"❌ Erreur envoi Telegram: {e}")