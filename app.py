import streamlit as st
import anthropic
import json
import re
from datetime import date

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NSGA-II + LSTM Portfolio Engine · DEGIRO España",
    page_icon="📈",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@700;900&display=swap');
body, .stApp { background: #020408 !important; color: #b0e8ff; }
h1,h2,h3 { font-family: 'Orbitron', sans-serif !important; color: #00c8ff !important; }
.metric-label { color: rgba(30,80,100,1) !important; font-size: 11px !important; }
.stTabs [data-baseweb="tab-list"] { background: transparent; border-bottom: 1px solid rgba(0,200,255,0.1); }
.stTabs [data-baseweb="tab"] { color: rgba(30,80,100,1); font-family: 'Share Tech Mono', monospace; font-size: 11px; letter-spacing: 2px; }
.stTabs [aria-selected="true"] { color: #00c8ff !important; border-bottom: 2px solid #00c8ff !important; }
.stButton>button { background: transparent; border: 1px solid #00c8ff; color: #00c8ff; font-family: 'Orbitron', sans-serif; letter-spacing: 3px; font-weight: 700; width: 100%; padding: 14px; }
.stButton>button:hover { background: rgba(0,200,255,0.05); box-shadow: 0 0 20px rgba(0,200,255,0.1); }
.stTextInput>div>div>input { background: rgba(0,0,0,0.5) !important; border: 1px solid rgba(0,200,255,0.2) !important; color: #00c8ff !important; font-family: 'Share Tech Mono', monospace !important; }
.stNumberInput>div>div>input { background: rgba(0,0,0,0.5) !important; border: 1px solid rgba(0,200,255,0.2) !important; color: #00c8ff !important; font-family: 'Orbitron', sans-serif !important; font-weight: 700; }
.stSelectbox>div { background: rgba(0,0,0,0.5) !important; border: 1px solid rgba(0,200,255,0.2) !important; color: #00c8ff !important; }
.stRadio label { color: #b0e8ff; font-size: 13px; }
div[data-testid="metric-container"] { background: rgba(0,0,0,0.3); border: 1px solid rgba(0,200,255,0.07); border-radius: 6px; padding: 10px; }
div[data-testid="metric-container"] label { color: rgba(30,80,100,1) !important; font-family: 'Share Tech Mono', monospace; font-size: 10px; letter-spacing: 2px; }
div[data-testid="metric-container"] div { color: #00c8ff !important; font-family: 'Orbitron', sans-serif !important; font-weight: 700; }
.stProgress > div > div { background: linear-gradient(90deg, #ff3c6e, #ffcc00, #00c8ff) !important; }
.asset-card { background: rgba(0,200,255,0.02); border: 1px solid rgba(0,200,255,0.12); border-radius: 6px; padding: 16px; margin-bottom: 10px; }
.disclaimer { text-align: center; font-family: 'Share Tech Mono', monospace; font-size: 9px; color: rgba(20,60,80,0.7); margin-top: 24px; letter-spacing: 1px; }
</style>
""", unsafe_allow_html=True)

# ── Asset Universes ───────────────────────────────────────────────────────────
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

def call_api(api_key, messages, max_tokens=8000):
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        messages=messages,
    )
    return "".join(b.text for b in response.content if hasattr(b, "text"))

# ── UI ────────────────────────────────────────────────────────────────────────
st.markdown("# NSGA‑II + LSTM **PORTFOLIO ENGINE** · 🇪🇸")
st.markdown(
    "<div style='font-family:\"Share Tech Mono\",monospace;font-size:10px;color:rgba(30,80,100,1);"
    "letter-spacing:1px;margin-bottom:20px'>"
    "universo DEGIRO España · IBEX35 · ETFs europeos Core · acciones globales · horizonte 90 días</div>",
    unsafe_allow_html=True
)

col_left, col_right = st.columns([1, 2])

with col_left:
    st.markdown("#### 🔑 API Key")
    api_key = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-api03-...",
                             help="Obtén tu key en console.anthropic.com. No se almacena.")

    st.markdown("#### 🌐 Universo")
    universe_name = st.radio("Selecciona universo", list(UNIVERSES.keys()), label_visibility="collapsed")
    universe = UNIVERSES[universe_name]
    st.caption(universe["desc"])

    st.markdown("#### 💶 Capital")
    capital = st.number_input("Capital disponible (€)", min_value=1000, max_value=10_000_000,
                               value=20000, step=1000, format="%d")

    run = st.button("▶  INICIAR OPTIMIZACIÓN")

with col_right:
    if run:
        if not api_key:
            st.error("⚠ Introduce tu API Key de Anthropic para continuar.")
            st.stop()

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
            "Generación 50/50 — frontera de Pareto estabilizada ✓",
            "Aplicando restricciones de diversificación (máx. 35% por clase)...",
            "Seleccionando top-10 por indicador de hipervolumen...",
            "Enviando al motor IA para puntuación final...",
        ]

        progress_bar = st.progress(0)
        status_text = st.empty()
        term = st.empty()
        term_lines = []

        for i, step in enumerate(steps):
            pct = int((i+1)/len(steps)*94)
            progress_bar.progress(pct)
            status_text.markdown(
                f"<div style='font-family:\"Share Tech Mono\",monospace;font-size:10px;color:#00c8ff'>"
                f"⟳ {step}</div>", unsafe_allow_html=True)
            term_lines.append(f"[{i+1:02d}/{len(steps)}] {step}")
            term.code("\n".join(term_lines[-8:]), language=None)
            import time; time.sleep(0.18)

        # Call 1
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
{{"summary":"2 frases","regime_landscape":"Alcista-dominante","pareto_hypervolume":0.73,"nsga_generations":50,"expected_portfolio_90d":11.4,"portfolio_sharpe":1.45,"portfolio_volatility":14.2,"cash_reserve_eur":650,"currency_note":"nota divisa","top10":[{{"ticker":"SAN","asset_name":"Banco Santander","asset_class":"Banca-ES","exchange":"BME","degiro_fee":"€1+€1","regime":"Alcista Tranquilo","lstm_signal":"ALCISTA","lstm_confidence":0.82,"lstm_90d":12.4,"nsga_weight":15.5,"expected_90d":11.8,"sharpe":1.45,"volatility":18.2,"max_drawdown":-14.2,"shares":120,"allocated_eur":8820,"rationale":"una frase","fiscal_note":"Dividendo retención 19%"}}],"risk_warnings":[{{"title":"Riesgo","body":"Descripción"}}],"rebalance_trigger":"condiciones","fiscal_summary":"párrafo breve fiscalidad"}}"""

        try:
            status_text.markdown(
                "<div style='font-family:\"Share Tech Mono\",monospace;font-size:10px;color:#ffcc00'>"
                "⟳ Llamada 1/2 — Asignación top-10...</div>", unsafe_allow_html=True)
            raw1 = call_api(api_key, [{"role":"user","content":p1}])
            data = parse_json(raw1)
            if not data or not data.get("top10"):
                st.error(f"⚠ Error parseando respuesta. Preview: {raw1[:400]}")
                st.stop()

            # Call 2
            selected = ", ".join(a["ticker"] for a in data["top10"])
            all_tick  = ", ".join(a["t"] for a in universe["assets"])
            p2 = f"""Para un gráfico scatter Pareto con activos DEGIRO España.
Activos SELECCIONADOS (top10): {selected}
Resto del universo: {all_tick}
Responde ÚNICAMENTE con un array JSON sin markdown:
[{{"ticker":"SAN","asset_class":"Banca-ES","risk":18.2,"return_est":11.8,"selected":true}}]"""

            status_text.markdown(
                "<div style='font-family:\"Share Tech Mono\",monospace;font-size:10px;color:#ffcc00'>"
                "⟳ Llamada 2/2 — Datos scatter Pareto...</div>", unsafe_allow_html=True)
            raw2 = call_api(api_key, [{"role":"user","content":p2}], max_tokens=2000)
            all_assets = []
            try:
                s, e = raw2.index("["), raw2.rindex("]")
                all_assets = json.loads(raw2[s:e+1])
            except:
                all_assets = [{"ticker":a["ticker"],"asset_class":a["asset_class"],
                               "risk":a.get("volatility",15),"return_est":a.get("expected_90d",8),"selected":True}
                              for a in data["top10"]]

            progress_bar.progress(100)
            status_text.empty(); term.empty()

            # ── Render results ─────────────────────────────────────────────
            st.success(f"✓ Optimización completa · Hipervolumen Pareto: {data.get('pareto_hypervolume','—')}")

            # Summary
            st.markdown(
                f"<div style='font-family:\"Share Tech Mono\",monospace;font-size:11px;"
                f"color:rgba(100,180,200,0.8);line-height:1.8;padding:14px 18px;"
                f"background:rgba(0,200,255,0.03);border-left:2px solid rgba(0,200,255,0.35);"
                f"border-radius:0 4px 4px 0;margin-bottom:16px'>{data.get('summary','')}</div>",
                unsafe_allow_html=True)

            # Stats
            c1,c2,c3,c4,c5,c6 = st.columns(6)
            cols = [c1,c2,c3,c4,c5,c6]
            stats = [
                ("Yield 90D", f"+{data.get('expected_portfolio_90d',0):.1f}%"),
                ("Sharpe",    f"{data.get('portfolio_sharpe',0):.2f}"),
                ("Volatil.",  f"±{data.get('portfolio_volatility',0):.1f}%"),
                ("Hypervolumen", f"{data.get('pareto_hypervolume',0):.2f}"),
                ("Gen. NSGA-II", str(data.get('nsga_generations',50))),
                ("Efectivo €", f"€{int(data.get('cash_reserve_eur',0)):,}"),
            ]
            for col, (lbl, val) in zip(cols, stats):
                col.metric(lbl, val)

            st.markdown("---")
            tabs = st.tabs(["📊 TOP 10", "🎯 PARETO", "📋 ASIGNACIÓN", "⚠️ RIESGOS", "🏦 FISCALIDAD"])

            # ── Tab TOP 10 ─────────────────────────────────────────────────
            with tabs[0]:
                for i, a in enumerate(data.get("top10",[])):
                    color = PAL[i % len(PAL)]
                    rc = regime_color(a.get("regime",""))
                    lc = lstm_color(a.get("lstm_signal",""))
                    is_pos = (a.get("expected_90d",0) or 0) >= 0
                    with st.container():
                        st.markdown(
                            f"<div style='border:1px solid {color}30;border-radius:6px;padding:14px;margin-bottom:10px'>",
                            unsafe_allow_html=True)
                        ca, cb = st.columns([3,1])
                        with ca:
                            st.markdown(
                                f"<span style='font-family:Orbitron;font-size:15px;font-weight:700;color:#fff;letter-spacing:2px'>{a['ticker']}</span>"
                                f"&nbsp;&nbsp;<span style='font-family:\"Share Tech Mono\",monospace;font-size:8px;padding:2px 6px;border-radius:2px;border:1px solid rgba(0,200,255,0.3);color:#00c8ff'>{a.get('exchange','')}</span>"
                                f"&nbsp;<span style='font-family:\"Share Tech Mono\",monospace;font-size:8px;padding:2px 6px;border-radius:2px;border:1px solid rgba(255,204,0,0.3);color:rgba(255,204,0,0.7)'>{a.get('degiro_fee','')}</span>",
                                unsafe_allow_html=True)
                            st.caption(f"{a.get('asset_name','')} · {a.get('asset_class','')}")
                            st.markdown(
                                f"<span style='font-family:\"Share Tech Mono\",monospace;font-size:8px;padding:2px 8px;border-radius:2px;border:1px solid {rc};color:{rc}'>{a.get('regime','')}</span>",
                                unsafe_allow_html=True)
                        with cb:
                            st.markdown(f"<div style='font-family:Orbitron;font-size:28px;font-weight:900;color:rgba(0,200,255,0.1);text-align:right'>{str(i+1).zfill(2)}</div>", unsafe_allow_html=True)

                        st.markdown(
                            f"<div style='font-family:\"Share Tech Mono\",monospace;font-size:9px;padding:3px 9px;border-radius:2px;"
                            f"background:rgba(0,200,255,0.06);border:1px solid rgba(0,200,255,0.18);color:#00c8ff;display:inline-block;margin:8px 0'>"
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
                            f"color:#00c8ff;display:inline-block;margin-top:6px'>"
                            f"COMPRAR {a.get('shares',0)} acc. · €{int(a.get('allocated_eur',0)):,} asignado</div>",
                            unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)

            # ── Tab PARETO ─────────────────────────────────────────────────
            with tabs[1]:
                import plotly.graph_objects as go
                fig = go.Figure()
                for a in all_assets:
                    if not a.get("selected"):
                        fig.add_trace(go.Scatter(
                            x=[a.get("risk",0)], y=[a.get("return_est",0)],
                            mode="markers", marker=dict(color="#0a2030", size=7, line=dict(color="rgba(0,200,255,0.1)",width=1)),
                            name=a["ticker"], showlegend=False,
                            hovertemplate=f"<b>{a['ticker']}</b><br>Riesgo: {a.get('risk',0):.1f}%<br>Rentabilidad: {a.get('return_est',0):.1f}%<extra></extra>"
                        ))
                sel_sorted = sorted([a for a in all_assets if a.get("selected")], key=lambda x: x.get("risk",0))
                if sel_sorted:
                    fig.add_trace(go.Scatter(
                        x=[a.get("risk",0) for a in sel_sorted],
                        y=[a.get("return_est",0) for a in sel_sorted],
                        mode="lines", line=dict(color="rgba(0,200,255,0.2)", width=1.5, dash="dot"),
                        showlegend=False
                    ))
                for i, a in enumerate([a for a in all_assets if a.get("selected")]):
                    fig.add_trace(go.Scatter(
                        x=[a.get("risk",0)], y=[a.get("return_est",0)],
                        mode="markers+text", text=[a["ticker"]],
                        textposition="top right", textfont=dict(color="#fff", size=9, family="Share Tech Mono"),
                        marker=dict(color=PAL[i%len(PAL)], size=12,
                                    line=dict(color=PAL[i%len(PAL)],width=1.5)),
                        name=a["ticker"],
                        hovertemplate=f"<b>{a['ticker']}</b><br>Riesgo: {a.get('risk',0):.1f}%<br>Rentabilidad: {a.get('return_est',0):.1f}%<extra></extra>"
                    ))
                fig.update_layout(
                    paper_bgcolor="#020408", plot_bgcolor="rgba(0,200,255,0.02)",
                    font=dict(color="#b0e8ff", family="Share Tech Mono"),
                    xaxis=dict(title="RIESGO (VOLATILIDAD) %", gridcolor="rgba(0,200,255,0.05)",
                               tickfont=dict(color="rgba(30,80,100,1)")),
                    yaxis=dict(title="RENTABILIDAD ESTIMADA 90D %", gridcolor="rgba(0,200,255,0.05)",
                               tickfont=dict(color="rgba(30,80,100,1)")),
                    showlegend=True, height=420, margin=dict(l=20,r=20,t=20,b=20),
                )
                st.plotly_chart(fig, use_container_width=True)

            # ── Tab ASIGNACIÓN ─────────────────────────────────────────────
            with tabs[2]:
                import pandas as pd
                rows = []
                for a in data.get("top10",[]):
                    rows.append({
                        "Ticker": a.get("ticker",""), "Nombre": a.get("asset_name",""),
                        "Bolsa": a.get("exchange",""), "Clase": a.get("asset_class",""),
                        "LSTM": a.get("lstm_signal",""), "Peso %": round(a.get("nsga_weight",0) or 0,1),
                        "Yield 90D %": round(a.get("expected_90d",0) or 0,1),
                        "Sharpe": round(a.get("sharpe",0) or 0,2),
                        "Acciones": a.get("shares",0),
                        "Asignado €": int(a.get("allocated_eur",0) or 0),
                    })
                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True, hide_index=True)

            # ── Tab RIESGOS ────────────────────────────────────────────────
            with tabs[3]:
                for w in data.get("risk_warnings",[]):
                    st.error(f"**{w.get('title','')}**\n\n{w.get('body','')}")
                st.markdown("**🔄 Trigger de Rebalanceo**")
                st.info(data.get("rebalance_trigger",""))

            # ── Tab FISCALIDAD ─────────────────────────────────────────────
            with tabs[4]:
                st.markdown("#### 📋 Fiscalidad IRPF — Residente Fiscal España")
                st.markdown(data.get("fiscal_summary","Consulta a un asesor fiscal."))

                st.markdown("#### 📊 Escala Plusvalías — Base del Ahorro 2024")
                irpf_data = {
                    "Tramo": ["0 – 6.000 €","6.000 – 50.000 €","50.000 – 200.000 €","200.000 – 300.000 €","+300.000 €"],
                    "Tipo": ["19%","21%","23%","27%","28%"]
                }
                import pandas as pd
                st.table(pd.DataFrame(irpf_data))

                st.warning(f"**⚠ Riesgo Divisa EUR/USD**\n\n{data.get('currency_note','Los activos en USD están sujetos al riesgo de tipo de cambio EUR/USD. DEGIRO aplica comisión de conversión del 0.1%.')}")
                st.info("**🏦 Modelo 720 / D6**\n\nSi el valor total de tus activos en el extranjero supera **50.000 €**, deberás presentar el Modelo 720. Consulta siempre con un asesor fiscal.")

        except Exception as e:
            st.error(f"⚠ Error: {e}")

    else:
        st.markdown(
            "<div style='text-align:center;padding:60px 20px;font-family:\"Share Tech Mono\",monospace;"
            "color:rgba(30,80,100,1);font-size:11px;line-height:2'>"
            "Introduce tu API key · Selecciona universo · Define capital<br>"
            "▶ Pulsa INICIAR OPTIMIZACIÓN<br><br>"
            "<span style='font-size:9px'>NSGA-II (50 gen) + LSTM (2 capas) · frontera de Pareto · top-10 activos DEGIRO España</span>"
            "</div>",
            unsafe_allow_html=True)

st.markdown(
    "<div class='disclaimer'>⚠ SIMULACIÓN GENERADA POR IA · SOLO FINES EDUCATIVOS · NO ES ASESORAMIENTO FINANCIERO · CONSULTA UN ASESOR ANTES DE INVERTIR</div>",
    unsafe_allow_html=True)

