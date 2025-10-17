from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from conversational_agent5 import ConversationalAgent
from gtts import gTTS
import pandas as pd
import matplotlib.pyplot as plt
import requests
import os
import glob

# ====================================
# 🚀 CONFIGURACIÓN FASTAPI
# ====================================

app = FastAPI(title="Orion AI - Gemini API")

agent = ConversationalAgent()

# 🔓 Permitir acceso desde cualquier origen
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====================================
# 🏠 FRONTEND PRINCIPAL
# ====================================

@app.get("/")
def root():
    """Sirve el archivo frontend principal"""
    with open("frontend.html", encoding="utf-8") as f:
        return HTMLResponse(f.read())

# Servir archivos estáticos
app.mount("/static", StaticFiles(directory="."), name="static")


# ====================================
# 💬 CHAT PRINCIPAL (IA + funciones)
# ====================================

@app.post("/chat")
async def chat(user_message: str = Form(...)):
    mensaje = user_message.lower()
    graphic = None

    # 🤖 Respuestas inteligentes y comandos
    if any(p in mensaje for p in ["hola", "buenos días", "buenas", "hey", "qué tal"]):
        texto_respuesta = (
            "👋 ¡Hola! Soy Orion, tu agente conversacional con IA. "
            "Puedo ayudarte con clima, gráficos, voz, traducción, búsqueda web y más."
        )

    elif "clima" in mensaje or "temperatura" in mensaje:
        try:
            url = "https://api.open-meteo.com/v1/forecast?latitude=4.61&longitude=-74.08&current_weather=true"
            data = requests.get(url).json()
            clima = data.get("current_weather", {})
            temperatura = clima.get("temperature", "desconocida")
            viento = clima.get("windspeed", "desconocido")
            texto_respuesta = f"🌤️ En Bogotá hay {temperatura}°C y viento de {viento} km/h."
        except Exception as e:
            texto_respuesta = f"No pude obtener el clima: {str(e)}"

    elif "voz" in mensaje:
        texto_respuesta = "🎤 Para usar voz escribe: voz: Hola, ¿cómo estás?"

    elif "scrape" in mensaje or "extraer" in mensaje:
        texto_respuesta = "🌐 Para hacer scraping, escribe: scrape: https://ejemplo.com"

    elif "traducir" in mensaje:
        texto_respuesta = "🌎 Para traducir, escribe: traducir: hola al inglés"

    elif "calcular" in mensaje or "cuánto es" in mensaje:
        texto_respuesta = "➗ Para calcular, escribe: calcular: 5 * 3 + 2"

    elif "grafico" in mensaje or "gráfico" in mensaje or "visualizar" in mensaje:
        csv_files = glob.glob("*.csv")
        if not csv_files:
            texto_respuesta = "❌ No encontré ningún archivo CSV cargado. Sube uno primero."
        else:
            latest_csv = max(csv_files, key=os.path.getmtime)
            try:
                df = pd.read_csv(latest_csv)

                # 🔍 Detectar tipo de gráfico
                tipo = "bar"
                if "líneas" in mensaje or "lineas" in mensaje:
                    tipo = "line"
                elif "pie" in mensaje or "pastel" in mensaje:
                    tipo = "pie"

                plt.figure(figsize=(8, 4))
                if tipo == "pie":
                    df[df.columns[1]].value_counts().plot.pie(autopct="%1.1f%%")
                elif tipo == "line":
                    df.plot(x=df.columns[0], y=df.columns[1:], kind="line", marker="o")
                else:
                    df.plot(x=df.columns[0], y=df.columns[1:], kind="bar")

                plt.title(f"Gráfico tipo {tipo} - {latest_csv}")
                plt.tight_layout()
                filename = "grafico.png"
                plt.savefig(filename)
                plt.close()

                graphic = filename
                texto_respuesta = f"📊 Gráfico {tipo} generado correctamente."
            except Exception as e:
                texto_respuesta = f"⚠️ Error al generar gráfico: {str(e)}"

    else:
        # 🧠 Si no coincide con ninguna orden, pasa a la IA
        texto_respuesta = agent.chat(user_message)
        files = [f for f in os.listdir('.') if f.endswith('.png')]
        if files:
            graphic = max(files, key=os.path.getmtime)

    return JSONResponse({"response": texto_respuesta, "graphic": graphic})


# ====================================
# 📂 SUBIR ARCHIVO CSV
# ====================================

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    """Guarda un archivo CSV subido"""
    out = file.filename
    with open(out, "wb") as f:
        f.write(await file.read())
    return {"filename": out}


# ====================================
# 🖼️ SERVIR IMÁGENES
# ====================================

@app.get("/image/{name}")
def image(name: str):
    """Devuelve una imagen generada (como gráficos)"""
    return FileResponse(os.path.abspath(name))


# ====================================
# 🔊 GENERAR VOZ
# ====================================

@app.post("/voz")
async def voz_endpoint(text: str = Form(...)):
    """Convierte texto a voz con gTTS"""
    tts = gTTS(text, lang="es")
    filename = "voz.mp3"
    tts.save(filename)
    return FileResponse(filename, media_type="audio/mpeg")


# ====================================
# 🌤️ CLIMA DIRECTO
# ====================================

@app.get("/clima")
def obtener_clima(ciudad: str = "Bogotá"):
    """Devuelve el clima actual de una ciudad"""
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude=4.61&longitude=-74.08&current_weather=true"
        response = requests.get(url)
        data = response.json()
        clima = data.get("current_weather", {})
        temperatura = clima.get("temperature", "desconocida")
        viento = clima.get("windspeed", "desconocido")
        return {"respuesta": f"En {ciudad} hay {temperatura}°C y viento de {viento} km/h."}
    except Exception as e:
        return {"respuesta": f"No pude obtener el clima: {str(e)}"}
