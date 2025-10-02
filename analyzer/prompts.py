"""
prompts.py

Colección de templates de prompts para el LLM, específicos al dominio de vacantes y empresas.

Funciones:
- prompt_procurement(vacante): prompt para clasificar si la vacante es de Procurement.
- prompt_fit_usuario(vacante): prompt para evaluar encaje con el perfil del usuario.
- prompt_nivel(vacante): prompt para estimar nivel de seniority.
- prompt_info_empresa(nombre_empresa): prompt para generar resumen ejecutivo de una empresa.

Mantener los prompts centralizados aquí facilita ajustes finos y reusabilidad.
"""


def format_vacante(vacante):
    return f"""Job Title: {vacante['title'].strip()}

    Job Description:
    {vacante['full_text'].strip()}
    """



def prompt_fit_usuario(vacante):
    return f"""
    You are a job search advisor specialized in helping senior procurement executives.

    Your client is a Procurement Director with 20 years of experience in global companies. His expertise includes strategic sourcing, supplier management, category management, contract negotiations, procurement involvement in product launches (NPI), and supplier/supply risk mitigation. He has worked in the energy, aerospace, and automotive sectors, and is fluent in French, English, and Spanish.

    Your job is to assess job postings and determine whether they are **truly worth considering** based on their professional relevance, potential impact, and alignment with your client's core strengths.

    Focus your evaluation **only on the responsibilities, main functions, and core focus of the role**. Ignore the country, language, or location.

    ⚠️ Important:
    - Only answer 'yes' if the role includes **direct responsibility over procurement, strategic sourcing, or supplier management**.
    - Do NOT answer 'yes' if the role only interacts with those areas but is primarily focused on engineering, product, manufacturing, or general operations.
    - Ignore surface-level mentions like “collaborates with sourcing” or “supports procurement” if the role is not directly accountable for those functions.

    ---
    Job posting:
    {format_vacante(vacante)}
    ---

    Do you believe this job is a good match for this senior procurement executive to seriously consider?

    Answer ONLY with 'yes' or 'no'.
"""

def prompt_procurement(vacancy):
    return f"""
    Analyze the following job description and determine if the position is primarily focused on procurement, strategic sourcing, category management, or supplier management. 

    For clarity:
    - Procurement means acquiring goods and services for a company’s internal operations and value chain. 
    - This includes: strategic sourcing, category management, supplier evaluation and selection, supplier relationship management, contract negotiation, cost reduction, risk management, and supply continuity. 
    - Typical job titles: Buyer, Senior Buyer, Procurement Specialist, Category Manager, Sourcing Manager, Procurement Manager, Supplier Relationship Manager, Director of Procurement, VP of Sourcing. 

    It does NOT include:
    - Sales, business development, customer acquisition, account management, or growth roles.
    - Recruiting/talent sourcing or HR-related sourcing.
    - Roles where “sourcing” refers to finding new clients, leads, or revenue.
    - Consulting roles that only advise without owning the procurement process.

    Decision rule:
    - If the role clearly matches procurement as defined above → answer 'yes'.
    - If the role is ambiguous, mixed with sales, or unrelated → answer 'no'.
    - I am looking for a STRONG correlation, where the ideal candidate is unmistakably a procurement professional.

    ---
    {format_vacante(vacancy)}
    ---

    Answer ONLY with 'yes' or 'no'.
    """

def prompt_nivel(vacante):
    return f"""
    Analyze this job posting and determine its primary seniority level.

    Choose **only one** of the following options. If it is not clear, output '0-unclear':

    - 1-entry: Entry level. Typically less than 5 years of experience required. Individual contributor. Junior analyst or support role.  
    - 2-experienced: Still an individual contributor (no direct reports) but for more experienced professionals.  
    - 3-manager: Leads a team, but reports to a Director.  
    - 4-director: Leads a function or regional team, reports to a VP.  
    - 5-vp+: Executive leadership role such as Vice President, Senior Vice President, Head of Global, or equivalent.  

    Base your conclusion on both the job title and the description. When in doubt, be conservative and downgrade the level.

    ---
    Title: {vacante['title'].strip()}

    Description:
    {vacante['full_text'].strip()}
    ---

    Output MUST BE EXACTLY one of: 0-unclear, 1-entry, 2-experienced, 3-manager, 4-director, or 5-vp+
    """

def prompt_info_empresa(nombre_empresa):
    return f"""
    Act as a professional business analyst with high standards.

    OUTPUT RULES (MANDATORY):
    - Return ONLY one valid JSON object. If you output anything other than a valid JSON object, it will be discarded.
    - No text, no explanations, no markdown, no backticks. JSON only.
    - The JSON must start with '{{' and end with '}}'.
    - Use exactly these keys (in Spanish): resumen_empresa, sector_empresa, tamaño_empresa, presencia_mexico, glassdoor_score.
    - Allowed values:
    - presencia_mexico: "Yes", "No", "Partial", or "No information".
    - glassdoor_score: number (e.g., 3.9) or "No information". 
    - If "{nombre_empresa}" is not clearly a company (e.g., an event, a person, a product) or if the information is not reliable, set the fields to "No information".
    - Do not invent or speculate.

    DATA REQUIREMENTS:
    - resumen_empresa: A short summary (1 to 3 lines) of what the company does.
    - sector_empresa: The main industry (e.g., aerospace, technology, logistics).
    - tamaño_empresa: Small, Medium, Large, Multinational, or "No information". This is the overall size of the company
    - presencia_mexico: Presence in Mexico → "Yes", "No", "Partial", or "No information".
    - glassdoor_score: Number from 1.0 to 5.0 if known, otherwise "No information". This is the company score from Glassdoor.

    EXPECTED OUTPUT FORMAT (example):

    {{
    "resumen_empresa": "French company specialized in aircraft engines and defense.",
    "sector_empresa": "Aerospace",
    "tamaño_empresa": "Multinational",
    "presencia_mexico": "Yes",
    "glassdoor_score": 3.9
    }}
    """