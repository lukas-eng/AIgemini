"""
Agente Conversacional con Herramientas Expandidas
Versión conectada a Gemini API (sin Ollama)
"""

import json
import requests
import pyttsx3
import matplotlib.pyplot as plt
from datetime import datetime
from typing import Optional, Dict, Any
from deep_translator import GoogleTranslator
import threading
from bs4 import BeautifulSoup
import csv
import os
import pandas as pd
from dotenv import load_dotenv
import google.generativeai as genai
import re
import time

# ============================================
# CONFIGURACIÓN GEMINI
# ============================================

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# 🔁 Modelo más liviano y rápido (menos restricciones de cuota)
model = genai.GenerativeModel("models/gemini-2.5-flash")

# ============================================
# HERRAMIENTAS DISPONIBLES
# ============================================

class ToolKit:
    """Conjunto de herramientas que el agente puede usar"""

    def __init__(self):
        try:
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', 150)
            self.tts_engine.setProperty('volume', 0.9)
            self.tts_available = True
        except:
            self.tts_available = False
            print("⚠️ TTS no disponible")

    def search_web(self, query: str) -> str:
        try:
            url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
            response = requests.get(url, timeout=3)
            data = response.json()
            abstract = data.get('Abstract', '')
            if abstract:
                return abstract
            topics = data.get('RelatedTopics', [])
            if topics:
                return "\n".join(t.get("Text", "") for t in topics[:3])
            return "No se encontró información relevante."
        except Exception as e:
            return f"Error al buscar: {str(e)}"

    def get_weather(self, city="Bogotá") -> str:
        try:
            url = f"https://wttr.in/{city}?format=j1"
            r = requests.get(url, timeout=3)
            d = r.json()
            current = d['current_condition'][0]
            return f"{city}: {current['temp_C']}°C, {current['weatherDesc'][0]['value']}, humedad {current['humidity']}%"
        except Exception as e:
            return f"No pude obtener el clima: {str(e)}"

    def calculate(self, expression):
        try:
            allowed = "0123456789+-*/(). "
            if not all(c in allowed for c in expression):
                return "Expresión inválida."
            return f"Resultado: {eval(expression)}"
        except Exception as e:
            return f"Error: {str(e)}"

    def translate_text(self, text, target="en"):
        try:
            return GoogleTranslator(source='auto', target=target).translate(text)
        except Exception as e:
            return f"Error al traducir: {str(e)}"

    def create_chart_from_csv(self, csv_file, chart_type="bar", x_column=None, y_column=None):
        try:
            df = pd.read_csv(csv_file)
            if x_column is None: x_column = df.columns[0]
            if y_column is None: y_column = df.columns[1]
            labels, values = df[x_column].astype(str), df[y_column]

            filename = f"grafico_{chart_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.figure(figsize=(10, 6))
            if chart_type == "bar":
                plt.bar(labels, values, color="skyblue")
            elif chart_type == "pie":
                plt.pie(values, labels=labels, autopct="%1.1f%%")
            elif chart_type == "line":
                plt.plot(labels, values, marker="o", color="green")
            plt.title(f"{chart_type.upper()} - {csv_file}")
            plt.savefig(filename, bbox_inches="tight")
            plt.close()
            return f"Gráfico creado: {filename}"
        except Exception as e:
            return f"Error: {str(e)}"


# ============================================
# AGENTE CONVERSACIONAL (GEMINI)
# ============================================

class ConversationalAgent:
    def __init__(self):
        self.toolkit = ToolKit()
        self.history = []

    def chat(self, user_message):
        lower_msg = user_message.lower()

        # --- Detección de CSV para gráfico ---
        if ".csv" in lower_msg and any(p in lower_msg for p in ["grafico","gráfico","barras","pie","circular","linea","línea"]):
            match = re.search(r"([\w\-_.]+\.csv)", user_message)
            if match:
                csv_file = match.group(1)
                res = self.toolkit.create_chart_from_csv(csv_file)
                return res
            return "No se encontró el archivo CSV."

        # --- Procesar con Gemini (con auto-reintento en caso de 429) ---
        try:
            response = model.generate_content(user_message)
            return response.text.strip()
        except Exception as e:
            err = str(e)
            if "429" in err or "quota" in err.lower():
                print("⚠️ Límite alcanzado, esperando 45 segundos para reintentar...")
                time.sleep(45)
                try:
                    response = model.generate_content(user_message)
                    return response.text.strip()
                except Exception as e2:
                    return f"Error persistente tras reintento: {str(e2)}"
            return f"Error al usar Gemini: {err}"


# ============================================
# CLI (modo terminal)
# ============================================

if __name__ == "__main__":
    print("🤖 Agente conectado a Gemini listo (modelo: gemini-2.5-flash).")
    agent = ConversationalAgent()

    while True:
        user_input = input("\nTú: ")
        if user_input.lower() in ["salir", "exit", "quit"]:
            print("👋 Adiós.")
            break
        print("Agente:", agent.chat(user_input))
