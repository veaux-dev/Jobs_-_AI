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
    You are a job search analist and advisor. You job is to go through job name and description and determine its seniority level.

    ⚠️ OUTPUT INSTRUCTIONS (critical):
    - Respond with **only one** of the following options.
    - Do **not** include explanations, reasoning, or extra words.
    - If uncertain, return '0-unclear'.
    - Your output will be parsed by a computer program; any deviation will cause an error.

    Valid options:
    - '1-entry' → Entry level (typically <5 years experience, junior, analyst, support role)
    - '2-experienced' → Individual contributor with more experience
    - '3-manager' → Leads a team, reports to a Director
    - '4-director' → Leads a function or regional team, reports to a VP
    - '5-vp+' → Executive role (VP, SVP, Head of Global, C-level)
    - '0-unclear' → Not enough information

    When in doubt, **downgrade** to the more conservative level.

    ---
    Job posting:
    {format_vacante(vacante)}
    ---

    ✅ Output **only one** of these options exactly:
    0-unclear, 1-entry, 2-experienced,3-manager,4-director or 5-vp+

    Answer strictly with one of the tokens above. 
    If you output anything else, your answer will be invalid and discarded.
    Therefore, ensure the **only** text you emit is one of the six valid labels.
    
    """

def prompt_info_empresa(nombre_empresa):
    return f"""
Act as a professional business analyst specialized in global industry classification.

OUTPUT RULES (MANDATORY):
- Return ONLY one valid JSON object. If you output anything other than a valid JSON object, it will be discarded. Automation downstream depend on these exact rules to be followed strictly.
- No text, no explanations, no markdown, no backticks. JSON only.
- The JSON must start with '{{' and end with '}}'.
- Use exactly these keys (in English): resumen_empresa, sector_empresa, tamaño_empresa, presencia_mexico, glassdoor_score.
- Each key must have ONE single value. Never use multiple values, lists, or combined strings (no slashes like "Tech / Consulting").
- Allowed values:
  - presencia_mexico: "Yes", "No", "Partial", or "No information".
  - glassdoor_score: number (e.g., 3.9) or "No information".
  - sector_empresa: MUST be exactly ONE of the following canonical values (do not combine or modify):

    1. "Energy / Oil & Gas / Power Generation"
    2. "Chemicals / Materials / Mining / Metals"
    3. "Industrial Manufacturing / Machinery / Automation"
    4. "Aerospace / Defense / Aviation / Space"
    5. "Automotive / Mobility / Transportation Equipment"
    6. "Electrical / Electronics / Semiconductors"
    7. "Engineering / Construction / Infrastructure"
    8. "Logistics / Supply Chain / Distribution / Transportation Services"
    9. "Technology / Software / IT / Automation Software / AI"
    10. "Consulting / Advisory / Professional Services"
    11. "Finance / Banking / Investment / Insurance"
    12. "Consumer Goods / Retail / FMCG / Apparel"
    13. "Food / Beverage / Agriculture / Food Processing"
    14. "Hospitality / Travel / Tourism / Leisure"
    15. "Healthcare / Medical Devices / Pharmaceuticals / Biotechnology"
    16. "Education / Government / Public Administration / NGOs"
    17. "Marketing / Media / Advertising / Events"
    18. "Real Estate / Construction Materials / Property Development"
    19. "Environmental / Sustainability / Recycling / Waste Management"
    20. "Miscellaneous / Diversified / Unknown"

DATA REQUIREMENTS:
- resumen_empresa: A short summary (1–3 lines) of what the company does.
- sector_empresa: The standardized macro-sector selected from the list above (only one value allowed).
- tamaño_empresa: "Small", "Medium", "Large", "Multinational", or "No information".
- presencia_mexico: "Yes", "No", "Partial", or "No information".
- glassdoor_score: Number from 1.0 to 5.0 if known, otherwise "No information".

If "{nombre_empresa}" is not clearly a company (e.g., an event, a person, or a product) or if the information is unreliable, set ALL fields to "No information".

EXPECTED OUTPUT FORMAT (example):

{{
"resumen_empresa": "French multinational specializing in aircraft engines and defense systems.",
"sector_empresa": "Aerospace / Defense / Aviation / Space",
"tamaño_empresa": "Multinational",
"presencia_mexico": "Yes",
"glassdoor_score": 3.9
}}
"""

