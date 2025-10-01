import subprocess

# ✅ Ruta absoluta al ejecutable de Ollama (ajústala si cambia)
OLLAMA_PATH = 'C:\\Users\\Aizen\\AppData\\Local\\Programs\\Ollama\\ollama.exe'

def ejecutar_ollama(prompt, modelo='gemma3'):
    """
    Ejecuta una consulta en Ollama usando el modelo especificado (ej: 'gemma' o 'deepseek').    
    """

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



def evaluar_booleano(prompt, modelo='gemma3'):
    """
    Llama al modelo y trata de interpretar si la respuesta fue un 'sí' o 'no'.
    """
    respuesta = ejecutar_ollama(prompt, modelo=modelo).lower()
    if 'sí' in respuesta or 'yes' in respuesta:
        return True
    if 'no' in respuesta:
        return False
    return None  # para que puedas detectar casos ambiguos o errores