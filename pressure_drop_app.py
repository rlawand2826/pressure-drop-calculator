import streamlit as st
import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
import io  # ✅ Required for Excel download

# -----------------------------
# Function: Calculate screen area
# -----------------------------
def calculate_screen_area(strainer_type, od_mm, length_mm, height_mm=None):
    od = od_mm / 1000
    length = length_mm / 1000
    if strainer_type in ["Y-type", "T-type", "Basket"]:
        return math.pi * od * length  # Cylindrical surface
    elif strainer_type == "Cone" and height_mm is not None:
        r = od / 2
        h = height_mm / 1000
        return math.pi * r * math.sqrt(r**2 + h**2)  # Conical surface
    return 0

# -----------------------------
# Function: Pressure drop calculation
# -----------------------------
def pressure_drop_calc(A_pipe, A_screen, flow_m3_hr, rho, K, g):
    flow_m3_s = flow_m3_hr / 3600
    V_clean = flow_m3_s / A_screen
    deltaP_clean = (K * (rho / 1000) * (V_clean * 100)**2) / (2 * g) * 0.980665

    A_clogged = A_screen / 2
    V_clogged = flow_m3_s / A_clogged
    deltaP_clogged = (K * (rho / 1000) * (V_clogged * 100)**2) / (2 * g) * 0.980665

    return V_clean, V_clogged, deltaP_clean, deltaP_clogged

# -----------------------------
# UI
# -----------------------------
st.title("Pressure Drop Calculator for Strainers")

with st.form("data_input"):
    strainer_type = st.selectbox("Strainer Type", ["Y-type", "T-type", "Basket", "Cone"])
    pipe_id_mm = st.number_input("Pipe ID (mm)", value=52.48)
    od_mm = st.number_input("Screen OD (mm)", value=50.0)
    length_mm = st.number_input("Screen Length (mm)", value=200.0)
    height_mm = None
    if strainer_type == "Cone":
        height_mm = st.number_input("Cone Height (mm)", value=100.0)
    mesh_pct = st.number_input("Mesh Open Area (%)", value=40.0)
    perf_pct = st.number_input("Perforated Sheet Open Area (%)", value=60.0)
    flowrate = st.number_input("Flowrate (m³/hr)", value=10.0)
    density = st.number_input("Density (kg/m³)", value=1000.0)
    viscosity = st.number_input("Viscosity (cP)", value=1.0)
    K = st.slider("K (Loss Coefficient)", min_value=0.5, max_value=10.0, value=2.5, step=0.1)

    submitted = st.form_submit_button("Calculate")

# -----------------------------
# Calculations & Output
# -----------------------------
if submitted:
    g = 980
    alpha = (mesh_pct * perf_pct) / 10000

    A_pipe = (math.pi / 4) * (pipe_id_mm / 1000) ** 2
    A_screen = calculate_screen_area(strainer_type, od_mm, length_mm, height_mm) * alpha

    V_clean, V_clogged, dP_clean, dP_clogged = pressure_drop_calc(
        A_pipe, A_screen, flowrate, density, K, g
    )

    results = {
        "Pipe Area (m²)": round(A_pipe, 6),
        "Screen Area (m²)": round(A_screen, 6),
        "Free Flow Area Ratio": round(A_pipe / A_screen, 3),
        "Velocity Clean (m/s)": round(V_clean, 3),
        "Velocity 50% Clogged (m/s)": round(V_clogged, 3),
        "ΔP Clean (mbar)": round(dP_clean, 2),
        "ΔP 50% Clogged (mbar)": round(dP_clogged, 2)
    }

    df = pd.DataFrame([results])
    st.success("✅ Calculation Complete")
    st.table(df)

    # ✅ Fixed: Download Excel using BytesIO
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)

    st.download_button(
        label="📥 Download Excel",
        data=buffer,
        file_name="pressure_drop_result.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # 🔍 Plot Graph: Flowrate vs Pressure Drop
    flow_values = np.linspace(1, 20, 40)
    clean_dp_list, clog_dp_list = [], []
    for f in flow_values:
        _, _, dp_c, dp_clog = pressure_drop_calc(A_pipe, A_screen, f, density, K, g)
        clean_dp_list.append(dp_c)
        clog_dp_list.append(dp_clog)

    fig, ax = plt.subplots()
    ax.plot(flow_values, clean_dp_list, label="Clean", color='green')
    ax.plot(flow_values, clog_dp_list, label="50% Clogged", color='red')
    ax.set_xlabel("Flowrate (m³/hr)")
    ax.set_ylabel("Pressure Drop (mbar)")
    ax.set_title("Pressure Drop vs Flowrate")
    ax.grid(True)
    ax.legend()
    st.pyplot(fig)
