import requests
import os

def send_telegram(message):
    """Envoie un message Telegram si les tokens sont présents."""
    token = os.getenv("TELEGRAM_HOMELAB_TOKEN")
    chat_ids = tuple(
        chat_id.strip()
        for chat_id in os.getenv("TELEGRAM_CHAT_IDS", "").split(",")
        if chat_id.strip()
    )
    
    if not token or not chat_ids:
        print("⚠️ Pas de config Telegram trouvée.")
        return
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        # Pas de proxy spécifique ici, on utilise le NAT du serveur
        for chat_id in chat_ids:
            requests.post(
                url,
                json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
                timeout=5,
            )
    except Exception as e:
        print(f"❌ Erreur envoi Telegram: {e}")
