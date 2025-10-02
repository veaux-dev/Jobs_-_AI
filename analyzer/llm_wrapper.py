"""
llm_wrapper.py

Módulo centralizado para interactuar con el modelo LLM (Ollama/Gemma/Deepseek).
Encapsula las llamadas de inferencia y el postprocesamiento básico de respuestas.

Funciones:
- evaluar_booleano(prompt, modelo): evalúa un prompt con salida booleana.
- evaluar_con_llm(prompt, modelo): evalúa un prompt con salida libre en texto.

Este módulo permite desacoplar la lógica de negocio de la implementación concreta del modelo.
Si se cambia de motor (Ollama → OpenAI → HuggingFace), solo este archivo debe modificarse.
"""


import subprocess
import unicodedata

OLLAMA_PATH = None

def set_ollama_path(path):
    global OLLAMA_PATH
    OLLAMA_PATH = path

def ejecutar_ollama(prompt, modelo='gemma3'):
    """
    Ejecuta una consulta en Ollama usando el modelo especificado (ej: 'gemma' o 'deepseek').    
    """

    if not OLLAMA_PATH:
        raise RuntimeError("OLLAMA_PATH no ha sido configurado. Llama a set_ollama_path(path) antes de usar ejecutar_ollama().")

    try:
        resultado = subprocess.run(
            [OLLAMA_PATH, 'run', modelo],
            input=prompt.encode('utf-8'),
            capture_output=True,
            timeout=60
        )
        respuesta = resultado.stdout.decode('utf-8').strip()
        return respuesta
    except Exception as e:
        return f"[ERROR] LLM execution failed: {str(e)}"
    


def evaluar_con_llm(prompt, modelo='gemma3'):
    """
    Llama al modelo y retorna la respuesta completa (texto completo).
    """
    return ejecutar_ollama(prompt, modelo=modelo)



def normalize(text: str) -> str:
    """
    Normaliza un texto eliminando acentos y pasando todo a minúsculas.
    Ejemplo:
        "Sí" -> "si"
        "NO" -> "no"
    """
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    ).lower()


def evaluar_booleano(prompt, modelo='gemma3'):
    """
    Llama al modelo y trata de interpretar si la respuesta fue un 'sí' o 'no'.
    Normaliza la salida para evitar problemas con acentos o mayúsculas.
    """
    respuesta = normalize(ejecutar_ollama(prompt, modelo=modelo))

    if 'si' in respuesta or 'yes' in respuesta or 'true' in respuesta:
        return True
    if 'no' in respuesta or 'false' in respuesta:
        return False
    return None  # para detectar casos ambiguos o respuestas raras