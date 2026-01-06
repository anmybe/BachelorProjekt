import google.generativeai as genai
import time

# === KONFIGURATION ===
API_KEY = "..."  # 👈 Dein neuer Key
MODEL = "gemini-2.5-flash"

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL)

# === BEISPIELTEXT (~20k Zeichen) ===
sample_text = ("Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 400)
prompt = f"""
Split the following scientific text into 3 semantically coherent chunks.
Keep wording identical and output valid JSON only with keys 'id' and 'text'.

Text:
{sample_text}
"""

print(f"🟢 Promptlänge: {len(prompt)} Zeichen")

try:
    start = time.time()
    print("🟡 Sende Anfrage an Gemini ...")
    response = model.generate_content(prompt, request_options={"timeout": 300})
    duration = time.time() - start

    print(f"⏱️ Dauer: {duration:.2f}s")
    if not response:
        print("❌ Keine Antwortobjekt erhalten.")
    else:
        print("✅ Antwortobjekt erhalten:", type(response))
        txt = getattr(response, "text", None)
        if txt:
            print(f"📤 Antwort (erste 800 Zeichen):\n{txt}")
        else:
            print("⚠️ Kein Text in der Antwort vorhanden.")
except Exception as e:
    print("💥 Fehler:")
    print(f"Typ: {type(e).__name__}")
    print(f"Details: {e}")
