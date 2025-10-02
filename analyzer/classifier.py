from db_utils import fetch_all_vacantes, update_vacante_fields, insert_or_update_empresa, get_empresas_pendientes
from prompts import prompt_procurement, prompt_fit_usuario, prompt_nivel, prompt_info_empresa
from llm_wrapper import evaluar_booleano, evaluar_con_llm
from datetime import datetime
import json

DEFAULT_MODEL = 'gemma3'

def es_procurement(vacante):
    """Clasifica si una vacante pertenece a Procurement usando LLM."""
    if not vacante['full_text'].strip():
        return None
    return evaluar_booleano(prompt_procurement(vacante), modelo=DEFAULT_MODEL)

def es_fit_usuario(vacante):
    """Evalúa si la vacante encaja con el perfil del usuario usando LLM."""
    if not vacante['full_text'].strip():
        return None
    return evaluar_booleano(prompt_fit_usuario(vacante), modelo=DEFAULT_MODEL)

def estimar_nivel(vacante):
    """Estima nivel de seniority (entry, manager, director, VP+) usando LLM."""
    if not vacante['full_text'].strip():
        return None
    nivel = evaluar_con_llm(prompt_nivel(vacante), modelo=DEFAULT_MODEL).strip().lower()
    if nivel in ['0-unclear','1-entry', '2-experienced', '3-manager', '4-director', '5-vp+']:
        return nivel
    return None

def clasificar_vacantes(force=False):
    """Clasifica todas las vacantes nuevas/en proceso y guarda resultados usando LLM."""
    vacantes = fetch_all_vacantes()
    print(f"🧠 Clasificando {len(vacantes)} vacantes...")

    for vac in vacantes:
        id_ = vac['job_hash']
        cambios = {}

        if force or vac['es_procurement'] is None:
            cambios['es_procurement'] = es_procurement(vac)
            print(f"[{id_}] es_procurement: {cambios['es_procurement']}")

      
        if force or vac['es_fit_usuario'] is None:
            cambios['es_fit_usuario'] = es_fit_usuario(vac)
            print(f"[{id_}] es_fit_usuario: {cambios['es_fit_usuario']}")

        if force or vac['nivel_estimado'] is None:
            cambios['nivel_estimado'] = estimar_nivel(vac)
            print(f"[{id_}] nivel_estimado: {cambios['nivel_estimado']}")

        if any(k in cambios for k in ['es_procurement', 'es_fit_usuario', 'nivel_estimado']):
            cambios['processed_at'] = datetime.today().strftime('%Y-%m-%d')

        if cambios:
            update_vacante_fields(id_, cambios)

def extraer_info_empresa(nombre_empresa, modelo=DEFAULT_MODEL):
    """Genera info ejecutiva de una empresa usando LLM y devuelve dict."""
    prompt = prompt_info_empresa(nombre_empresa)
    respuesta = evaluar_con_llm(prompt, modelo=modelo)

    # Detectar bloque JSON si viene en formato markdown
    if "```json" in respuesta:
        respuesta = respuesta.split("```json")[1].split("```")[0].strip()

    try:
        data = json.loads(respuesta)
    except json.JSONDecodeError:
        print(f"❌ Error al parsear JSON para {nombre_empresa}: {respuesta}")
        return None

    return {
        "company": nombre_empresa,
        "resumen_empresa": data.get("resumen_empresa", "Sin información"),
        "sector_empresa": data.get("sector_empresa", "Sin información"),
        "tamaño_empresa": data.get("tamaño_empresa", "Sin información"),
        "presencia_mexico": data.get("presencia_mexico", "Sin información"),
        "glassdoor_score": data.get("glassdoor_score") if isinstance(data.get("glassdoor_score"), (int, float)) else None,
        "last_updated": datetime.today().strftime('%Y-%m-%d')
    }


def clasificar_empresas(report_callback=None, force=False):
    """Enriquece la tabla `empresas` con información ejecutiva vía LLM.

    Args:
        report_callback (dict, opcional): objetos de UI como {'progress': ..., 'status': ...}
        force (bool): si True, reprocesa todas las empresas. Si False, solo las que tengan campos vacíos.
    """

    # 1. Seleccionar empresas según modo
    empresas_pendientes = get_empresas_pendientes(force)
    total = len(empresas_pendientes)
    print(f"🧠 Clasificando {total} empresas{' (FORCE)' if force else ''}...")

       # 2. Configuración opcional de UI
    progress = status = None
    if report_callback:
        progress = report_callback.get('progress')
        status = report_callback.get('status')

    # 3. Loop principal
    for i, empresa in enumerate(empresas_pendientes, start=1):
        if status:
            status.text(f"Procesando: {empresa} ({i}/{total})")
        if progress:
            progress.progress(i / total)

        info = extraer_info_empresa(empresa)
        if info:
            insert_or_update_empresa(info)

    # 4. UI al terminar
    if status:
        status.text("✅ Clasificación de empresas completada.")
    if progress:
        progress.progress(1.0)
