from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from conversational_agent5 import ConversationalAgent
from gtts import gTTS
import pandas as pd
from fastapi.staticfiles import StaticFiles
import matplotlib.pyplot as plt
import requests
import os
import glob

app = FastAPI()
agent = ConversationalAgent()

# 🔓 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🏠 FRONTEND
@app.get("/")
def root():
    with open("frontend.html", encoding="utf-8") as f:
        return HTMLResponse(f.read())
app.mount("/static", StaticFiles(directory="."), name="static")
# 💬 CHAT PRINCIPAL (DETECTA TODAS LAS INTENCIONES)
@app.post("https://orionxgemini.onrender.com/chat")
async def chat(user_message: str = Form(...)):
    mensaje = user_message.lower()
    graphic = None

    # --- SALUDO ---
    if any(p in mensaje for p in ["hola", "buenos días", "buenas", "hey", "qué tal"]):
        texto_respuesta = "¡Hola! 👋 Soy tu agente conversacional. Puedo ayudarte con gráficos, voz, clima, traducción, búsqueda web y más."

    # --- CLIMA ---
    elif "clima" in mensaje or "temperatura" in mensaje:
        try:
            url = "https://api.open-meteo.com/v1/forecast?latitude=4.61&longitude=-74.08&current_weather=true"
            response = requests.get(url)
            data = response.json()
            clima = data.get("current_weather", {})
            temperatura = clima.get("temperature", "desconocida")
            viento = clima.get("windspeed", "desconocido")
            texto_respuesta = f"En Bogotá hay {temperatura}°C y viento de {viento} km/h 🌤️."
        except Exception as e:
            texto_respuesta = f"No pude obtener el clima: {str(e)}"

    # --- VOZ ---
    elif "voz" in mensaje:
        texto_respuesta = "Puedes usar la herramienta de voz diciendo: voz: Hola, ¿cómo estás?"

    # --- SCRAPING ---
    elif "scrapear" in mensaje or "extraer datos" in mensaje:
        texto_respuesta = "Para hacer scraping, escribe: scrape: https://ejemplo.com"

    # --- TRADUCCIÓN ---
    elif "traducir" in mensaje:
        texto_respuesta = "Para traducir, escribe: traducir: texto al idioma destino (por ejemplo: traducir hola al inglés)"

    # --- CÁLCULO ---
    elif "calcular" in mensaje or "cuánto es" in mensaje:
        texto_respuesta = "Para cálculos, escribe: calcular: 5 * 8 + 3"

    # --- GRAFICOS CSV ---
        # --- GRAFICOS CSV PERSONALIZADOS ---
        # --- GRAFICOS CSV PERSONALIZADOS ---
    elif "gráfico" in mensaje or "grafico" in mensaje or "visualizar" in mensaje:
        csv_files = glob.glob("*.csv")
        if not csv_files:
            texto_respuesta = "❌ No encontré ningún archivo CSV cargado. Sube uno primero."
        else:
            latest_csv = max(csv_files, key=os.path.getmtime)
            try:
                df = pd.read_csv(latest_csv)
                df.columns = df.columns.str.strip().str.lower()  # Normaliza nombres
                mensaje_lower = mensaje.lower()

                # 🔍 Detectar tipo de gráfico
                tipo = "line"
                if "barras" in mensaje_lower:
                    tipo = "bar"
                elif "líneas" in mensaje_lower or "lineas" in mensaje_lower:
                    tipo = "line"
                elif "pastel" in mensaje_lower or "pie" in mensaje_lower:
                    tipo = "pie"

                # 🧠 Extraer X y Y del mensaje
                x_col = None
                y_cols = []
                if "x=" in mensaje_lower:
                    x_col = mensaje_lower.split("x=")[1].split(",")[0].strip()
                if "y=" in mensaje_lower:
                    parte_y = mensaje_lower.split("y=")[1]
                    y_cols = [col.strip() for col in parte_y.replace("y=", "").split(",") if col.strip()]

                # 📊 Crear el gráfico
                plt.figure(figsize=(8, 4))

                if tipo == "pie":
                    # Gráfico de pastel (solo usa Y)
                    if y_cols:
                        y = y_cols[0]
                        df[y].value_counts().plot.pie(autopct='%1.1f%%')
                        plt.ylabel('')
                    else:
                        df[df.columns[0]].value_counts().plot.pie(autopct='%1.1f%%')
                        plt.ylabel('')
                elif x_col and y_cols:
                    # Si el usuario especifica X e Y
                    for y in y_cols:
                        if tipo == "bar":
                            plt.bar(df[x_col], df[y], label=y)
                        else:
                            plt.plot(df[x_col], df[y], marker='o', label=y)
                    plt.xlabel(x_col)
                    plt.ylabel(", ".join(y_cols))
                    plt.legend()
                else:
                    # Gráfico automático con columnas numéricas
                    df.select_dtypes("number").plot(kind=tipo)
                
                plt.title(f"Gráfico tipo {tipo} generado con '{latest_csv}'")
                plt.tight_layout()
                filename = "grafico.png"
                plt.savefig(filename)
                plt.close()
                graphic = filename
                texto_respuesta = f"📈 Gráfico ({tipo}) generado correctamente usando '{latest_csv}'."
            except Exception as e:
                texto_respuesta = f"⚠️ Ocurrió un error al generar el gráfico: {str(e)}"



    # --- DEFAULT (usa el modelo conversacional)
    else:
        texto_respuesta = agent.chat(user_message)
        files = [f for f in os.listdir('.') if f.endswith('.png')]
        if files:
            graphic = max(files, key=os.path.getmtime)

    return JSONResponse({"response": texto_respuesta, "graphic": graphic})


# 📂 SUBIR ARCHIVO CSV
@app.post("https://orionxgemini.onrender.com/upload")
async def upload(file: UploadFile = File(...)):
    out = file.filename
    with open(out, "wb") as f:
        f.write(await file.read())
    return {"filename": out}


# 🖼️ SERVIR IMÁGENES
@app.get("https://orionxgemini.onrender.com/image/{name}")
def image(name: str):
    return FileResponse(os.path.abspath(name))


# 🔊 VOZ
@app.post("https://orionxgemini.onrender.com/voz")
async def voz_endpoint(text: str = Form(...)):
    tts = gTTS(text, lang="es")
    filename = "voz.mp3"
    tts.save(filename)
    return FileResponse(filename, media_type="audio/mpeg")


# 🌐 SCRAPE
@app.post("https://orionxgemini.onrender.com/scrape")
async def scrape_endpoint(url: str = Form(...)):
    result = agent.scrape(url)
    return {"response": result}


# 🔍 BUSCAR WEB
@app.post("https://orionxgemini.onrender.com/buscar")
async def buscar_endpoint(query: str = Form(...)):
    result = agent.search(query)
    return {"response": result}


# 🌎 TRADUCIR
@app.post("https://orionxgemini.onrender.com/traducir")
async def traducir_endpoint(text: str = Form(...), target: str = Form("en")):
    result = agent.translate(text, target)
    return {"response": result}


# ➗ CALCULAR
@app.post("https://orionxgemini.onrender.com/calcular")
async def calcular_endpoint(expr: str = Form(...)):
    result = agent.calculate(expr)
    return {"response": result}


# 🌤️ CLIMA DIRECTO
@app.get("https://orionxgemini.onrender.com/clima")
def obtener_clima(ciudad: str = "Bogotá"):
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



