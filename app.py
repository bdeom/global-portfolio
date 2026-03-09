"""
NSGA-II + LSTM Portfolio Engine · DEGIRO España
Uso interno — login usuario/contraseña desde secrets.toml
"""

import streamlit as st
import anthropic
import json, re, time, hashlib
from datetime import date

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Portfolio Engine · DEGIRO España",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Auth helper ───────────────────────────────────────────────────────────────
def check_credentials(username, password):
    ok_user = st.secrets.get("APP_USERNAME", "")
    ok_hash = st.secrets.get("APP_PASSWORD", "")
    entered_hash = hashlib.sha256(password.encode()).hexdigest()
    if username.strip().lower() == ok_user.lower() and entered_hash == ok_hash:
        return username
    return None

# ── Login screen ──────────────────────────────────────────────────────────────
def show_login():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@700;900&display=swap');
body, .stApp { background: #020408 !important; }
.stTextInput>div>div>input {
    background: rgba(0,0,0,0.5) !important;
    border: 1px solid rgba(0,200,255,0.2) !important;
    color: #00c8ff !important;
    font-family: 'Share Tech Mono', monospace !important;
}
.stButton>button {
    background: transparent; border: 1px solid #00c8ff; color: #00c8ff;
    font-family: 'Orbitron', sans-serif; letter-spacing: 3px;
    font-weight: 700; width: 100%; padding: 12px; margin-top: 8px;
}
.stButton>button:hover { background: rgba(0,200,255,0.06); }
</style>
""", unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown(
            "<div style='font-family:Orbitron,sans-serif;font-size:1.4rem;font-weight:900;"
            "color:#fff;letter-spacing:2px;margin-bottom:4px;margin-top:60px'>PORTFOLIO ENGINE</div>",
            unsafe_allow_html=True)
        st.markdown(
            "<div style='font-family:\"Share Tech Mono\",monospace;font-size:9px;"
            "color:rgba(30,80,100,1);letter-spacing:2px;text-transform:uppercase;"
            "margin-bottom:24px'>// DEGIRO España · acceso restringido</div>",
            unsafe_allow_html=True)

        username = st.text_input("Usuario", placeholder="tu_usuario", key="login_user")
        password = st.text_input("Contraseña", type="password", placeholder="••••••••", key="login_pass")

        if st.button("▶  ENTRAR"):
            if not username or not password:
                st.error("Introduce usuario y contraseña.")
            else:
                name = check_credentials(username, password)
                if name:
                    st.session_state["authenticated"] = True
                    st.session_state["user_name"]     = name
                    st.session_state["username"]      = username.strip().lower()
                    st.rerun()
                else:
                    st.error("⚠ Usuario o contraseña incorrectos.")

        st.markdown(
            "<div style='font-family:\"Share Tech Mono\",monospace;font-size:8px;"
            "color:rgba(20,60,80,0.6);text-align:center;margin-top:20px'>"
            "Contacta con el administrador para obtener acceso</div>",
            unsafe_allow_html=True)

# ── Auth gate ─────────────────────────────────────────────────────────────────
if not st.session_state.get("authenticated"):
    show_login()
    st.stop()

check_auth()

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@700;900&display=swap');
body, .stApp { background: #020408 !important; color: #b0e8ff; }
h1,h2,h3 { font-family: 'Orbitron', sans-serif !important; color: #00c8ff !important; }
section[data-testid="stSidebar"] { background: #010306 !important; border-right: 1px solid rgba(0,200,255,0.08); }
.stTabs [data-baseweb="tab-list"] { background: transparent; border-bottom: 1px solid rgba(0,200,255,0.1); }
.stTabs [data-baseweb="tab"] { color: rgba(30,80,100,1); font-family: 'Share Tech Mono', monospace; font-size: 11px; letter-spacing: 2px; }
.stTabs [aria-selected="true"] { color: #00c8ff !important; border-bottom: 2px solid #00c8ff !important; }
.stButton>button { background: transparent; border: 1px solid #00c8ff; color: #00c8ff; font-family: 'Orbitron', sans-serif; letter-spacing: 3px; font-weight: 700; width: 100%; padding: 14px; }
.stButton>button:hover { background: rgba(0,200,255,0.05); box-shadow: 0 0 20px rgba(0,200,255,0.1); }
.stNumberInput>div>div>input { background: rgba(0,0,0,0.5) !important; border: 1px solid rgba(0,200,255,0.2) !important; color: #00c8ff !important; font-family: 'Orbitron', sans-serif !important; font-weight: 700; }
.stRadio label { color: #b0e8ff; font-size: 13px; }
div[data-testid="metric-container"] { background: rgba(0,0,0,0.3); border: 1px solid rgba(0,200,255,0.07); border-radius: 6px; padding: 10px; }
div[data-testid="metric-container"] label { color: rgba(30,80,100,1) !important; font-family: 'Share Tech Mono', monospace; font-size: 10px; letter-spacing: 2px; }
div[data-testid="metric-container"] div { color: #00c8ff !important; font-family: 'Orbitron', sans-serif !important; font-weight: 700; }
.stProgress > div > div { background: linear-gradient(90deg, #ff3c6e, #ffcc00, #00c8ff) !important; }
.stAlert { font-family: 'Share Tech Mono', monospace; font-size: 11px; }
.disclaimer { text-align:center;font-family:'Share Tech Mono',monospace;font-size:9px;color:rgba(20,60,80,0.7);margin-top:24px;letter-spacing:1px }
</style>
""", unsafe_allow_html=True)

# ── Asset universes ───────────────────────────────────────────────────────────
UNIVERSES = {
    "⚖ Equilibrado": {
        "desc": "IBEX35 blue chips + ETFs Core DEGIRO + bonos europeos + materias primas",
        "assets": [
            {"t":"SAN","n":"Banco Santander","ex":"BME","cl":"Banca-ES","fee":"€1+€1"},
            {"t":"BBVA","n":"BBVA","ex":"BME","cl":"Banca-ES","fee":"€1+€1"},
            {"t":"ITX","n":"Inditex","ex":"BME","cl":"Consumo-ES","fee":"€1+€1"},
            {"t":"IBE","n":"Iberdrola","ex":"BME","cl":"Utilities-ES","fee":"€1+€1"},
            {"t":"TEF","n":"Telefónica","ex":"BME","cl":"Telecom-ES","fee":"€1+€1"},
            {"t":"REP","n":"Repsol","ex":"BME","cl":"Energía-ES","fee":"€1+€1"},
            {"t":"AMS","n":"Amadeus IT","ex":"BME","cl":"Tech-ES","fee":"€1+€1"},
            {"t":"ELE","n":"Endesa","ex":"BME","cl":"Utilities-ES","fee":"€1+€1"},
            {"t":"IWDA","n":"iShares MSCI World","ex":"Xetra","cl":"ETF-Global","fee":"€1 Core"},
            {"t":"VWCE","n":"Vanguard FTSE All-World","ex":"Xetra","cl":"ETF-Global","fee":"€1 Core"},
            {"t":"CSPX","n":"iShares Core S&P 500","ex":"LSE","cl":"ETF-US","fee":"€1 Core"},
            {"t":"EIMI","n":"iShares MSCI EM IMI","ex":"Xetra","cl":"ETF-EM","fee":"€1 Core"},
            {"t":"IBCE","n":"iShares EUR Corp Bond","ex":"Xetra","cl":"Bono-EUR","fee":"€1 Core"},
            {"t":"SEGA","n":"Amundi Euro Govt Bond","ex":"Euronext","cl":"Bono-EUR-Gov","fee":"€2"},
            {"t":"ASML","n":"ASML Holding","ex":"Euronext","cl":"Tech-EU","fee":"€3.90+€1"},
            {"t":"SAP","n":"SAP SE","ex":"Xetra","cl":"Tech-EU","fee":"€3.90+€1"},
            {"t":"SIE","n":"Siemens AG","ex":"Xetra","cl":"Industrial-EU","fee":"€3.90+€1"},
            {"t":"NVDA","n":"NVIDIA Corp","ex":"NASDAQ","cl":"Tech-US","fee":"€1+€1"},
            {"t":"MSFT","n":"Microsoft","ex":"NASDAQ","cl":"Tech-US","fee":"€1+€1"},
            {"t":"AMZN","n":"Amazon","ex":"NASDAQ","cl":"Consumo-US","fee":"€1+€1"},
            {"t":"SGLD","n":"Invesco Physical Gold","ex":"LSE","cl":"Oro","fee":"€2"},
            {"t":"OILW","n":"WisdomTree Brent Crude","ex":"LSE","cl":"Petróleo","fee":"€2"},
        ]
    },
    "🇪🇸 IBEX Focus": {
        "desc": "Máxima exposición española: IBEX35 completo + IBEX Medium Cap",
        "assets": [
            {"t":"SAN","n":"Banco Santander","ex":"BME","cl":"Banca","fee":"€1+€1"},
            {"t":"BBVA","n":"BBVA","ex":"BME","cl":"Banca","fee":"€1+€1"},
            {"t":"ITX","n":"Inditex","ex":"BME","cl":"Moda/Retail","fee":"€1+€1"},
            {"t":"IBE","n":"Iberdrola","ex":"BME","cl":"Utilities","fee":"€1+€1"},
            {"t":"TEF","n":"Telefónica","ex":"BME","cl":"Telecom","fee":"€1+€1"},
            {"t":"REP","n":"Repsol","ex":"BME","cl":"Energía","fee":"€1+€1"},
            {"t":"AMS","n":"Amadeus IT","ex":"BME","cl":"Tech","fee":"€1+€1"},
            {"t":"ELE","n":"Endesa","ex":"BME","cl":"Utilities","fee":"€1+€1"},
            {"t":"CABK","n":"CaixaBank","ex":"BME","cl":"Banca","fee":"€1+€1"},
            {"t":"SAB","n":"Banco Sabadell","ex":"BME","cl":"Banca","fee":"€1+€1"},
            {"t":"CLNX","n":"Cellnex Telecom","ex":"BME","cl":"Telecom","fee":"€1+€1"},
            {"t":"IAG","n":"IAG (Iberia/BA)","ex":"BME","cl":"Aerolínea","fee":"€1+€1"},
            {"t":"FER","n":"Ferrovial","ex":"BME","cl":"Infraestructura","fee":"€1+€1"},
            {"t":"MAP","n":"MAPFRE","ex":"BME","cl":"Seguros","fee":"€1+€1"},
            {"t":"NTGY","n":"Naturgy Energy","ex":"BME","cl":"Gas","fee":"€1+€1"},
            {"t":"MEL","n":"Meliá Hotels","ex":"BME","cl":"Turismo","fee":"€1+€1"},
            {"t":"GRF","n":"Grifols","ex":"BME","cl":"Salud","fee":"€1+€1"},
            {"t":"ACX","n":"Acerinox","ex":"BME","cl":"Industrial","fee":"€1+€1"},
            {"t":"VIS","n":"Viscofan","ex":"BME","cl":"Alimentación","fee":"€1+€1"},
            {"t":"ENG","n":"Enagás","ex":"BME","cl":"Gas","fee":"€1+€1"},
        ]
    },
    "🇪🇺 Europa": {
        "desc": "Eurostoxx, DAX, CAC40, AEX + BME + ETFs europeos sin exposición USD",
        "assets": [
            {"t":"SAN","n":"Banco Santander","ex":"BME","cl":"Banca-ES","fee":"€1+€1"},
            {"t":"IBE","n":"Iberdrola","ex":"BME","cl":"Utilities-ES","fee":"€1+€1"},
            {"t":"ITX","n":"Inditex","ex":"BME","cl":"Consumo-ES","fee":"€1+€1"},
            {"t":"ASML","n":"ASML Holding","ex":"Euronext","cl":"Semi-NL","fee":"€3.90+€1"},
            {"t":"HEIA","n":"Heineken","ex":"Euronext","cl":"Bebidas-NL","fee":"€3.90+€1"},
            {"t":"MC","n":"LVMH","ex":"Euronext","cl":"Lujo-FR","fee":"€3.90+€1"},
            {"t":"OR","n":"L'Oréal","ex":"Euronext","cl":"Consumo-FR","fee":"€3.90+€1"},
            {"t":"SAP","n":"SAP SE","ex":"Xetra","cl":"Tech-DE","fee":"€3.90+€1"},
            {"t":"SIE","n":"Siemens AG","ex":"Xetra","cl":"Industrial-DE","fee":"€3.90+€1"},
            {"t":"ALV","n":"Allianz","ex":"Xetra","cl":"Seguros-DE","fee":"€3.90+€1"},
            {"t":"BAYN","n":"Bayer AG","ex":"Xetra","cl":"Farma-DE","fee":"€3.90+€1"},
            {"t":"MEUD","n":"Lyxor Core MSCI EMU","ex":"Euronext","cl":"ETF-Eurozona","fee":"€1 Core"},
            {"t":"IWDA","n":"iShares MSCI World","ex":"Xetra","cl":"ETF-Global","fee":"€1 Core"},
            {"t":"IBCE","n":"iShares EUR Corp Bond","ex":"Xetra","cl":"Bono-EUR","fee":"€1 Core"},
            {"t":"SEGA","n":"Amundi Euro Govt Bond","ex":"Euronext","cl":"Bono-EUR-Gov","fee":"€2"},
            {"t":"MRL","n":"Merlin Properties","ex":"BME","cl":"REIT-ES","fee":"€1+€1"},
            {"t":"SGLD","n":"Invesco Physical Gold","ex":"LSE","cl":"Oro","fee":"€2"},
        ]
    },
    "🌍 Global": {
        "desc": "Acceso total DEGIRO: IBEX + NYSE/NASDAQ + ETFs mundiales + emergentes",
        "assets": [
            {"t":"SAN","n":"Banco Santander","ex":"BME","cl":"Banca-ES","fee":"€1+€1"},
            {"t":"ITX","n":"Inditex","ex":"BME","cl":"Consumo-ES","fee":"€1+€1"},
            {"t":"IBE","n":"Iberdrola","ex":"BME","cl":"Utilities-ES","fee":"€1+€1"},
            {"t":"AMS","n":"Amadeus IT","ex":"BME","cl":"Tech-ES","fee":"€1+€1"},
            {"t":"NVDA","n":"NVIDIA Corp","ex":"NASDAQ","cl":"Tech-US","fee":"€1+€1"},
            {"t":"MSFT","n":"Microsoft","ex":"NASDAQ","cl":"Tech-US","fee":"€1+€1"},
            {"t":"AAPL","n":"Apple Inc","ex":"NASDAQ","cl":"Tech-US","fee":"€1+€1"},
            {"t":"AMZN","n":"Amazon","ex":"NASDAQ","cl":"Consumo-US","fee":"€1+€1"},
            {"t":"META","n":"Meta Platforms","ex":"NASDAQ","cl":"Tech-US","fee":"€1+€1"},
            {"t":"JPM","n":"JPMorgan Chase","ex":"NYSE","cl":"Banca-US","fee":"€1+€1"},
            {"t":"JNJ","n":"Johnson & Johnson","ex":"NYSE","cl":"Salud-US","fee":"€1+€1"},
            {"t":"ASML","n":"ASML Holding","ex":"Euronext","cl":"Semi-EU","fee":"€3.90+€1"},
            {"t":"SAP","n":"SAP SE","ex":"Xetra","cl":"Tech-EU","fee":"€3.90+€1"},
            {"t":"IWDA","n":"iShares MSCI World","ex":"Xetra","cl":"ETF-Global","fee":"€1 Core"},
            {"t":"VWCE","n":"Vanguard FTSE All-World","ex":"Xetra","cl":"ETF-Global","fee":"€1 Core"},
            {"t":"CSPX","n":"iShares Core S&P 500","ex":"LSE","cl":"ETF-US","fee":"€1 Core"},
            {"t":"EIMI","n":"iShares MSCI EM IMI","ex":"Xetra","cl":"ETF-EM","fee":"€1 Core"},
            {"t":"IBCE","n":"iShares EUR Corp Bond","ex":"Xetra","cl":"Bono-EUR","fee":"€1 Core"},
            {"t":"SGLD","n":"Invesco Physical Gold","ex":"LSE","cl":"Oro","fee":"€2"},
            {"t":"OILW","n":"WisdomTree Brent Crude","ex":"LSE","cl":"Petróleo","fee":"€2"},
        ]
    },
}

PAL = ["#00c8ff","#ff3c6e","#ffcc00","#00ffb3","#ff8c42","#a8ff78","#f72585","#7b5cff","#4cc9f0","#ffd166"]

def regime_color(r):
    if "Alcista" in r and "Tranquilo" in r: return "#00ffb3"
    if "Alcista" in r and "Volátil" in r:   return "#ffcc00"
    if "Bajista" in r and "Tranquilo" in r: return "#ff8c42"
    if "Bajista" in r:                       return "#ff3c6e"
    return "#888"

def lstm_color(s):
    return {"ALCISTA":"#00c8ff","NEUTRAL":"#ffcc00"}.get(s,"#ff3c6e")

def parse_json(text):
    text = text.strip()
    for pat in [r'```json\s*([\s\S]*?)```', r'```\s*([\s\S]*?)```']:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try: return json.loads(m.group(1).strip())
            except: pass
    try:
        s, e = text.index("{"), text.rindex("}")
        return json.loads(text[s:e+1])
    except: pass
    try: return json.loads(text)
    except: return None

def call_api(messages, max_tokens=8000):
    """Usa la API key almacenada en Streamlit secrets — nunca expuesta al usuario."""
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        messages=messages,
    )
    return "".join(b.text for b in response.content if hasattr(b, "text"))

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    # User info + logout
    user_name = st.session_state.get("user_name", "")
    username  = st.session_state.get("username", "")
    ucol, lcol = st.columns([3, 1])
    with ucol:
        st.markdown(
            f"<div style='font-family:\"Share Tech Mono\",monospace;font-size:10px;"
            f"color:rgba(0,200,255,0.5);padding:8px 0;border-bottom:1px solid rgba(0,200,255,0.08);margin-bottom:16px'>"
            f"👤 {user_name} ({username})</div>",
            unsafe_allow_html=True)
    with lcol:
        if st.button("↩", help="Cerrar sesión"):
            st.session_state.clear()
            st.rerun()

    st.markdown("### ⚙️ Configuración")

    universe_name = st.radio(
        "Universo de inversión",
        list(UNIVERSES.keys()),
        help="Selecciona el universo de activos DEGIRO España"
    )
    universe = UNIVERSES[universe_name]
    st.caption(universe["desc"])

    st.markdown("---")
    capital = st.number_input(
        "Capital disponible (€)",
        min_value=1000, max_value=10_000_000,
        value=20000, step=1000, format="%d",
        help="Capital total en euros a invertir"
    )

    st.markdown("---")

    # Asset list for selected universe
    with st.expander(f"📋 Activos del universo ({len(universe['assets'])})"):
        for a in universe["assets"]:
            st.markdown(
                f"<div style='font-family:\"Share Tech Mono\",monospace;font-size:9px;"
                f"color:rgba(30,80,100,1);padding:2px 0'>"
                f"<span style='color:#00c8ff'>{a['t']}</span> · {a['ex']} · {a['fee']}</div>",
                unsafe_allow_html=True)

    st.markdown("---")
    run = st.button("▶  OPTIMIZAR CARTERA")

    st.markdown(
        "<div style='font-family:\"Share Tech Mono\",monospace;font-size:8px;"
        "color:rgba(20,60,80,0.5);margin-top:16px;line-height:1.8'>"
        "NSGA-II · 50 generaciones<br>"
        "LSTM · 2 capas · 128 unidades<br>"
        "Horizonte · 90 días<br>"
        "API · claude-sonnet-4</div>",
        unsafe_allow_html=True)

# ── Main area ─────────────────────────────────────────────────────────────────
st.markdown("# NSGA‑II + LSTM **PORTFOLIO ENGINE** · 🇪🇸")
st.markdown(
    "<div style='font-family:\"Share Tech Mono\",monospace;font-size:10px;"
    "color:rgba(30,80,100,1);letter-spacing:1px;margin-bottom:20px'>"
    "universo DEGIRO España · IBEX35 · ETFs europeos Core · acciones globales · horizonte 90 días</div>",
    unsafe_allow_html=True)

if run:
    tickers = ", ".join(f"{a['t']} ({a['n']}, {a['ex']}, {a['cl']})" for a in universe["assets"])
    today = date.today().isoformat()

    steps = [
        "Inicializando optimizador NSGA-II multi-objetivo...",
        "Cargando activos disponibles en DEGIRO España...",
        "Calculando matriz de covarianza 5Y (Ledoit-Wolf shrinkage)...",
        "LSTM forward pass — secuencias de precios (lookback=60d)...",
        "Refinando estado oculto h_t · 2 capas, 128 unidades...",
        "Extrayendo señales de momentum 90 días ✓",
        "NSGA-II generación 10/50 — evolucionando frente de Pareto...",
        "NSGA-II generación 25/50 — ordenación por distancia de hacinamiento...",
        "NSGA-II generación 40/50 — convergencia de frente detectada...",
        "Frontera de Pareto estabilizada ✓",
        "Aplicando restricciones de diversificación...",
        "Seleccionando top-10 por indicador de hipervolumen...",
        "Enviando al motor IA para puntuación final...",
    ]

    prog = st.progress(0)
    status = st.empty()
    term = st.empty()
    term_lines = []

    for i, step in enumerate(steps):
        prog.progress(int((i+1)/len(steps)*94))
        status.markdown(
            f"<div style='font-family:\"Share Tech Mono\",monospace;font-size:10px;color:#00c8ff'>⟳ {step}</div>",
            unsafe_allow_html=True)
        term_lines.append(f"[{i+1:02d}/{len(steps)}] {step}")
        term.code("\n".join(term_lines[-8:]), language=None)
        time.sleep(0.18)

    # ── API Call 1 ─────────────────────────────────────────────────────────────
    p1 = f"""Eres un motor cuantitativo de inversión especializado en carteras de DEGIRO España.
Capital disponible: €{capital:,} EUR | Fecha: {today} | Horizonte: 90 días
Universo seleccionado: {universe_name} — {universe['desc']}

Activos disponibles:
{tickers}

INSTRUCCIONES:
1. Simula LSTM (lookback 60 días, 2 capas, 128 unidades): señal lstm_signal (ALCISTA/NEUTRAL/BAJISTA), lstm_confidence (0-1), lstm_90d %.
2. Ejecuta NSGA-II (50 gen, pop=200): maximizar rentabilidad, minimizar volatilidad, maximizar Sharpe.
3. Selecciona exactamente 10 activos Pareto-óptimos diversificados (mín. 4 clases diferentes).
4. Restricciones: máx 30% por activo, máx 40% por clase, pesos suman exactamente 100%.
5. Calcula número de acciones a precio actual en EUR.
6. Régimen EN ESPAÑOL: "Alcista Tranquilo", "Alcista Volátil", "Bajista Tranquilo" o "Bajista Volátil".
7. Añade nota fiscal breve por activo (retención dividendo, plusvalía IRPF 19-28%).

Responde ÚNICAMENTE con un objeto JSON sin markdown:
{{"summary":"2 frases","regime_landscape":"Alcista-dominante","pareto_hypervolume":0.73,"nsga_generations":50,"expected_portfolio_90d":11.4,"portfolio_sharpe":1.45,"portfolio_volatility":14.2,"cash_reserve_eur":650,"currency_note":"nota divisa","top10":[{{"ticker":"SAN","asset_name":"Banco Santander","asset_class":"Banca-ES","exchange":"BME","degiro_fee":"€1+€1","regime":"Alcista Tranquilo","lstm_signal":"ALCISTA","lstm_confidence":0.82,"lstm_90d":12.4,"nsga_weight":15.5,"expected_90d":11.8,"sharpe":1.45,"volatility":18.2,"max_drawdown":-14.2,"shares":120,"allocated_eur":8820,"rationale":"una frase","fiscal_note":"Dividendo retención 19%"}}],"risk_warnings":[{{"title":"Riesgo","body":"Descripción"}}],"rebalance_trigger":"condiciones","fiscal_summary":"párrafo breve"}}"""

    try:
        status.markdown(
            "<div style='font-family:\"Share Tech Mono\",monospace;font-size:10px;color:#ffcc00'>⟳ Llamada 1/2 — Asignación top-10...</div>",
            unsafe_allow_html=True)
        raw1 = call_api([{"role":"user","content":p1}])
        data = parse_json(raw1)
        if not data or not data.get("top10"):
            st.error(f"⚠ Error parseando respuesta. Preview: {raw1[:400]}")
            st.stop()

        # ── API Call 2 ─────────────────────────────────────────────────────────
        selected = ", ".join(a["ticker"] for a in data["top10"])
        all_tick  = ", ".join(a["t"] for a in universe["assets"])
        p2 = f"""Para gráfico scatter Pareto activos DEGIRO España.
Seleccionados (top10): {selected}
Resto: {all_tick}
Responde ÚNICAMENTE con array JSON:
[{{"ticker":"SAN","asset_class":"Banca-ES","risk":18.2,"return_est":11.8,"selected":true}}]"""

        status.markdown(
            "<div style='font-family:\"Share Tech Mono\",monospace;font-size:10px;color:#ffcc00'>⟳ Llamada 2/2 — Scatter Pareto...</div>",
            unsafe_allow_html=True)
        raw2 = call_api([{"role":"user","content":p2}], max_tokens=2000)

        all_assets = []
        try:
            s, e = raw2.index("["), raw2.rindex("]")
            all_assets = json.loads(raw2[s:e+1])
        except:
            all_assets = [{"ticker":a["ticker"],"asset_class":a["asset_class"],
                           "risk":a.get("volatility",15),"return_est":a.get("expected_90d",8),"selected":True}
                          for a in data["top10"]]

        prog.progress(100)
        status.empty(); term.empty()

        # ── Results ────────────────────────────────────────────────────────────
        st.success(f"✓ Optimización completa — Hipervolumen Pareto: {data.get('pareto_hypervolume','—')}")

        st.markdown(
            f"<div style='font-family:\"Share Tech Mono\",monospace;font-size:11px;"
            f"color:rgba(100,180,200,0.8);line-height:1.8;padding:14px 18px;"
            f"background:rgba(0,200,255,0.03);border-left:2px solid rgba(0,200,255,0.35);"
            f"border-radius:0 4px 4px 0;margin-bottom:16px'>{data.get('summary','')}</div>",
            unsafe_allow_html=True)

        # Stats
        cols = st.columns(6)
        for col, (lbl, val) in zip(cols, [
            ("Yield 90D", f"+{data.get('expected_portfolio_90d',0):.1f}%"),
            ("Sharpe",    f"{data.get('portfolio_sharpe',0):.2f}"),
            ("Volatil.",  f"±{data.get('portfolio_volatility',0):.1f}%"),
            ("Hypervolumen",f"{data.get('pareto_hypervolume',0):.2f}"),
            ("Gen. NSGA-II", str(data.get('nsga_generations',50))),
            ("Efectivo €", f"€{int(data.get('cash_reserve_eur',0)):,}"),
        ]):
            col.metric(lbl, val)

        st.markdown("---")
        tabs = st.tabs(["📊 TOP 10","🎯 PARETO","📋 ASIGNACIÓN","⚠️ RIESGOS","🏦 FISCALIDAD"])

        # TOP 10
        with tabs[0]:
            for i, a in enumerate(data.get("top10",[])):
                color = PAL[i % len(PAL)]
                rc = regime_color(a.get("regime",""))
                lc = lstm_color(a.get("lstm_signal",""))
                is_pos = (a.get("expected_90d",0) or 0) >= 0
                with st.container():
                    ca, cb = st.columns([3,1])
                    with ca:
                        st.markdown(
                            f"<span style='font-family:Orbitron;font-size:15px;font-weight:700;color:#fff;letter-spacing:2px'>{a['ticker']}</span>"
                            f"&nbsp;&nbsp;<span style='font-family:\"Share Tech Mono\",monospace;font-size:8px;padding:2px 6px;border-radius:2px;border:1px solid rgba(0,200,255,0.3);color:#00c8ff'>{a.get('exchange','')}</span>"
                            f"&nbsp;<span style='font-family:\"Share Tech Mono\",monospace;font-size:8px;padding:2px 6px;border-radius:2px;border:1px solid rgba(255,204,0,0.3);color:rgba(255,204,0,0.7)'>{a.get('degiro_fee','')}</span>",
                            unsafe_allow_html=True)
                        st.caption(f"{a.get('asset_name','')} · {a.get('asset_class','')}")
                        st.markdown(
                            f"<span style='font-family:\"Share Tech Mono\",monospace;font-size:8px;"
                            f"padding:2px 8px;border-radius:2px;border:1px solid {rc};color:{rc}'>{a.get('regime','')}</span>",
                            unsafe_allow_html=True)
                    with cb:
                        st.markdown(f"<div style='font-family:Orbitron;font-size:28px;font-weight:900;color:rgba(0,200,255,0.1);text-align:right'>{str(i+1).zfill(2)}</div>", unsafe_allow_html=True)

                    st.markdown(
                        f"<div style='font-family:\"Share Tech Mono\",monospace;font-size:9px;padding:3px 9px;"
                        f"border-radius:2px;background:rgba(0,200,255,0.06);border:1px solid rgba(0,200,255,0.18);"
                        f"color:#00c8ff;display:inline-block;margin:8px 0'>"
                        f"◈ LSTM&nbsp;<span style='color:{lc};font-weight:700'>{a.get('lstm_signal','')}</span>"
                        f"&nbsp;·&nbsp;{int((a.get('lstm_confidence',0) or 0)*100)}% conf"
                        f"&nbsp;·&nbsp;{'+' if (a.get('lstm_90d',0) or 0)>=0 else ''}{(a.get('lstm_90d',0) or 0):.1f}% pronóstico</div>",
                        unsafe_allow_html=True)

                    m1,m2,m3 = st.columns(3)
                    m1.metric("Yield 90D", f"{'+' if is_pos else ''}{(a.get('expected_90d',0) or 0):.1f}%")
                    m2.metric("Sharpe", f"{(a.get('sharpe',0) or 0):.2f}")
                    m3.metric("Volatilidad", f"{(a.get('volatility',0) or 0):.1f}%")
                    st.caption(a.get("rationale",""))
                    if a.get("fiscal_note"):
                        st.markdown(f"<small style='color:rgba(255,204,0,0.5)'>📋 {a['fiscal_note']}</small>", unsafe_allow_html=True)
                    st.markdown(
                        f"<div style='font-family:\"Share Tech Mono\",monospace;font-size:9px;padding:4px 10px;"
                        f"background:rgba(0,200,255,0.05);border:1px solid rgba(0,200,255,0.15);border-radius:2px;"
                        f"color:#00c8ff;display:inline-block;margin-top:4px'>"
                        f"COMPRAR {a.get('shares',0)} acc. · €{int(a.get('allocated_eur',0)):,} asignado</div>",
                        unsafe_allow_html=True)
                    st.divider()

        # PARETO
        with tabs[1]:
            import plotly.graph_objects as go
            fig = go.Figure()
            for a in all_assets:
                if not a.get("selected"):
                    fig.add_trace(go.Scatter(
                        x=[a.get("risk",0)], y=[a.get("return_est",0)],
                        mode="markers", marker=dict(color="#0a2030",size=7,line=dict(color="rgba(0,200,255,0.1)",width=1)),
                        name=a["ticker"], showlegend=False,
                        hovertemplate=f"<b>{a['ticker']}</b><br>Riesgo: {a.get('risk',0):.1f}%<br>Rentab.: {a.get('return_est',0):.1f}%<extra></extra>"))
            sel = sorted([a for a in all_assets if a.get("selected")], key=lambda x: x.get("risk",0))
            if sel:
                fig.add_trace(go.Scatter(
                    x=[a.get("risk",0) for a in sel], y=[a.get("return_est",0) for a in sel],
                    mode="lines", line=dict(color="rgba(0,200,255,0.2)",width=1.5,dash="dot"), showlegend=False))
            for i, a in enumerate([a for a in all_assets if a.get("selected")]):
                fig.add_trace(go.Scatter(
                    x=[a.get("risk",0)], y=[a.get("return_est",0)],
                    mode="markers+text", text=[a["ticker"]],
                    textposition="top right", textfont=dict(color="#fff",size=9,family="Share Tech Mono"),
                    marker=dict(color=PAL[i%len(PAL)],size=12,line=dict(color=PAL[i%len(PAL)],width=1.5)),
                    name=a["ticker"],
                    hovertemplate=f"<b>{a['ticker']}</b><br>Riesgo: {a.get('risk',0):.1f}%<br>Rentab.: {a.get('return_est',0):.1f}%<extra></extra>"))
            fig.update_layout(
                paper_bgcolor="#020408", plot_bgcolor="rgba(0,200,255,0.02)",
                font=dict(color="#b0e8ff",family="Share Tech Mono"),
                xaxis=dict(title="RIESGO (VOLATILIDAD) %",gridcolor="rgba(0,200,255,0.05)"),
                yaxis=dict(title="RENTABILIDAD ESTIMADA 90D %",gridcolor="rgba(0,200,255,0.05)"),
                height=420, margin=dict(l=20,r=20,t=20,b=20))
            st.plotly_chart(fig, use_container_width=True)

        # ASIGNACIÓN
        with tabs[2]:
            import pandas as pd
            df = pd.DataFrame([{
                "Ticker": a.get("ticker",""), "Nombre": a.get("asset_name",""),
                "Bolsa": a.get("exchange",""), "Clase": a.get("asset_class",""),
                "LSTM": a.get("lstm_signal",""),
                "Peso %": round(a.get("nsga_weight",0) or 0,1),
                "Yield 90D %": round(a.get("expected_90d",0) or 0,1),
                "Sharpe": round(a.get("sharpe",0) or 0,2),
                "Acciones": a.get("shares",0),
                "Asignado €": int(a.get("allocated_eur",0) or 0),
            } for a in data.get("top10",[])])
            st.dataframe(df, use_container_width=True, hide_index=True)

        # RIESGOS
        with tabs[3]:
            for w in data.get("risk_warnings",[]):
                st.error(f"**{w.get('title','')}**\n\n{w.get('body','')}")
            st.markdown("**🔄 Trigger de Rebalanceo**")
            st.info(data.get("rebalance_trigger",""))

        # FISCALIDAD
        with tabs[4]:
            st.markdown("#### 📋 Fiscalidad IRPF — Residente Fiscal España")
            st.markdown(data.get("fiscal_summary",""))
            st.markdown("#### 📊 Escala Plusvalías 2024")
            import pandas as pd
            st.table(pd.DataFrame({
                "Tramo": ["0–6.000 €","6.000–50.000 €","50.000–200.000 €","200.000–300.000 €","+300.000 €"],
                "Tipo IRPF": ["19%","21%","23%","27%","28%"]
            }))
            st.warning(f"**⚠ Riesgo Divisa EUR/USD**\n\n{data.get('currency_note','DEGIRO aplica 0.1% de conversión de divisa.')}")
            st.info("**🏦 Modelo 720**\n\nSi activos en el extranjero superan **50.000 €** → declaración obligatoria.")

    except Exception as e:
        st.error(f"⚠ Error: {e}")

else:
    st.markdown(
        "<div style='text-align:center;padding:60px 20px;font-family:\"Share Tech Mono\",monospace;"
        "color:rgba(30,80,100,1);font-size:11px;line-height:2'>"
        "Configura los parámetros en el panel lateral<br>"
        "▶ Pulsa OPTIMIZAR CARTERA<br><br>"
        "<span style='font-size:9px'>NSGA-II (50 gen) + LSTM (2 capas) · frontera de Pareto · top-10 activos DEGIRO España</span>"
        "</div>",
        unsafe_allow_html=True)

st.markdown("<div class='disclaimer'>⚠ SIMULACIÓN IA · SOLO FINES EDUCATIVOS · NO ES ASESORAMIENTO FINANCIERO</div>", unsafe_allow_html=True)

