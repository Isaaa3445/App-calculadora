import numpy as np
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# ── Configuración de página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Calculadora Acústica",
    page_icon="🔊",
    layout="wide",
)

st.title("🔊 Calculadora Acústica de Recintos")
st.caption("Tiempos de reverberación · Campo sonoro · Distancia crítica · Inteligibilidad de la palabra (%ALcons)")

# ── Constantes ───────────────────────────────────────────────────────────────
c      = 343.0
I0     = 1e-12
FREQS  = np.array([125, 250, 500, 1000, 2000, 4000])
FREQ_LABELS = [f"{f} Hz" for f in FREQS]

MATERIALES = {
    "concreto":  [0.01, 0.01, 0.02, 0.02, 0.03, 0.04],
    "drywall":   [0.05, 0.05, 0.05, 0.04, 0.07, 0.09],
    "ladrillo":  [0.01, 0.01, 0.02, 0.02, 0.03, 0.04],
    "vidrio":    [0.28, 0.22, 0.15, 0.12, 0.08, 0.06],
    "madera":    [0.15, 0.11, 0.10, 0.07, 0.06, 0.07],
    "aluminio":  [0.01, 0.01, 0.02, 0.02, 0.02, 0.02],
    "baldosa":   [0.01, 0.01, 0.02, 0.02, 0.03, 0.04],
}

def alcons_categoria(alcons):
    if alcons < 7:
        return "Excelente", "🟢"
    elif alcons < 11:
        return "Buena", "🟡"
    elif alcons < 15:
        return "Aceptable", "🟠"
    elif alcons < 20:
        return "Pobre", "🔴"
    else:
        return "Inaceptable", "⛔"

# ── Sidebar: parámetros de entrada ──────────────────────────────────────────
with st.sidebar:
    st.header("Dimensiones del recinto")
    largo = st.number_input("Largo (m)", min_value=1.0, value=10.0, step=0.5)
    ancho = st.number_input("Ancho (m)", min_value=1.0, value=8.0,  step=0.5)
    alto  = st.number_input("Altura (m)", min_value=1.0, value=3.0, step=0.1)

    st.divider()
    st.header("Materiales")
    piso  = st.selectbox("Piso",  list(MATERIALES.keys()), index=4)
    techo = st.selectbox("Techo", list(MATERIALES.keys()), index=0)

    st.divider()
    st.header("Paredes")
    n_paredes = st.number_input("Número de materiales en paredes", min_value=1, max_value=6, value=2, step=1)

    paredes = []
    for i in range(int(n_paredes)):
        with st.expander(f"Material de pared {i+1}", expanded=True):
            mat  = st.selectbox("Material", list(MATERIALES.keys()), key=f"mat_{i}")
            area = st.number_input("Área (m²)", min_value=0.1, value=30.0, step=1.0, key=f"area_{i}")
            paredes.append((mat, area))

    st.divider()
    st.header("Fuente sonora")
    Lw = st.slider("Nivel de potencia sonora Lw (dB)", 50, 150, 90)
    r  = st.slider("Distancia fuente–receptor r (m)", 0.5, 20.0, 2.0, step=0.5)
    Q  = 2  # semiesfera (fuente sobre superficie)

# ── Cálculos principales ─────────────────────────────────────────────────────
V        = largo * ancho * alto
S_piso   = largo * ancho
S_techo  = S_piso
S_pared  = 2*(largo*alto) + 2*(ancho*alto)
S_total  = 2*S_piso + S_pared
l        = 4*V / S_total
tau      = l / c
W        = 10**((Lw - 120) / 10)
If_      = W / (4 * np.pi * r**2)
LI       = 10 * np.log10(If_ / I0)

alpha_piso  = np.array(MATERIALES[piso])
alpha_techo = np.array(MATERIALES[techo])

RT_sabine    = np.zeros(6)
RT_eyring    = np.zeros(6)
RT_millington= np.zeros(6)
n_reflex     = np.zeros(6)
Lp_arr       = np.zeros(6)
Dc_arr       = np.zeros(6)
R_arr        = np.zeros(6)
A_arr        = np.zeros(6)

for i in range(6):
    A_pared = sum(area * MATERIALES[mat][i] for mat, area in paredes)
    A       = S_piso*alpha_piso[i] + S_techo*alpha_techo[i] + A_pared
    ap      = min(A / S_total, 0.9999)
    A_arr[i] = A

    RT_sabine[i]     = 0.161 * V / A
    RT_eyring[i]     = 0.161 * V / (-S_total * np.log(1 - ap))
    lp_sum = (S_piso  * np.log(1 - min(alpha_piso[i],  0.9999)) +
              S_techo * np.log(1 - min(alpha_techo[i], 0.9999)) +
              (A_pared * np.log(1 - ap) / ap if ap > 0 else 0))
    RT_millington[i] = 0.161 * V / (-lp_sum)

    R         = A / (1 - ap)
    R_arr[i]  = R
    Lp_arr[i] = Lw + 10*np.log10(Q/(4*np.pi*r**2) + 4/R)
    Dc_arr[i] = 0.057 * np.sqrt(Q * R)
    n_reflex[i] = c * RT_sabine[i] / l

# RT promedio en banda de 1000 Hz (índice 3) — referencia para %ALcons
RT_ref = RT_sabine[3]
R_ref  = R_arr[3]
Dc_ref = Dc_arr[3]

# ── Métricas generales ───────────────────────────────────────────────────────
st.subheader("Datos generales del recinto")
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Volumen",          f"{V:.1f} m³")
c2.metric("Superficie total", f"{S_total:.1f} m²")
c3.metric("Rec. libre medio", f"{l:.2f} m")
c4.metric("RT Sabine prom.",  f"{RT_sabine.mean():.2f} s")
c5.metric("Lp campo total",   f"{Lp_arr.mean():.1f} dB")
c6.metric("Distancia crítica",f"{Dc_ref:.2f} m")

st.divider()

# ── Gráfica RT ───────────────────────────────────────────────────────────────
st.subheader("Tiempo de reverberación vs frecuencia")
fig = go.Figure()
fig.add_trace(go.Scatter(x=FREQ_LABELS, y=RT_sabine,    mode="lines+markers", name="Sabine",
                         line=dict(color="#378ADD", width=2), marker=dict(size=7)))
fig.add_trace(go.Scatter(x=FREQ_LABELS, y=RT_eyring,    mode="lines+markers", name="Eyring",
                         line=dict(color="#1D9E75", width=2), marker=dict(size=7)))
fig.add_trace(go.Scatter(x=FREQ_LABELS, y=RT_millington,mode="lines+markers", name="Millington",
                         line=dict(color="#D85A30", width=2), marker=dict(size=7)))
fig.update_layout(
    xaxis_title="Frecuencia (Hz)",
    yaxis_title="RT (s)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    height=380,
    margin=dict(l=0, r=0, t=10, b=0),
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Tabla RT ─────────────────────────────────────────────────────────────────
st.subheader("Resultados por banda de frecuencia")
df = pd.DataFrame({
    "Frecuencia":            FREQ_LABELS,
    "RT Sabine (s)":         np.round(RT_sabine,    3),
    "RT Eyring (s)":         np.round(RT_eyring,    3),
    "RT Millington (s)":     np.round(RT_millington,3),
    "Reflexiones":           np.round(n_reflex,     1),
    "Lp (dB)":               np.round(Lp_arr,       1),
    "Distancia crítica (m)": np.round(Dc_arr,        2),
})
st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()

# ════════════════════════════════════════════════════════════════════════════
# SECCIÓN: INTELIGIBILIDAD DE LA PALABRA — %ALcons
# ════════════════════════════════════════════════════════════════════════════
st.subheader("🗣️ Inteligibilidad de la palabra — %ALcons")

st.markdown("""
El **%ALcons** (Percentage Articulation Loss of Consonants) indica qué porcentaje de consonantes 
se pierden en la comunicación verbal. Se calcula con la fórmula de Peutz:

$$\\%ALcons = \\frac{200 \\cdot r^2 \\cdot RT_{60}^2}{V \\cdot Q}$$

Para distancias mayores a la distancia crítica se usa una versión corregida.
""")

# Escala de referencia
col_esc1, col_esc2 = st.columns([1, 2])
with col_esc1:
    st.markdown("""
| %ALcons | Calidad |
|---------|---------|
| < 7% | 🟢 Excelente |
| 7 – 11% | 🟡 Buena |
| 11 – 15% | 🟠 Aceptable |
| 15 – 20% | 🔴 Pobre |
| > 20% | ⛔ Inaceptable |
""")

st.markdown("#### Ingresar distancias a evaluar")
st.caption("Escribe las distancias separadas por comas (ej: 1, 2, 5, 10, 15)")

# Distancias por defecto: distribuidas a lo largo de la sala
d_default = ", ".join([str(round(x, 1)) for x in np.linspace(0.5, max(largo, ancho)*0.9, 8)])
distancias_input = st.text_input("Distancias (m)", value=d_default)

# Opción de agregar distancia crítica automáticamente
incluir_dc = st.checkbox("Incluir distancia crítica automáticamente", value=True)

try:
    distancias = [float(d.strip()) for d in distancias_input.split(",") if d.strip()]
    if incluir_dc and round(Dc_ref, 1) not in [round(d, 1) for d in distancias]:
        distancias.append(round(Dc_ref, 2))
        distancias = sorted(distancias)

    if len(distancias) == 0:
        st.warning("Ingresa al menos una distancia.")
    else:
        # ── Cálculo %ALcons por distancia ────────────────────────────────────
        resultados = []
        for d in distancias:
            # Fórmula de Peutz
            # Para d <= Dc: fórmula directa
            # Para d > Dc:  se satura, se usa d = Dc en el campo reverberante
            if d <= Dc_ref:
                alcons = (200 * d**2 * RT_ref**2) / (V * Q)
            else:
                # Campo reverberante domina: ALcons con corrección
                alcons = (200 * Dc_ref**2 * RT_ref**2) / (V * Q) * (d / Dc_ref)

            alcons = min(alcons, 100.0)
            cat, emoji = alcons_categoria(alcons)
            zona = "campo directo" if d <= Dc_ref else "campo reverberante"
            resultados.append({
                "Distancia (m)": d,
                "%ALcons": round(alcons, 2),
                "Calidad": f"{emoji} {cat}",
                "Zona": zona,
            })

        df_alcons = pd.DataFrame(resultados)

        # ── Métricas resumen ──────────────────────────────────────────────────
        mejor = df_alcons.loc[df_alcons["%ALcons"].idxmin()]
        peor  = df_alcons.loc[df_alcons["%ALcons"].idxmax()]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("RT₆₀ @ 1kHz (referencia)", f"{RT_ref:.2f} s")
        m2.metric("Distancia crítica Dc",       f"{Dc_ref:.2f} m")
        m3.metric("Mejor %ALcons",  f"{mejor['%ALcons']}%", f"a {mejor['Distancia (m)']} m")
        m4.metric("Peor %ALcons",   f"{peor['%ALcons']}%",  f"a {peor['Distancia (m)']} m")

        # ── Tabla resultados ──────────────────────────────────────────────────
        st.dataframe(df_alcons, use_container_width=True, hide_index=True)

        # ── Gráfica %ALcons vs distancia ──────────────────────────────────────
        fig2 = go.Figure()

        # Zonas de color de fondo
        x_range = [0, max(distancias) * 1.1]
        for ymin, ymax, color, label in [
            (0,  7,  "rgba(29,158,117,0.10)",  "Excelente"),
            (7,  11, "rgba(250,199,117,0.15)",  "Buena"),
            (11, 15, "rgba(216,90,48,0.10)",    "Aceptable"),
            (15, 20, "rgba(226,75,74,0.10)",    "Pobre"),
            (20, max(max([r["%ALcons"] for r in resultados])*1.2, 25),
                     "rgba(160,50,50,0.08)",    "Inaceptable"),
        ]:
            fig2.add_hrect(y0=ymin, y1=ymax, fillcolor=color, line_width=0,
                           annotation_text=label, annotation_position="right",
                           annotation_font_size=11)

        # Línea vertical en Dc
        fig2.add_vline(x=Dc_ref, line_dash="dash", line_color="#888",
                       annotation_text=f"Dc = {Dc_ref:.1f} m",
                       annotation_position="top right",
                       annotation_font_size=11)

        # Curva %ALcons
        fig2.add_trace(go.Scatter(
            x=[r["Distancia (m)"] for r in resultados],
            y=[r["%ALcons"] for r in resultados],
            mode="lines+markers+text",
            text=[f"{r['%ALcons']}%" for r in resultados],
            textposition="top center",
            textfont=dict(size=10),
            line=dict(color="#378ADD", width=2.5),
            marker=dict(size=8),
            name="%ALcons"
        ))

        fig2.update_layout(
            xaxis_title="Distancia (m)",
            yaxis_title="%ALcons",
            yaxis=dict(range=[0, max(max([r["%ALcons"] for r in resultados])*1.2, 25)]),
            height=420,
            margin=dict(l=0, r=80, t=20, b=0),
            showlegend=False,
        )
        st.plotly_chart(fig2, use_container_width=True)

        # ── Interpretación automática ─────────────────────────────────────────
        st.markdown("#### Interpretación")
        pct_aceptable = sum(1 for r in resultados if r["%ALcons"] < 15) / len(resultados) * 100
        dist_limite = next((r["Distancia (m)"] for r in resultados if r["%ALcons"] >= 15), None)

        if dist_limite:
            st.warning(f"La inteligibilidad es aceptable hasta aproximadamente **{dist_limite} m**. "
                       f"Más allá de esa distancia la sala presenta pérdida de consonantes significativa.")
        else:
            st.success(f"La inteligibilidad es **aceptable o mejor** en todas las distancias evaluadas ({pct_aceptable:.0f}%).")

        if RT_ref > 1.5:
            st.info(f"El RT₆₀ de {RT_ref:.2f} s en 1 kHz es elevado. Reducirlo con materiales absorbentes mejoraría significativamente el %ALcons.")

except ValueError:
    st.error("Formato inválido. Usa números separados por comas, ej: 1, 2, 5, 10")

st.divider()

# ── Detalles físicos ──────────────────────────────────────────────────────────
with st.expander("Ver detalles físicos adicionales"):
    d1, d2, d3 = st.columns(3)
    d1.metric("Tiempo entre reflexiones τ", f"{tau*1000:.2f} ms")
    d2.metric("Intensidad directa If",       f"{If_:.2e} W/m²")
    d3.metric("Nivel de intensidad LI",      f"{LI:.1f} dB")
