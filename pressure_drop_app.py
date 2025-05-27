
import streamlit as st
import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
import io
from PIL import Image
from fpdf import FPDF
import tempfile
import os

# Constants
GRAVITY = 980  # cm/s²
K_DEFAULT = 2.5  # Loss coefficient

# Calculate screen area
def calculate_screen_area(strainer_type, od_mm, length_mm, height_mm=None):
    od = od_mm / 1000
    length = length_mm / 1000
    if strainer_type in ["Y-type", "T-type", "Basket"]:
        return math.pi * od * length
    elif strainer_type == "Cone" and height_mm is not None:
        r = od / 2
        h = height_mm / 1000
        return math.pi * r * math.sqrt(r**2 + h**2)
    return 0

# Calculate pressure drop
def pressure_drop(A_pipe, A_screen, flow_m3_hr, rho, K):
    flow_m3_s = flow_m3_hr / 3600
    V_clean = flow_m3_s / A_screen
    V_clogged = flow_m3_s / (A_screen / 2)

    dP_clean = (K * (rho / 1000) * (V_clean * 100) ** 2) / (2 * GRAVITY) * 0.980665
    dP_clogged = (K * (rho / 1000) * (V_clogged * 100) ** 2) / (2 * GRAVITY) * 0.980665

    return round(V_clean, 3), round(V_clogged, 3), round(dP_clean, 2), round(dP_clogged, 2)

# Generate PDF report
def generate_pdf(data, graph_img_path):
    pdf = FPDF()
    pdf.add_page()
    logo_path = "pressure_drop_calculator/logo.png"
    pdf.image(logo_path, x=10, y=8, w=40)
    pdf.ln(25)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="STRAINER PRESSURE DROP CALCULATION", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", '', 10)

    for idx, d in enumerate(data):
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 8, txt=f"CASE {idx + 1}", ln=True)
        pdf.set_font("Arial", '', 10)
        for k, v in d.items():
            pdf.cell(100, 8, txt=f"{k}: {v}", ln=True)
        pdf.ln(3)

    pdf.image(graph_img_path, x=10, w=180)
    pdf.ln(5)

    # Add abbreviations
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="Abbreviations Used", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 8, txt="""
ΔP - Pressure drop
Re - Reynolds No.
C - Coefficient of discharge (From Perry page no. 5-40)
V - Superficial Velocity of fluid based upon the gross area of the screen m/sec
α - Effective opening area
D - Opening width (mm)
g - Gravitational force (m/s²)
Q - % opening in wire mesh
p - Density of media in kg/m³
P - % opening in perforated sheet
μ - Viscosity of media in cP
K - Velocity Head Loss (From Miller, D.S.-Internal Flow Systems)
""")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
        pdf.output(f.name)
        return f.name

# Streamlit UI
st.title("Strainer Pressure Drop Calculator")
num_cases = st.selectbox("Number of Cases", [1, 2], index=1)
cases = []

for i in range(num_cases):
    with st.expander(f"Case {i+1} Inputs"):
        strainer_type = st.selectbox("Strainer Type", ["Y-type", "T-type", "Basket", "Cone"], key=f"type{i}")
        pipe_id = st.number_input("Pipe ID (mm)", value=52.48, key=f"pipe{i}")
        od = st.number_input("Screen OD (mm)", value=50.0, key=f"od{i}")
        length = st.number_input("Screen Length (mm)", value=200.0, key=f"length{i}")
        height = None
        if strainer_type == "Cone":
            height = st.number_input("Cone Height (mm)", value=100.0, key=f"height{i}")
        mesh_pct = st.number_input("Mesh Open Area (%)", value=40.0, key=f"mesh{i}")
        perf_pct = st.number_input("Perforated Open Area (%)", value=60.0, key=f"perf{i}")
        flow = st.number_input("Flowrate (m³/hr)", value=10.0, key=f"flow{i}")
        density = st.number_input("Density (kg/m³)", value=1000.0, key=f"density{i}")
        viscosity = st.number_input("Viscosity (cP)", value=1.0, key=f"viscosity{i}")
        K = st.slider("Loss Coefficient K", 0.5, 10.0, K_DEFAULT, step=0.1, key=f"K{i}")

        alpha = (mesh_pct * perf_pct) / 10000
        A_pipe = math.pi / 4 * (pipe_id / 1000) ** 2
        A_screen = calculate_screen_area(strainer_type, od, length, height) * alpha
        V_clean, V_clogged, dP_clean, dP_clogged = pressure_drop(A_pipe, A_screen, flow, density, K)

        cases.append({
            "Strainer Type": strainer_type,
            "Pipe ID (mm)": pipe_id,
            "Screen Area (m²)": round(A_screen, 6),
            "Free Flow Ratio (Clean)": round(A_pipe / A_screen, 3),
            "Free Flow Ratio (50% Clogged)": round(A_pipe / (A_screen / 2), 3),
            "Velocity (Clean)": V_clean,
            "Velocity (Clogged)": V_clogged,
            "ΔP (Clean) [mbar]": dP_clean,
            "ΔP (50% Clogged) [mbar]": dP_clogged,
            "Flowrate (m³/hr)": flow
        })

if st.button("Generate Reports"):
    df = pd.DataFrame(cases)
    # Excel download
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Results")
    excel_buffer.seek(0)
    st.download_button("Download Excel Report", data=excel_buffer, file_name="Strainer_Report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # Plot graph
    flow_range = np.linspace(1, 20, 40)
    fig, ax = plt.subplots()
    for idx, case in enumerate(cases):
        A = case["Screen Area (m²)"]
        dp_values = [(2.5 * (1000 / 1000) * ((f / 3600 / A) * 100) ** 2) / (2 * GRAVITY) * 0.980665 for f in flow_range]
        ax.plot(flow_range, dp_values, label=f"Case {idx+1}")
    ax.set_xlabel("Flowrate (m³/hr)")
    ax.set_ylabel("Pressure Drop (mbar)")
    ax.set_title("Flow vs Pressure Drop")
    ax.grid(True)
    ax.legend()
    st.pyplot(fig)

    # Save graph for PDF
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as graph_img:
        fig.savefig(graph_img.name)
        pdf_path = generate_pdf(cases, graph_img.name)

    # PDF download
    with open(pdf_path, "rb") as f:
        st.download_button("Download PDF Report", data=f, file_name="Strainer_Report.pdf", mime="application/pdf")
