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
st.caption("Reverberación · Parámetros de sala · Inteligibilidad de la palabra (%ALcons)")

# ── Constantes físicas ───────────────────────────────────────────────────────
c   = 343.0    # velocidad del sonido en aire (m/s)
I0  = 1e-12    # intensidad de referencia (W/m²)
Q   = 2        # factor de directividad fijo (semiesfera)
m   = 0.003    # coeficiente de absorción del aire (m⁻¹)

FREQS       = np.array([125, 250, 500, 1000, 2000, 4000])
FREQ_LABELS = [f"{f} Hz" for f in FREQS]

MATERIALES = {
    "concreto": [0.01, 0.01, 0.02, 0.02, 0.03, 0.04],
    "drywall":  [0.05, 0.05, 0.05, 0.04, 0.07, 0.09],
    "ladrillo": [0.01, 0.01, 0.02, 0.02, 0.03, 0.04],
    "vidrio":   [0.28, 0.22, 0.15, 0.12, 0.08, 0.06],
    "madera":   [0.15, 0.11, 0.10, 0.07, 0.06, 0.07],
    "aluminio": [0.01, 0.01, 0.02, 0.02, 0.02, 0.02],
    "baldosa":  [0.01, 0.01, 0.02, 0.02, 0.03, 0.04],
}

def alcons_categoria(v):
    if v < 7:    return "Excelente",    "🟢"
    elif v < 11: return "Buena",        "🟡"
    elif v < 15: return "Aceptable",    "🟠"
    elif v < 20: return "Pobre",        "🔴"
    else:        return "Inaceptable",  "⛔"

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Dimensiones del recinto")
    largo = st.number_input("Largo (m)",  min_value=1.0, value=10.0, step=0.5)
    ancho = st.number_input("Ancho (m)",  min_value=1.0, value=8.0,  step=0.5)
    alto  = st.number_input("Altura (m)", min_value=1.0, value=3.0,  step=0.1)

    st.divider()
    st.header("Materiales")
    piso  = st.selectbox("Piso",  list(MATERIALES.keys()), index=4)
    techo = st.selectbox("Techo", list(MATERIALES.keys()), index=0)

    st.divider()
    st.header("Paredes")
    n_paredes = st.number_input("Número de materiales", min_value=1, max_value=6, value=2, step=1)
    paredes = []
    for i in range(int(n_paredes)):
        with st.expander(f"Material de pared {i+1}", expanded=True):
            mat  = st.selectbox("Material", list(MATERIALES.keys()), key=f"mat_{i}")
            area = st.number_input("Área (m²)", min_value=0.1, value=30.0, step=1.0, key=f"area_{i}")
            paredes.append((mat, area))

    st.divider()
    st.header("Fuente sonora")
    Lw = st.slider("Nivel de potencia Lw (dB)", 50, 150, 90)
    r  = st.slider("Distancia fuente–receptor r (m)", 0.5, 20.0, 2.0, step=0.5)

# ════════════════════════════════════════════════════════════════════════════
# CÁLCULOS
# ════════════════════════════════════════════════════════════════════════════
V       = largo * ancho * alto
S_piso  = largo * ancho
S_techo = S_piso
S_pared = 2*(largo*alto) + 2*(ancho*alto)
S_total = 2*S_piso + S_pared
W       = 10**((Lw - 120) / 10)
If_     = W / (4 * np.pi * r**2)
LI      = 10 * np.log10(If_ / I0)

alpha_piso  = np.array(MATERIALES[piso])
alpha_techo = np.array(MATERIALES[techo])

RT_sabine     = np.zeros(6)
RT_eyring     = np.zeros(6)
RT_millington = np.zeros(6)
A_arr         = np.zeros(6)
R_arr         = np.zeros(6)
Dc_arr        = np.zeros(6)
Lp_arr        = np.zeros(6)
Lp_aire_arr   = np.zeros(6)
n_reflex_arr  = np.zeros(6)

for i in range(6):
    A_pared  = sum(area * MATERIALES[mat][i] for mat, area in paredes)
    A        = S_piso*alpha_piso[i] + S_techo*alpha_techo[i] + A_pared
    ap       = min(A / S_total, 0.9999)
    A_arr[i] = A

    RT_sabine[i]     = 0.161 * V / A
    RT_eyring[i]     = 0.161 * V / (-S_total * np.log(1 - ap))
    lp_sum = (S_piso  * np.log(1 - min(alpha_piso[i],  0.9999)) +
              S_techo * np.log(1 - min(alpha_techo[i], 0.9999)) +
              (A_pared * np.log(1 - ap) / ap if ap > 0 else 0))
    RT_millington[i] = 0.161 * V / (-lp_sum)

    R                = A / (1 - ap)
    R_arr[i]         = R
    Dc_arr[i]        = 0.057 * np.sqrt(Q * R)
    Lp_arr[i]        = Lw + 10*np.log10(Q/(4*np.pi*r**2) + 4/R)
    Lp_aire_arr[i]   = Lp_arr[i] - 20*np.log10(r) - m*r
    n_reflex_arr[i]  = c * RT_sabine[i] / (4*V/S_total)

# Parámetros globales
l_medio  = 4 * V / S_total
tau      = l_medio / c
RT_medio = RT_sabine.mean()
RT_1k    = RT_sabine[3]
R_1k     = R_arr[3]
Dc_1k    = Dc_arr[3]

# ════════════════════════════════════════════════════════════════════════════
# SECCIÓN 1 — DATOS GENERALES
# ════════════════════════════════════════════════════════════════════════════
st.subheader("📐 Datos generales del recinto")
g1, g2, g3, g4 = st.columns(4)
g1.metric("Volumen",          f"{V:.1f} m³")
g2.metric("Superficie total", f"{S_total:.1f} m²")
g3.metric("Potencia W",       f"{W:.2e} W")
g4.metric("Lw fuente",        f"{Lw} dB")

st.divider()

# ════════════════════════════════════════════════════════════════════════════
# SECCIÓN 2 — PARÁMETROS ACÚSTICOS DE SALA
# ════════════════════════════════════════════════════════════════════════════
st.subheader("📊 Parámetros acústicos de sala")

p1, p2, p3 = st.columns(3)
p1.metric("Recorrido libre medio",
          f"{l_medio:.3f} m",
          help="l = 4V / S  —  distancia promedio entre reflexiones")
p2.metric("Tiempo medio entre reflexiones",
          f"{tau*1000:.2f} ms",
          help="τ = l / c")
p3.metric("Nº reflexiones promedio (1 kHz)",
          f"{n_reflex_arr[3]:.1f}",
          help="n = c · RT / l")

p4, p5, p6 = st.columns(3)
p4.metric("Constante de sala R (1 kHz)",
          f"{R_1k:.2f} m²",
          help="R = A / (1 − ᾱ)")
p5.metric("Distancia crítica Dc (1 kHz)",
          f"{Dc_1k:.2f} m",
          help="Dc = 0.057·√(Q·R)")
p6.metric("Factor de directividad Q",
          "2",
          help="Q = 2 fijo: fuente sobre superficie plana (semiesfera)")

st.divider()

# ════════════════════════════════════════════════════════════════════════════
# SECCIÓN 3 — TIEMPOS DE REVERBERACIÓN
# ════════════════════════════════════════════════════════════════════════════
st.subheader("⏱️ Tiempos de reverberación")

rm1, rm2, rm3, rm4 = st.columns(4)
rm1.metric("RT medio Sabine",     f"{RT_sabine.mean():.2f} s")
rm2.metric("RT medio Eyring",     f"{RT_eyring.mean():.2f} s")
rm3.metric("RT medio Millington", f"{RT_millington.mean():.2f} s")
rm4.metric("RT @ 1 kHz (Sabine)", f"{RT_1k:.2f} s",
           help="Referencia para %ALcons")

fig = go.Figure()
fig.add_trace(go.Scatter(x=FREQ_LABELS, y=RT_sabine,     mode="lines+markers",
                         name="Sabine",     line=dict(color="#378ADD", width=2), marker=dict(size=7)))
fig.add_trace(go.Scatter(x=FREQ_LABELS, y=RT_eyring,     mode="lines+markers",
                         name="Eyring",     line=dict(color="#1D9E75", width=2), marker=dict(size=7)))
fig.add_trace(go.Scatter(x=FREQ_LABELS, y=RT_millington, mode="lines+markers",
                         name="Millington", line=dict(color="#D85A30", width=2), marker=dict(size=7)))
fig.update_layout(xaxis_title="Frecuencia (Hz)", yaxis_title="RT (s)",
                  legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                  height=360, margin=dict(l=0, r=0, t=10, b=0))
st.plotly_chart(fig, use_container_width=True)

df_rt = pd.DataFrame({
    "Frecuencia":            FREQ_LABELS,
    "Absorción A (m²Sab)":   np.round(A_arr,         2),
    "RT Sabine (s)":         np.round(RT_sabine,      3),
    "RT Eyring (s)":         np.round(RT_eyring,      3),
    "RT Millington (s)":     np.round(RT_millington,  3),
    "Constante R (m²)":      np.round(R_arr,          2),
    "Distancia crítica (m)": np.round(Dc_arr,          2),
    "Reflexiones":           np.round(n_reflex_arr,   1),
    "Lp total (dB)":         np.round(Lp_arr,         1),
    "Lp con aire (dB)":      np.round(Lp_aire_arr,    1),
})
st.dataframe(df_rt, use_container_width=True, hide_index=True)

st.divider()

# ════════════════════════════════════════════════════════════════════════════
# SECCIÓN 4 — ABSORCIÓN DEL AIRE
# ════════════════════════════════════════════════════════════════════════════
st.subheader("💨 Absorción del aire")
st.caption(f"Coeficiente m = {m} m⁻¹  ·  distancia r = {r} m")

at1, at2, at3 = st.columns(3)
at1.metric("Atenuación geométrica", f"{20*np.log10(r):.2f} dB",  help="20·log(r)")
at2.metric("Atenuación por aire",   f"{m*r:.4f} dB",             help="m · r")
at3.metric("Atenuación total",      f"{20*np.log10(r)+m*r:.2f} dB")

fig_aire = go.Figure()
fig_aire.add_trace(go.Bar(x=FREQ_LABELS, y=np.round(Lp_arr,      1),
                          name="Lp sin absorción de aire", marker_color="#378ADD"))
fig_aire.add_trace(go.Bar(x=FREQ_LABELS, y=np.round(Lp_aire_arr, 1),
                          name="Lp con absorción de aire", marker_color="#1D9E75"))
fig_aire.update_layout(barmode="group", xaxis_title="Frecuencia (Hz)",
                       yaxis_title="Nivel (dB)", height=300,
                       margin=dict(l=0, r=0, t=10, b=0),
                       legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
st.plotly_chart(fig_aire, use_container_width=True)

st.divider()

# ════════════════════════════════════════════════════════════════════════════
# SECCIÓN 5 — INTELIGIBILIDAD %ALcons
# ════════════════════════════════════════════════════════════════════════════
st.subheader("🗣️ Inteligibilidad de la palabra — %ALcons")

st.markdown(f"""
Fórmula de Peutz usando **RT medio @ 1 kHz = {RT_1k:.2f} s**:

$$\\%ALcons = \\frac{{200 \\cdot r^2 \\cdot RT_{{60}}^2}}{{V \\cdot Q}}$$

Para r > Dc ({Dc_1k:.2f} m) el campo reverberante domina y la degradación es mayor.
""")

col_esc, col_param = st.columns([1, 2])
with col_esc:
    st.markdown("""
| %ALcons | Calidad |
|---------|---------|
| < 7% | 🟢 Excelente |
| 7 – 11% | 🟡 Buena |
| 11 – 15% | 🟠 Aceptable |
| 15 – 20% | 🔴 Pobre |
| > 20% | ⛔ Inaceptable |
""")
with col_param:
    st.markdown("**Parámetros de entrada para %ALcons**")
    st.markdown(f"- RT₆₀ @ 1 kHz = **{RT_1k:.3f} s**")
    st.markdown(f"- RT medio (todas las bandas) = **{RT_medio:.3f} s**")
    st.markdown(f"- Volumen V = **{V:.1f} m³**")
    st.markdown(f"- Q = **{Q}** (fijo)")
    st.markdown(f"- Distancia crítica Dc = **{Dc_1k:.2f} m**")
    st.markdown(f"- Recorrido libre medio = **{l_medio:.3f} m**")
    st.markdown(f"- Tiempo entre reflexiones = **{tau*1000:.2f} ms**")

st.markdown("#### Distancias a evaluar")
st.caption("Escribe las distancias separadas por comas (ej: 1, 2, 5, 10, 15)")

d_default   = ", ".join([str(round(x, 1)) for x in np.linspace(0.5, max(largo, ancho)*0.9, 8)])
distancias_input = st.text_input("Distancias (m)", value=d_default)
incluir_dc  = st.checkbox("Incluir distancia crítica automáticamente", value=True)

try:
    distancias = [float(d.strip()) for d in distancias_input.split(",") if d.strip()]
    if incluir_dc and round(Dc_1k, 1) not in [round(d, 1) for d in distancias]:
        distancias.append(round(Dc_1k, 2))
        distancias = sorted(distancias)

    if len(distancias) == 0:
        st.warning("Ingresa al menos una distancia.")
    else:
        resultados = []
        for d in distancias:
            if d <= Dc_1k:
                alcons = (200 * d**2 * RT_1k**2) / (V * Q)
            else:
                alcons = (200 * Dc_1k**2 * RT_1k**2) / (V * Q) * (d / Dc_1k)
            alcons = min(alcons, 100.0)
            cat, emoji = alcons_categoria(alcons)
            resultados.append({
                "Distancia (m)": d,
                "%ALcons":       round(alcons, 2),
                "Calidad":       f"{emoji} {cat}",
                "Zona":          "campo directo" if d <= Dc_1k else "campo reverberante",
            })

        mejor = min(resultados, key=lambda x: x["%ALcons"])
        peor  = max(resultados, key=lambda x: x["%ALcons"])

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("RT₆₀ @ 1kHz",       f"{RT_1k:.2f} s")
        m2.metric("Distancia crítica",  f"{Dc_1k:.2f} m")
        m3.metric("Mejor %ALcons",      f"{mejor['%ALcons']}%", f"a {mejor['Distancia (m)']} m")
        m4.metric("Peor %ALcons",       f"{peor['%ALcons']}%",  f"a {peor['Distancia (m)']} m")

        st.dataframe(pd.DataFrame(resultados), use_container_width=True, hide_index=True)

        # Gráfica
        ymax_graf = max(max(r["%ALcons"] for r in resultados)*1.25, 25)
        fig2 = go.Figure()
        for ymin, ymax, color, label in [
            (0,  7,         "rgba(29,158,117,0.10)",  "Excelente"),
            (7,  11,        "rgba(250,199,117,0.15)", "Buena"),
            (11, 15,        "rgba(216,90,48,0.10)",   "Aceptable"),
            (15, 20,        "rgba(226,75,74,0.10)",   "Pobre"),
            (20, ymax_graf, "rgba(160,50,50,0.08)",   "Inaceptable"),
        ]:
            fig2.add_hrect(y0=ymin, y1=ymax, fillcolor=color, line_width=0,
                           annotation_text=label, annotation_position="right",
                           annotation_font_size=11)

        fig2.add_vline(x=Dc_1k, line_dash="dash", line_color="#888",
                       annotation_text=f"Dc = {Dc_1k:.1f} m",
                       annotation_position="top right", annotation_font_size=11)

        fig2.add_trace(go.Scatter(
            x=[r["Distancia (m)"] for r in resultados],
            y=[r["%ALcons"] for r in resultados],
            mode="lines+markers+text",
            text=[f"{r['%ALcons']}%" for r in resultados],
            textposition="top center",
            textfont=dict(size=10),
            line=dict(color="#378ADD", width=2.5),
            marker=dict(size=8),
        ))
        fig2.update_layout(
            xaxis_title="Distancia (m)", yaxis_title="%ALcons",
            yaxis=dict(range=[0, ymax_graf]),
            height=420, margin=dict(l=0, r=80, t=20, b=0),
            showlegend=False,
        )
        st.plotly_chart(fig2, use_container_width=True)

        # Interpretación automática
        st.markdown("#### Interpretación")
        dist_limite = next((r["Distancia (m)"] for r in resultados if r["%ALcons"] >= 15), None)
        if dist_limite:
            st.warning(f"La inteligibilidad es aceptable hasta **{dist_limite} m**. "
                       f"Más allá de esa distancia las pérdidas de consonantes son significativas.")
        else:
            st.success("La inteligibilidad es aceptable o mejor en todas las distancias evaluadas.")
        if RT_1k > 1.5:
            st.info(f"El RT₆₀ de {RT_1k:.2f} s en 1 kHz es elevado. "
                    f"Agregar materiales absorbentes reduciría el %ALcons.")

except ValueError:
    st.error("Formato inválido. Usa números separados por comas, ej: 1, 2, 5, 10")
