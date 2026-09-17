import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import datetime
try:
    from fpdf import FPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# ── CONSTANTS ─────────────────────────────────────────────────────
USD_GBP = 0.79
GBP_INR = 106.5
USD_EUR = 0.92
USD_JPY = 149.5

# ── MATERIAL DATABASE ─────────────────────────────────────────────
SUBSTRATE_DB = {
    # ESD Tray Materials
    "HIPS (Standard ESD)":          {"base_R": 1e13, "density": 1.05, "max_temp": 70,  "cost_kg": 1.8,  "category": "ESD Tray"},
    "PETG (Clear ESD)":             {"base_R": 1e14, "density": 1.27, "max_temp": 75,  "cost_kg": 2.2,  "category": "ESD Tray"},
    "PP (High-Temp ESD)":           {"base_R": 1e15, "density": 0.91, "max_temp": 100, "cost_kg": 1.5,  "category": "ESD Tray"},
    "ABS (Impact ESD)":             {"base_R": 1e13, "density": 1.05, "max_temp": 80,  "cost_kg": 2.0,  "category": "ESD Tray"},
    "PC (Polycarbonate ESD)":       {"base_R": 1e14, "density": 1.20, "max_temp": 120, "cost_kg": 3.5,  "category": "ESD Tray"},
    "PET (Polyester ESD)":          {"base_R": 1e14, "density": 1.38, "max_temp": 85,  "cost_kg": 2.0,  "category": "ESD Tray"},
    # Carrier Tape Materials
    "PS (Carrier Tape Standard)":   {"base_R": 1e14, "density": 1.05, "max_temp": 70,  "cost_kg": 1.6,  "category": "Carrier Tape"},
    "PEEK (Carrier Tape HT)":       {"base_R": 1e15, "density": 1.32, "max_temp": 250, "cost_kg": 85.0, "category": "Carrier Tape"},
    "PC (Carrier Tape Clear)":      {"base_R": 1e14, "density": 1.20, "max_temp": 120, "cost_kg": 3.5,  "category": "Carrier Tape"},
    # Foam Materials
    "PE Foam (Anti-Static Pink)":   {"base_R": 1e10, "density": 0.025,"max_temp": 70,  "cost_kg": 3.2,  "category": "Foam"},
    "PU Foam (ESD Black)":          {"base_R": 1e8,  "density": 0.035,"max_temp": 80,  "cost_kg": 4.5,  "category": "Foam"},
    "Kaizen Foam (Tool ESD)":       {"base_R": 1e9,  "density": 0.030,"max_temp": 65,  "cost_kg": 5.8,  "category": "Foam"},
    # Barrier Film Materials
    "PET/Al/Nylon/PE (MBB Std)":   {"base_R": 1e12, "density": 1.35, "max_temp": 85,  "cost_kg": 8.5,  "category": "Barrier Film"},
    "PET/Al/PE (MBB Thin)":        {"base_R": 1e12, "density": 1.30, "max_temp": 80,  "cost_kg": 7.2,  "category": "Barrier Film"},
    "VMPET/PE (MBB Economy)":      {"base_R": 1e11, "density": 1.28, "max_temp": 75,  "cost_kg": 5.5,  "category": "Barrier Film"},
    # Metal / Premium
    "Aluminium Tray (Type III)":    {"base_R": 1e-2, "density": 2.70, "max_temp": 300, "cost_kg": 12.0, "category": "Metal"},
    "Stainless Steel Tray":         {"base_R": 1e-4, "density": 7.90, "max_temp": 500, "cost_kg": 18.0, "category": "Metal"},
}

COMPLIANCE_STANDARDS = {
    "JEDEC JESD625 (General Semiconductor)": {
        "esd_min": 1e4, "esd_max": 1e11,
        "mvtr_max": 0.005, "hardness_min": "H",
        "industries": ["Consumer", "Industrial", "Medical"],
        "regions": ["Global"]
    },
    "IEC 61340-5-1 (European ESD)": {
        "esd_min": 1e4, "esd_max": 1e11,
        "mvtr_max": 0.005, "hardness_min": "H",
        "industries": ["Industrial", "Automotive"],
        "regions": ["Europe", "Global"]
    },
    "AEC-Q100 (Automotive Grade)": {
        "esd_min": 1e4, "esd_max": 1e9,
        "mvtr_max": 0.002, "hardness_min": "2H",
        "industries": ["Automotive"],
        "regions": ["Global"]
    },
    "MIL-PRF-81705D (Defence/Aerospace)": {
        "esd_min": 1e4, "esd_max": 1e11,
        "mvtr_max": 0.002, "hardness_min": "2H",
        "industries": ["Defence", "Aerospace"],
        "regions": ["USA", "NATO"]
    },
    "JESD22-A114 (ESD HBM Sensitive)": {
        "esd_min": 1e4, "esd_max": 1e8,
        "mvtr_max": 0.003, "hardness_min": "H",
        "industries": ["Semiconductor", "Medical"],
        "regions": ["Global"]
    },
    "IPC-A-600 (PCB Assembly)": {
        "esd_min": 1e5, "esd_max": 1e11,
        "mvtr_max": 0.010, "hardness_min": "HB",
        "industries": ["Electronics Assembly"],
        "regions": ["Global"]
    },
}

HARDNESS_ORDER = ["B", "HB", "H", "2H", "3H", "4H", "5H+"]

CNT_PRICE_GBP  = 800
CLAY_PRICE_GBP = 25
SIO2_PRICE_GBP = 350

# ── LITERATURE-CITED PERCOLATION THRESHOLDS (wt% MWCNT) ──────────
# Matrix-specific — thermoplastics percolate at higher loading than
# epoxy due to melt-mixing dispersion vs. epoxy casting dispersion.
CITATIONS = {
    "epoxy_mohan": {
        "authors": "Mohan, N. et al.",
        "year": "2019",
        "title": "Determination of electrical percolation threshold of carbon nanotube-based epoxy nanocomposites and its experimental validation",
        "journal": "IET Science, Measurement & Technology",
        "finding": "Measured 0.17 wt% experimentally; 0.18 wt% theoretical (modified micromechanics model)",
        "url": "https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/iet-smt.2019.0011"
    },
    "pp_mwcnt": {
        "authors": "Multiple sources, MWCNT/PP composite literature",
        "year": "various",
        "title": "MWCNT percolation in polypropylene matrix",
        "journal": "Reported across PP/CNT composite studies",
        "finding": "Percolation threshold of approx. 2.0 wt% for high-aspect-ratio MWCNT in PP",
        "url": "https://www.researchgate.net/publication/226511004"
    },
    "pc_cnt": {
        "authors": "Study on LLDPE/PC conductive polymer composites",
        "year": "2022",
        "title": "Effect of Various Conductive Filler Additions on the Percolation Threshold of Conductive Polymer Composites",
        "journal": "Polymer Composites research",
        "finding": "PC-CNT percolation threshold approx. 1 wt%; PC-CF approx. 10 wt%",
        "url": "https://www.researchgate.net/publication/363787753"
    },
    "review_range": {
        "authors": "ScienceDirect Topics review",
        "year": "ongoing",
        "title": "Electrical Percolation Threshold — an overview",
        "journal": "ScienceDirect Topics (aggregated review)",
        "finding": "CNT percolation in polymers ranges 0.0025-15 wt%; thermoplastics typically 1-3 wt%",
        "url": "https://www.sciencedirect.com/topics/engineering/electrical-percolation-threshold"
    },
}

MATERIAL_PHI_C = {
    "HIPS (Standard ESD)":        {"phi_c": 1.5, "cite": "review_range", "basis": "estimated"},
    "PETG (Clear ESD)":           {"phi_c": 1.2, "cite": "review_range", "basis": "estimated"},
    "PP (High-Temp ESD)":         {"phi_c": 2.0, "cite": "pp_mwcnt",     "basis": "cited"},
    "ABS (Impact ESD)":           {"phi_c": 1.5, "cite": "review_range", "basis": "estimated"},
    "PC (Polycarbonate ESD)":     {"phi_c": 1.0, "cite": "pc_cnt",       "basis": "cited"},
    "PET (Polyester ESD)":        {"phi_c": 1.2, "cite": "review_range", "basis": "estimated"},
    "PS (Carrier Tape Standard)": {"phi_c": 1.5, "cite": "review_range", "basis": "estimated"},
    "PEEK (Carrier Tape HT)":     {"phi_c": 2.5, "cite": "review_range", "basis": "estimated"},
    "PC (Carrier Tape Clear)":    {"phi_c": 1.0, "cite": "pc_cnt",       "basis": "cited"},
}
DEFAULT_PHI_C_EPOXY = 0.18  # CITATIONS["epoxy_mohan"]

# ── PHYSICS MODELS ────────────────────────────────────────────────
def get_phi_c(material_key):
    """Return the percolation threshold for this material — user calibration
    overrides everything if set; otherwise use the material-specific
    literature value; fall back to the epoxy value only if truly unknown."""
    override_key = f"calibrated_phi_c__{material_key}"
    if override_key in st.session_state:
        return st.session_state[override_key]
    if material_key in MATERIAL_PHI_C:
        return MATERIAL_PHI_C[material_key]["phi_c"]
    return DEFAULT_PHI_C_EPOXY

def get_uncertainty_pct(material_key):
    """Confidence band width — tighter for measured/cited data, wider for estimates."""
    override_key = f"calibrated_phi_c__{material_key}"
    if override_key in st.session_state:
        return 0.05   # your own measured data — ±5%
    if material_key in MATERIAL_PHI_C and MATERIAL_PHI_C[material_key]["basis"] == "cited":
        return 0.15   # published, material-specific paper — ±15%
    return 0.40        # estimated from a general range — ±40%

def get_basis_label(material_key):
    override_key = f"calibrated_phi_c__{material_key}"
    if override_key in st.session_state:
        return "measured"
    if material_key in MATERIAL_PHI_C:
        return MATERIAL_PHI_C[material_key]["basis"]
    return "estimated"

# ── REACH / RoHS FLAGS (raw material components) ──────────────────
REGULATORY_DB = {
    "MWCNT (Multi-Wall Carbon Nanotubes)": {"REACH": True, "RoHS": True, "note": "REACH registered (EU); no RoHS-restricted substances"},
    "Nano-clay (Organo-MMT)":               {"REACH": True, "RoHS": True, "note": "REACH registered; naturally occurring mineral, quaternary ammonium surface treatment REACH-compliant"},
    "SiO2 nanoparticles (colloidal)":       {"REACH": True, "RoHS": True, "note": "REACH registered; silica is not RoHS-restricted"},
    "ESD-grade HIPS/PETG/PP/ABS/PC":        {"REACH": True, "RoHS": True, "note": "Standard engineering plastics — REACH & RoHS compliant grades widely available"},
}

# ── ENVIRONMENTAL FOOTPRINT (simplified estimate — clearly labelled) ─
def estimate_co2_footprint(is_domestic=True, weight_kg=1.0):
    """
    Simplified transport-only CO2e estimate. NOT a full LCA.
    Domestic (UK road, <300 miles): ~0.10 kg CO2e/kg-km-equivalent, assumed 150 miles avg
    Imported (sea freight Asia->UK + last-mile road): ~0.015 kg CO2e/tonne-km sea + air-freight premium if urgent
    These are simplified DEFRA-style factors for illustration, not a certified LCA.
    """
    domestic_factor = 0.012   # kg CO2e per kg, UK road freight ~150 miles
    import_sea_factor = 0.045 # kg CO2e per kg, sea freight Asia-UK + last mile
    import_air_factor = 0.850 # kg CO2e per kg, air freight Asia-UK (if expedited)
    domestic_co2 = weight_kg * domestic_factor
    import_sea_co2 = weight_kg * import_sea_factor
    import_air_co2 = weight_kg * import_air_factor
    return domestic_co2, import_sea_co2, import_air_co2

def build_pdf_report(report_text, material_key, standard_key, compliant):
    """Builds a simple branded one-page PDF summary. Returns bytes."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(13, 27, 75)
    pdf.rect(0, 0, 210, 28, 'F')
    pdf.set_text_color(201, 168, 76)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_xy(10, 8)
    pdf.cell(0, 10, "NanoSeal Sim - Formulation Report", ln=1)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_xy(10, 19)
    pdf.cell(0, 6, "Sahastra Mudra Ltd. (SC848171)  |  nanoseal-sim.streamlit.app", ln=1)

    pdf.set_text_color(20, 20, 20)
    pdf.set_xy(10, 34)
    pdf.set_font("Helvetica", "B", 11)
    status_txt = "COMPLIANT" if compliant else "NOT COMPLIANT"
    pdf.cell(0, 8, f"Material: {material_key}  |  Standard: {standard_key}  |  Status: {status_txt}", ln=1)

    pdf.set_font("Courier", "", 8)
    pdf.set_xy(10, 44)
    for line in report_text.split("\n"):
        safe_line = line.encode("latin-1", "replace").decode("latin-1")
        pdf.multi_cell(0, 4, safe_line)

    pdf.set_y(-15)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 10, f"Generated {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} | Prithviraj Hiralal Chowdhary, M.Sc. Nanoscience, University of Glasgow", 0, 0, 'C')

    return bytes(pdf.output(dest='S'))

def esd_surface_resistance(cnt_wt, thickness_nm, material_key):
    mat = SUBSTRATE_DB[material_key]
    R_base = mat["base_R"]
    if material_key in ["Aluminium Tray (Type III)", "Stainless Steel Tray"]:
        return R_base, True
    if material_key in ["PE Foam (Anti-Static Pink)", "PU Foam (ESD Black)", "Kaizen Foam (Tool ESD)"]:
        if cnt_wt == 0:
            return R_base, 1e4 <= R_base <= 1e11
        R = R_base * (1 - min(cnt_wt / 0.5, 0.9))
        return max(R, 1e3), 1e4 <= R <= 1e11
    phi_c = get_phi_c(material_key)
    if cnt_wt < phi_c:
        R = R_base * (1 - cnt_wt / phi_c * 0.5)
    else:
        t = 1.3
        phi = cnt_wt / 100
        phi_c_vol = phi_c / 100
        sigma_max = 1e5
        sigma = sigma_max * ((phi - phi_c_vol) / (1 - phi_c_vol)) ** t
        tf = np.log10(max(thickness_nm, 6) / 5) / np.log10(100)
        tf = np.clip(tf, 0.1, 2.0)
        thickness_m = thickness_nm * 1e-9
        R = 1 / (sigma * tf * thickness_m)
        R = np.clip(R, 1e2, 1e14)
    return R, True  # compliance checked against standard later

def mvtr_nano_clay(clay_wt, aspect_ratio=150, base_mvtr=0.020):
    clay_density, polymer_density = 2.86, 1.20
    phi = (clay_wt / 100) / (clay_wt / 100 + (1 - clay_wt / 100) * (clay_density / polymer_density))
    tau = 1 + (aspect_ratio * phi) / 2
    mvtr = base_mvtr / tau
    return mvtr, base_mvtr / mvtr

def sio2_hardness(sio2_wt, particle_size_nm=25):
    E_p, E_s = 3.5, 70.0
    phi = sio2_wt / 100
    xi = 2.0
    eta = (E_s / E_p - 1) / (E_s / E_p + xi)
    E_c = E_p * (1 + xi * eta * phi) / (1 - eta * phi)
    H = E_c / 14
    if H < 0.30:   p = "B"
    elif H < 0.40: p = "HB"
    elif H < 0.55: p = "H"
    elif H < 0.70: p = "2H"
    elif H < 0.90: p = "3H"
    elif H < 1.10: p = "4H"
    else:           p = "5H+"
    return H, p

def thermal_resistance(material_key, thickness_nm):
    thermal_k = {
        "HIPS (Standard ESD)": 0.17, "PETG (Clear ESD)": 0.29,
        "PP (High-Temp ESD)": 0.22, "ABS (Impact ESD)": 0.17,
        "PC (Polycarbonate ESD)": 0.20, "PET (Polyester ESD)": 0.24,
        "PS (Carrier Tape Standard)": 0.16, "PEEK (Carrier Tape HT)": 0.25,
        "PC (Carrier Tape Clear)": 0.20,
        "PE Foam (Anti-Static Pink)": 0.038, "PU Foam (ESD Black)": 0.025,
        "Kaizen Foam (Tool ESD)": 0.030,
        "PET/Al/Nylon/PE (MBB Std)": 0.35, "PET/Al/PE (MBB Thin)": 0.33,
        "VMPET/PE (MBB Economy)": 0.28,
        "Aluminium Tray (Type III)": 205.0, "Stainless Steel Tray": 16.0,
    }
    k = thermal_k.get(material_key, 0.20)
    t_m = thickness_nm * 1e-9
    R_th = t_m / k  # K·m²/W
    return R_th * 1e6, k  # return in µK·m²/W and conductivity

def coating_cost(cnt_wt, clay_wt, sio2_wt, thickness_nm, material_key):
    mat = SUBSTRATE_DB[material_key]
    density = 1.1
    t_cm = thickness_nm * 1e-7
    weight = density * t_cm * 1e6  # g/m²
    cnt_c  = weight * (cnt_wt  / 100) * CNT_PRICE_GBP  / 1000
    clay_c = weight * (clay_wt / 100) * CLAY_PRICE_GBP / 1000
    sio2_c = weight * (sio2_wt / 100) * SIO2_PRICE_GBP / 1000
    substrate_c = mat["cost_kg"] * density * t_cm * 0.1
    total = cnt_c + clay_c + sio2_c
    return total, weight, substrate_c

def check_compliance(R_surface, mvtr, pencil, standard_key, material_key):
    std = COMPLIANCE_STANDARDS[standard_key]
    mat = SUBSTRATE_DB[material_key]
    esd_pass  = std["esd_min"] <= R_surface <= std["esd_max"]
    mvtr_pass = mvtr <= std["mvtr_max"]
    h_idx     = HARDNESS_ORDER.index(pencil) if pencil in HARDNESS_ORDER else 0
    h_min_idx = HARDNESS_ORDER.index(std["hardness_min"])
    hard_pass = h_idx >= h_min_idx
    temp_pass = mat["max_temp"] >= 85
    return {
        "ESD": esd_pass, "MVTR": mvtr_pass,
        "Hardness": hard_pass, "Temperature": temp_pass,
        "Overall": esd_pass and mvtr_pass and hard_pass and temp_pass
    }

def auto_optimise(material_key, standard_key, thickness_nm, aspect_ratio, base_mvtr, sio2_wt, particle_size):
    std = COMPLIANCE_STANDARDS[standard_key]
    best = None
    best_cost = 1e9
    for cnt in np.arange(0.05, 3.0, 0.05):
        for clay in np.arange(0.5, 10.0, 0.5):
            R, _ = esd_surface_resistance(cnt, thickness_nm, material_key)
            mvtr, _ = mvtr_nano_clay(clay, aspect_ratio, base_mvtr)
            H, pencil = sio2_hardness(sio2_wt, particle_size)
            c = check_compliance(R, mvtr, pencil, standard_key, material_key)
            if c["Overall"]:
                cost, _, _ = coating_cost(cnt, clay, sio2_wt, thickness_nm, material_key)
                if cost < best_cost:
                    best_cost = cost
                    best = {"cnt": cnt, "clay": clay, "cost": cost,
                            "R": R, "mvtr": mvtr, "pencil": pencil}
    return best

# ── UI ─────────────────────────────────────────────────────────────
def main():
    st.set_page_config(page_title="NanoSeal Sim v2", page_icon="🔬", layout="wide")

    st.markdown("""
    <style>
    .header {
        background: linear-gradient(135deg, #0D1B4B, #1A237E);
        padding: 24px 32px; border-radius: 8px; margin-bottom: 16px;
    }
    .header h1 { color: #C9A84C; margin: 0; font-size: 26px; }
    .header p  { color: #90CAF9; margin: 4px 0 0 0; font-size: 13px; }
    .badge { display:inline-block; padding:2px 8px; border-radius:4px;
             font-size:11px; font-weight:600; margin:2px; }
    </style>
    <div class="header">
        <h1>🔬 NanoSeal Sim &nbsp; <span style="font-size:14px;color:#90CAF9;font-weight:400">v2.0 — Global Semiconductor Packaging Platform</span></h1>
        <p>16 materials · 6 international standards · Auto-optimiser · Multi-currency · Thermal analysis · 
        Sahastra Mudra Ltd. SC848171 · University of Glasgow Nano-fabrication Research</p>
    </div>
    """, unsafe_allow_html=True)

    # ── SIDEBAR ────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")

        st.markdown("**Material & Standard**")
        categories = list(set(v["category"] for v in SUBSTRATE_DB.values()))
        selected_cat = st.selectbox("Material category", sorted(categories))
        materials_in_cat = [k for k, v in SUBSTRATE_DB.items() if v["category"] == selected_cat]
        material_key = st.selectbox("Substrate material", materials_in_cat)
        standard_key = st.selectbox("Compliance standard", list(COMPLIANCE_STANDARDS.keys()))

        st.divider()
        st.markdown("**Currency**")
        currency = st.selectbox("Display currency", ["GBP £", "INR ₹", "USD $", "EUR €", "JPY ¥"])

        st.divider()
        st.markdown("**Layer 1 — CNT ESD Coating**")
        cnt_wt = st.slider("MWCNT concentration (wt%)", 0.0, 5.0, 0.5, 0.05)
        thickness_nm = st.slider("Coating thickness (nm)", 5, 500, 50, 5)

        st.markdown("**Layer 2 — Nano-Clay Barrier**")
        clay_wt = st.slider("Nano-clay loading (wt%)", 0.0, 10.0, 3.0, 0.5)
        aspect_ratio = st.slider("Platelet aspect ratio", 50, 300, 150, 10)
        base_mvtr = st.number_input("Base MVTR (g/m²/day)", 0.001, 0.1, 0.020, 0.001, format="%.3f")

        st.markdown("**Layer 3 — SiO₂ Scratch Coat**")
        sio2_wt = st.slider("SiO₂ loading (wt%)", 0.0, 40.0, 15.0, 1.0)
        particle_size = st.slider("Particle size (nm)", 10, 50, 25, 5)

    # ── CALCULATIONS ───────────────────────────────────────────────
    R_surface, _ = esd_surface_resistance(cnt_wt, thickness_nm, material_key)
    mvtr, mvtr_improve = mvtr_nano_clay(clay_wt, aspect_ratio, base_mvtr)
    H_gpa, pencil = sio2_hardness(sio2_wt, particle_size)
    R_th, k_th = thermal_resistance(material_key, thickness_nm)
    cost_m2, coat_wt, sub_cost = coating_cost(cnt_wt, clay_wt, sio2_wt, thickness_nm, material_key)
    compliance = check_compliance(R_surface, mvtr, pencil, standard_key, material_key)

    def fmt_currency(gbp_val):
        if currency == "GBP £":   return f"£{gbp_val:.4f}"
        elif currency == "INR ₹": return f"₹{gbp_val * GBP_INR:.2f}"
        elif currency == "USD $": return f"${gbp_val / USD_GBP:.4f}"
        elif currency == "EUR €": return f"€{gbp_val / USD_GBP * USD_EUR:.4f}"
        else:                      return f"¥{gbp_val / USD_GBP * USD_JPY:.1f}"

    # ── COMPLIANCE BANNER ──────────────────────────────────────────
    std = COMPLIANCE_STANDARDS[standard_key]
    if compliance["Overall"]:
        st.success(f"✅ **COMPLIANT** — Meets **{standard_key}** for {', '.join(std['industries'])} | Regions: {', '.join(std['regions'])}")
    else:
        fails = [k for k, v in compliance.items() if not v and k != "Overall"]
        st.error(f"❌ **NOT COMPLIANT** with {standard_key} — Failing: {', '.join(fails)}")

    # ── METRICS ROW ────────────────────────────────────────────────
    unc_pct = get_uncertainty_pct(material_key)
    basis_lbl = get_basis_label(material_key)
    R_low, R_high = R_surface * (1 - unc_pct), R_surface * (1 + unc_pct)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("ESD Resistance", f"{R_surface:.2e} Ω/sq",
                  delta="✅ Pass" if compliance["ESD"] else "❌ Fail",
                  delta_color="normal" if compliance["ESD"] else "inverse")
        st.caption(f"Target: {std['esd_min']:.0e}–{std['esd_max']:.0e} Ω/sq")
        st.caption(f"±{unc_pct*100:.0f}% range ({basis_lbl}): {R_low:.1e}–{R_high:.1e}")
    with c2:
        st.metric("MVTR", f"{mvtr:.4f} g/m²/day",
                  delta=f"{mvtr_improve:.1f}× better | {'✅' if compliance['MVTR'] else '❌'}",
                  delta_color="normal" if compliance["MVTR"] else "inverse")
        st.caption(f"Target: <{std['mvtr_max']} g/m²/day")
    with c3:
        st.metric("Scratch Resistance", f"{pencil} ({H_gpa:.2f} GPa)",
                  delta="✅ Pass" if compliance["Hardness"] else f"❌ Need {std['hardness_min']}",
                  delta_color="normal" if compliance["Hardness"] else "inverse")
    with c4:
        st.metric("Thermal Resistance", f"{R_th:.2f} µK·m²/W",
                  delta=f"k = {k_th:.2f} W/m·K",
                  delta_color="off")
        st.caption(f"Max temp: {SUBSTRATE_DB[material_key]['max_temp']}°C")
    with c5:
        st.metric("Coating cost/m²", fmt_currency(cost_m2),
                  delta=f"{fmt_currency(cost_m2 * 0.05)} per tray",
                  delta_color="off")
        st.caption(f"{coat_wt:.2f} g/m² applied")

    st.divider()

    # ── TABS ───────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11 = st.tabs([
        "📈 ESD Analysis",
        "💧 MVTR Analysis",
        "🌡️ Thermal",
        "🔀 Substrate Compare",
        "🌍 Standards Compare",
        "🤖 Auto-Optimiser",
        "📋 Report",
        "🎯 Calibrate & Compare",
        "🏭 Scale-Up Calculator",
        "✅ Compliance & Footprint",
        "💾 Saved Formulations"
    ])

    # TAB 1 — ESD
    with tab1:
        cnt_range = np.linspace(0.01, 5.0, 200)
        R_range = [esd_surface_resistance(c, thickness_nm, material_key)[0] for c in cnt_range]
        R_range_low = [r * (1 - unc_pct) for r in R_range]
        R_range_high = [r * (1 + unc_pct) for r in R_range]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=cnt_range + cnt_range[::-1],
                                  y=R_range_high + R_range_low[::-1],
                                  fill='toself', fillcolor='rgba(26,35,126,0.12)',
                                  line=dict(width=0), showlegend=True,
                                  name=f"±{unc_pct*100:.0f}% confidence ({basis_lbl})"))
        fig.add_trace(go.Scatter(x=cnt_range, y=R_range, mode='lines',
                                  name=material_key, line=dict(color='#1A237E', width=2.5)))
        fig.add_hrect(y0=std["esd_min"], y1=std["esd_max"],
                      fillcolor="rgba(201,168,76,0.15)", line_width=0,
                      annotation_text=f"Target zone ({standard_key})")
        fig.add_vline(x=cnt_wt, line_dash="dash", line_color="#C9A84C",
                      annotation_text=f"Current: {cnt_wt} wt%")
        fig.update_layout(title="ESD Surface Resistance vs CNT Loading",
                          xaxis_title="CNT (wt%)", yaxis_title="Resistance (Ω/sq)",
                          yaxis_type="log", height=380, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
        st.info(f"**Percolation threshold for {material_key}:** {get_phi_c(material_key)} wt% "
                f"({basis_lbl} — see Calibrate & Compare tab for source). "
                f"Above this, resistance drops several orders of magnitude. "
                f"Shaded band reflects prediction confidence: cited data ±15%, estimated ±40%, your own measured data ±5%.")

    # TAB 2 — MVTR
    with tab2:
        col_a, col_b = st.columns(2)
        with col_a:
            clay_range = np.linspace(0.1, 10.0, 100)
            mvtr_range = [mvtr_nano_clay(c, aspect_ratio, base_mvtr)[0] for c in clay_range]
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=clay_range, y=mvtr_range, mode='lines',
                                       name='MVTR', line=dict(color='#004D40', width=2.5)))
            fig2.add_hrect(y0=0, y1=std["mvtr_max"], fillcolor="rgba(201,168,76,0.15)",
                           line_width=0, annotation_text="Target zone")
            fig2.add_vline(x=clay_wt, line_dash="dash", line_color="#C9A84C",
                           annotation_text=f"Current: {clay_wt} wt%")
            fig2.update_layout(title="MVTR vs Nano-Clay Loading",
                               xaxis_title="Nano-clay (wt%)",
                               yaxis_title="MVTR (g/m²/day)", height=360, template="plotly_white")
            st.plotly_chart(fig2, use_container_width=True)
        with col_b:
            ar_range = np.linspace(50, 300, 100)
            mvtr_ar = [mvtr_nano_clay(clay_wt, ar, base_mvtr)[0] for ar in ar_range]
            fig2b = go.Figure()
            fig2b.add_trace(go.Scatter(x=ar_range, y=mvtr_ar, mode='lines',
                                        name='MVTR vs Aspect Ratio',
                                        line=dict(color='#1B5E20', width=2.5)))
            fig2b.add_hrect(y0=0, y1=std["mvtr_max"], fillcolor="rgba(201,168,76,0.15)",
                            line_width=0, annotation_text="Target zone")
            fig2b.add_vline(x=aspect_ratio, line_dash="dash", line_color="#C9A84C",
                            annotation_text=f"Current: {aspect_ratio}:1")
            fig2b.update_layout(title="MVTR vs Platelet Aspect Ratio",
                                xaxis_title="Aspect ratio (L/t)",
                                yaxis_title="MVTR (g/m²/day)", height=360, template="plotly_white")
            st.plotly_chart(fig2b, use_container_width=True)
        st.info(f"**Nielsen model:** Higher aspect ratio MMT platelets create longer tortuous paths. "
                f"Cloisite 20A (aspect ratio ~150) vs Cloisite 30B (~120) — 25% MVTR difference at same loading.")

    # TAB 3 — THERMAL
    with tab3:
        st.markdown("#### Thermal Performance Analysis")
        mat_info = SUBSTRATE_DB[material_key]
        tc1, tc2, tc3 = st.columns(3)
        with tc1:
            st.metric("Thermal conductivity", f"{k_th:.3f} W/m·K")
        with tc2:
            st.metric("Max operating temp", f"{mat_info['max_temp']}°C",
                      delta="✅ AEC-Q100 85°C" if mat_info['max_temp'] >= 85 else "❌ Below 85°C",
                      delta_color="normal" if mat_info['max_temp'] >= 85 else "inverse")
        with tc3:
            st.metric("Thermal resistance", f"{R_th:.2f} µK·m²/W")

        temp_data = {k: SUBSTRATE_DB[k]["max_temp"] for k in SUBSTRATE_DB}
        df_temp = pd.DataFrame(list(temp_data.items()), columns=["Material", "Max Temp (°C)"])
        df_temp = df_temp.sort_values("Max Temp (°C)", ascending=True)
        colors_bar = ["#1B5E20" if t >= 85 else "#B71C1C" for t in df_temp["Max Temp (°C)"]]
        fig_t = go.Figure(go.Bar(x=df_temp["Max Temp (°C)"], y=df_temp["Material"],
                                  orientation='h', marker_color=colors_bar))
        fig_t.add_vline(x=85, line_dash="dash", line_color="#C9A84C",
                        annotation_text="AEC-Q100 min (85°C)")
        fig_t.add_vline(x=125, line_dash="dot", line_color="#E65100",
                        annotation_text="Automotive high-temp (125°C)")
        fig_t.update_layout(title="Maximum Operating Temperature by Material",
                            xaxis_title="Temperature (°C)", height=500, template="plotly_white")
        st.plotly_chart(fig_t, use_container_width=True)

    # TAB 4 — SUBSTRATE COMPARE
    with tab4:
        st.markdown("#### All Materials — ESD Performance Comparison")
        fig4 = go.Figure()
        cat_colors = {"ESD Tray": "#1A237E", "Carrier Tape": "#004D40",
                      "Foam": "#E65100", "Barrier Film": "#6A1B9A", "Metal": "#B71C1C"}
        cnt_range_all = np.linspace(0.01, 3.0, 150)
        for mat_name, mat_props in SUBSTRATE_DB.items():
            if mat_name in ["Aluminium Tray (Type III)", "Stainless Steel Tray"]:
                continue
            R_all = [esd_surface_resistance(c, thickness_nm, mat_name)[0] for c in cnt_range_all]
            fig4.add_trace(go.Scatter(x=cnt_range_all, y=R_all, mode='lines',
                                       name=mat_name,
                                       line=dict(color=cat_colors[mat_props["category"]], width=1.5),
                                       opacity=0.8))
        fig4.add_hrect(y0=std["esd_min"], y1=std["esd_max"],
                       fillcolor="rgba(201,168,76,0.15)", line_width=0,
                       annotation_text=f"Target: {standard_key}")
        fig4.update_layout(title="ESD Surface Resistance — All Materials",
                           xaxis_title="CNT (wt%)", yaxis_title="Resistance (Ω/sq)",
                           yaxis_type="log", height=420, template="plotly_white")
        st.plotly_chart(fig4, use_container_width=True)

        st.markdown("#### Current formulation — all materials at a glance")
        rows = []
        for mat_name, mat_props in SUBSTRATE_DB.items():
            R, _ = esd_surface_resistance(cnt_wt, thickness_nm, mat_name)
            m, _ = mvtr_nano_clay(clay_wt, aspect_ratio, base_mvtr)
            _, p = sio2_hardness(sio2_wt, particle_size)
            comp = check_compliance(R, m, p, standard_key, mat_name)
            cost_v, _, _ = coating_cost(cnt_wt, clay_wt, sio2_wt, thickness_nm, mat_name)
            rows.append({
                "Category": mat_props["category"],
                "Material": mat_name,
                "ESD (Ω/sq)": f"{R:.2e}",
                "MVTR (g/m²/day)": f"{m:.4f}",
                "Hardness": p,
                "Max Temp (°C)": mat_props["max_temp"],
                "Cost/m²": fmt_currency(cost_v),
                "Overall": "✅ Pass" if comp["Overall"] else "❌ Fail"
            })
        df_all = pd.DataFrame(rows).sort_values(["Category", "Material"])
        st.dataframe(df_all, use_container_width=True, hide_index=True)

    # TAB 5 — STANDARDS COMPARE
    with tab5:
        st.markdown("#### Your formulation checked against all 6 international standards")
        std_rows = []
        for std_name, std_vals in COMPLIANCE_STANDARDS.items():
            comp_s = check_compliance(R_surface, mvtr, pencil, std_name, material_key)
            std_rows.append({
                "Standard": std_name,
                "Industries": ", ".join(std_vals["industries"]),
                "Regions": ", ".join(std_vals["regions"]),
                "ESD range": f"{std_vals['esd_min']:.0e}–{std_vals['esd_max']:.0e}",
                "MVTR limit": f"<{std_vals['mvtr_max']}",
                "ESD": "✅" if comp_s["ESD"] else "❌",
                "MVTR": "✅" if comp_s["MVTR"] else "❌",
                "Hardness": "✅" if comp_s["Hardness"] else "❌",
                "Overall": "✅ PASS" if comp_s["Overall"] else "❌ FAIL"
            })
        df_std = pd.DataFrame(std_rows)
        st.dataframe(df_std, use_container_width=True, hide_index=True)
        passes = sum(1 for r in std_rows if "PASS" in r["Overall"])
        st.info(f"Your current formulation passes **{passes} of 6** international standards.")

    # TAB 6 — AUTO OPTIMISER
    with tab6:
        st.markdown("#### 🤖 Automatic Formulation Optimiser")
        st.markdown(f"Finds the **cheapest compliant formulation** for **{material_key}** under **{standard_key}**")
        st.markdown("This searches 2,400 formulation combinations and returns the lowest-cost passing mix.")

        if st.button("🔍 Run Optimiser", type="primary"):
            with st.spinner("Searching 2,400 formulation combinations..."):
                result = auto_optimise(material_key, standard_key, thickness_nm,
                                       aspect_ratio, base_mvtr, sio2_wt, particle_size)
            if result:
                st.success("✅ Optimal formulation found!")
                oc1, oc2, oc3, oc4 = st.columns(4)
                with oc1:
                    st.metric("Optimal CNT loading", f"{result['cnt']:.2f} wt%",
                              delta=f"vs current {cnt_wt} wt%",
                              delta_color="normal" if result['cnt'] < cnt_wt else "inverse")
                with oc2:
                    st.metric("Optimal clay loading", f"{result['clay']:.1f} wt%",
                              delta=f"vs current {clay_wt} wt%")
                with oc3:
                    st.metric("Minimum cost/m²", fmt_currency(result['cost']))
                with oc4:
                    saving = cost_m2 - result['cost']
                    st.metric("Cost saving vs current", fmt_currency(abs(saving)),
                              delta="cheaper" if saving > 0 else "more expensive")
                st.markdown(f"""
                **Optimal formulation summary:**
                - CNT: **{result['cnt']:.2f} wt%** → ESD: {result['R']:.2e} Ω/sq ✅
                - Nano-clay: **{result['clay']:.1f} wt%** → MVTR: {result['mvtr']:.5f} g/m²/day ✅
                - SiO₂: **{sio2_wt} wt%** (unchanged) → Hardness: {result['pencil']} ✅
                - Material cost: **{fmt_currency(result['cost'])}/m²**
                """)
            else:
                st.error("No compliant formulation found within search range. "
                         "Try increasing coating thickness or changing material.")

    # TAB 7 — REPORT
    with tab7:
        st.markdown("#### 📋 Full Formulation Report")
        report = f"""
NANOSEAL SIM v2.0 — GLOBAL SEMICONDUCTOR PACKAGING REPORT
Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
Sahastra Mudra Ltd. (SC848171) | Prithviraj Hiralal Chowdhary
M.Sc. Nanoscience & Nanotechnology, University of Glasgow (2025)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMULATION INPUTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Material:               {material_key}
Compliance standard:    {standard_key}
Industries:             {', '.join(std['industries'])}
Regions:                {', '.join(std['regions'])}

Layer 1 — CNT ESD Coating
  MWCNT concentration:  {cnt_wt} wt%
  Coating thickness:    {thickness_nm} nm

Layer 2 — Nano-Clay Barrier
  MMT concentration:    {clay_wt} wt%
  Platelet aspect ratio:{aspect_ratio}:1
  Base MVTR:            {base_mvtr:.3f} g/m2/day

Layer 3 — SiO2 Scratch Coat
  SiO2 loading:         {sio2_wt} wt%
  Particle size:        {particle_size} nm

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PREDICTED PERFORMANCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ESD Surface Resistance: {R_surface:.3e} Ohm/sq   {'PASS' if compliance['ESD'] else 'FAIL'}
MVTR (nano-clay):       {mvtr:.5f} g/m2/day  {'PASS' if compliance['MVTR'] else 'FAIL'}
MVTR improvement:       {mvtr_improve:.1f}x better than uncoated
Scratch resistance:     {pencil} ({H_gpa:.2f} GPa)  {'PASS' if compliance['Hardness'] else 'FAIL'}
Thermal resistance:     {R_th:.2f} uK.m2/W
Max operating temp:     {SUBSTRATE_DB[material_key]['max_temp']}C   {'PASS' if compliance['Temperature'] else 'FAIL'}
Material cost:          {fmt_currency(cost_m2)}/m2
Cost per tray (500cm2): {fmt_currency(cost_m2 * 0.05)}

OVERALL {standard_key}: {'COMPLIANT' if compliance['Overall'] else 'NOT COMPLIANT'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STANDARDS COMPLIANCE SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        for s_name, s_vals in COMPLIANCE_STANDARDS.items():
            c = check_compliance(R_surface, mvtr, pencil, s_name, material_key)
            report += f"{'PASS' if c['Overall'] else 'FAIL'}  {s_name}\n"

        report += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
METHODOLOGY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ESD model:    Percolation theory (power law, t=1.3, phi_c={get_phi_c(material_key)} wt% for {material_key})
MVTR model:   Nielsen tortuous path (tau = 1 + alpha*phi/2)
Hardness:     Halpin-Tsai composite mechanics
Thermal:      Fourier conduction (R = t/k)
Percolation threshold source: see Calibrate & Compare tab for full citation
Academic reference: M.Sc. Nanoscience, University of Glasgow (2025)
Tool:         NanoSeal Sim v2.0 | nanoseal-sim.streamlit.app
"""
        st.code(report, language=None)
        st.download_button("📥 Download report (.txt)",
                           data=report,
                           file_name=f"nanoseal_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                           mime="text/plain")

        if PDF_AVAILABLE:
            pdf_bytes = build_pdf_report(report, material_key, standard_key, compliance["Overall"])
            st.download_button("📄 Download report (.pdf) — for customers/suppliers",
                               data=pdf_bytes,
                               file_name=f"nanoseal_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                               mime="application/pdf")
        else:
            st.caption("PDF export requires the `fpdf2` package — add it to requirements.txt to enable.")

    # TAB 8 — CALIBRATE & COMPARE
    with tab8:
        st.markdown("#### 🎯 Material-specific percolation thresholds")
        st.markdown("Every material now uses its own literature-sourced percolation threshold — "
                    "thermoplastics (HIPS, PP, PC etc.) percolate at 1–3 wt%, much higher than the "
                    "epoxy value (0.18 wt%) this tool used before. Sources are cited below.")

        phi_rows = []
        for mat_name in SUBSTRATE_DB:
            if mat_name in MATERIAL_PHI_C:
                info = MATERIAL_PHI_C[mat_name]
                override_key = f"calibrated_phi_c__{mat_name}"
                current_val = st.session_state.get(override_key, info["phi_c"])
                is_overridden = override_key in st.session_state
                cite_short = "Your lab data" if is_overridden else CITATIONS[info["cite"]]["authors"]
                phi_rows.append({
                    "Material": mat_name,
                    "Percolation threshold (wt%)": f"{current_val}" + (" 🔧" if is_overridden else ""),
                    "Basis": "measured" if is_overridden else info["basis"],
                    "Reference": cite_short
                })
        st.dataframe(pd.DataFrame(phi_rows), use_container_width=True, hide_index=True)
        st.caption("🔧 = calibrated with your own measured data, overriding the literature value")

        with st.expander("📚 Full references — click to see every citation in detail"):
            st.markdown(f"**Epoxy baseline (used only as fallback):**")
            c = CITATIONS["epoxy_mohan"]
            st.markdown(f"*{c['authors']} ({c['year']}).* **{c['title']}.** {c['journal']}. "
                       f"Finding: {c['finding']}. [Source]({c['url']})")
            st.divider()
            for key, c in CITATIONS.items():
                if key == "epoxy_mohan":
                    continue
                st.markdown(f"*{c['authors']} ({c['year']}).* **{c['title']}.** {c['journal']}. "
                           f"Finding: {c['finding']}. [Source]({c['url']})")
                st.markdown("")

        st.divider()
        st.markdown("#### Calibrate one material against your own lab data")
        st.markdown(f"Currently selected material: **{material_key}**  |  "
                    f"Literature default: **{MATERIAL_PHI_C.get(material_key, {}).get('phi_c', DEFAULT_PHI_C_EPOXY)} wt%**")

        cal1, cal2 = st.columns(2)
        with cal1:
            measured_cnt = st.number_input(f"Your measured CNT wt% at compliance threshold for {material_key}",
                                           min_value=0.05, max_value=5.0,
                                           value=float(get_phi_c(material_key)), step=0.05,
                                           help="The lowest CNT loading where your real coated sample first met the ESD spec")
        with cal2:
            st.write("")
            st.write("")
            if st.button("✅ Apply calibration to this material", type="primary"):
                st.session_state[f"calibrated_phi_c__{material_key}"] = measured_cnt
                st.success(f"{material_key} calibrated to {measured_cnt} wt% from your own data.")
                st.rerun()

        if f"calibrated_phi_c__{material_key}" in st.session_state:
            if st.button(f"↺ Reset {material_key} to literature value"):
                del st.session_state[f"calibrated_phi_c__{material_key}"]
                st.rerun()

        st.divider()

        st.markdown("#### ⚖️ Compare against an imported material")
        st.markdown("Paste a competitor or supplier spec sheet's numbers to see how your NanoSeal "
                    "formulation compares — useful for supplier negotiations or customer proposals.")

        comp1, comp2, comp3 = st.columns(3)
        with comp1:
            competitor_name = st.text_input("Competitor / import name", value="Imported (Japan)")
        with comp2:
            competitor_esd = st.number_input("Their ESD resistance (Ω/sq)",
                                             min_value=1e2, max_value=1e14, value=1e8, format="%.2e")
        with comp3:
            competitor_price = st.number_input(f"Their price ({currency.split()[0]}/m²)",
                                                min_value=0.0, value=0.45, step=0.01, format="%.4f")

        your_price = cost_m2 if currency == "GBP £" else cost_m2  # cost_m2 always computed in GBP base
        your_price_display = fmt_currency(cost_m2)

        comparison_rows = [
            ["Property", "Your NanoSeal formulation", competitor_name],
            ["ESD Resistance (Ω/sq)", f"{R_surface:.2e}", f"{competitor_esd:.2e}"],
            ["JEDEC Compliant", "✅ Yes" if compliance["ESD"] else "❌ No",
             "✅ Yes" if std["esd_min"] <= competitor_esd <= std["esd_max"] else "❌ No"],
            ["Price per m²", your_price_display, f"{currency.split()[0]}{competitor_price:.4f}"],
            ["Origin", "UK-manufactured (Glasgow)", "Imported"],
            ["Lead time", "2–5 days (domestic)", "6–14 weeks (typical import)"],
        ]
        df_comp = pd.DataFrame(comparison_rows[1:], columns=comparison_rows[0])
        st.dataframe(df_comp, use_container_width=True, hide_index=True)

        gbp_competitor = competitor_price if currency == "GBP £" else competitor_price
        price_diff_pct = ((cost_m2 - gbp_competitor) / gbp_competitor * 100) if gbp_competitor > 0 else 0
        if price_diff_pct < 0:
            st.success(f"Your formulation is **{abs(price_diff_pct):.1f}% cheaper** than {competitor_name}, "
                      f"with a {'6–14 week' if 'import' in competitor_name.lower() else 'comparable'} "
                      f"lead-time advantage from domestic UK manufacturing.")
        elif price_diff_pct > 0:
            st.warning(f"Your formulation is currently **{price_diff_pct:.1f}% more expensive** than "
                      f"{competitor_name} — try the Auto-Optimiser tab to find a cheaper compliant mix.")
        else:
            st.info("Prices are equal — differentiate on lead time and JEDEC compliance instead.")

    # TAB 9 — SCALE-UP CALCULATOR
    with tab9:
        st.markdown("#### 🏭 Production Scale-Up Calculator")
        st.markdown("Convert your formulation into real monthly raw material quantities — "
                    "and check against typical supplier minimum order quantities (MOQs).")

        su1, su2 = st.columns(2)
        with su1:
            monthly_units = st.number_input("Monthly production volume (units/trays)",
                                            min_value=100, max_value=1000000, value=3000, step=100)
        with su2:
            unit_area_cm2 = st.number_input("Area per unit (cm²)", min_value=10, max_value=5000,
                                            value=500, step=10,
                                            help="Approx. surface area of one tray/unit being coated")

        total_m2_month = monthly_units * (unit_area_cm2 / 10000)
        cnt_kg_month = (coat_wt * (cnt_wt/100) / 1000) * total_m2_month
        clay_kg_month = (coat_wt * (clay_wt/100) / 1000) * total_m2_month
        sio2_kg_month = (coat_wt * (sio2_wt/100) / 1000) * total_m2_month
        total_cost_month = cost_m2 * total_m2_month

        st.divider()
        sc1, sc2, sc3, sc4 = st.columns(4)
        with sc1:
            st.metric("Total area/month", f"{total_m2_month:.1f} m²")
        with sc2:
            st.metric("CNT needed/month", f"{cnt_kg_month*1000:.1f} g")
        with sc3:
            st.metric("Nano-clay needed/month", f"{clay_kg_month*1000:.1f} g")
        with sc4:
            st.metric("Total material cost/month", fmt_currency(total_cost_month))

        st.divider()
        st.markdown("#### Supplier MOQ check")
        moq_rows = [
            ["Raw material", "Your monthly need", "Typical small-batch MOQ", "Status"],
            ["MWCNT dispersion (e.g. Thomas Swan)", f"{cnt_kg_month*1000:.1f} g",
             "500 ml (~5-10 g equiv.)",
             "✅ Within range" if cnt_kg_month*1000 <= 500 else "⚠️ May need bulk order — contact supplier"],
            ["Nano-clay (e.g. Imerys Cloisite)", f"{clay_kg_month*1000:.1f} g",
             "1 kg minimum",
             "✅ Within range" if clay_kg_month <= 1 else "⚠️ Exceeds typical small-batch MOQ — good, justifies bulk pricing"],
            ["SiO2 colloidal (e.g. Evonik)", f"{sio2_kg_month*1000:.1f} g",
             "500 g minimum",
             "✅ Within range" if sio2_kg_month*1000 <= 500 else "⚠️ May need bulk order"],
        ]
        df_moq = pd.DataFrame(moq_rows[1:], columns=moq_rows[0])
        st.dataframe(df_moq, use_container_width=True, hide_index=True)
        st.caption("MOQ figures are typical small-batch estimates from the Raw Materials & Supply Chain document — confirm exact terms directly with each supplier.")

        st.divider()
        st.markdown("#### Annual projection")
        annual_cost = total_cost_month * 12
        st.metric("Projected annual material cost", fmt_currency(annual_cost))

    # TAB 10 — COMPLIANCE & FOOTPRINT
    with tab10:
        st.markdown("#### ✅ Regulatory Compliance (REACH / RoHS)")
        st.markdown("Status of each raw material component used in your formulation.")

        reg_rows = []
        for comp_name, info in REGULATORY_DB.items():
            reg_rows.append({
                "Component": comp_name,
                "REACH": "✅ Compliant" if info["REACH"] else "❌ Not compliant",
                "RoHS": "✅ Compliant" if info["RoHS"] else "❌ Not compliant",
                "Note": info["note"]
            })
        st.dataframe(pd.DataFrame(reg_rows), use_container_width=True, hide_index=True)
        st.caption("Regulatory status shown reflects commonly available REACH/RoHS-compliant grades of each material class. "
                  "Always confirm the specific Certificate of Analysis (CoA) with your actual supplier batch.")

        st.divider()
        st.markdown("#### 🌱 Environmental Footprint Estimate")
        st.markdown("Simplified transport-emissions comparison — domestic UK manufacturing vs. imported alternatives. "
                    "This is an illustrative estimate based on typical freight emission factors, **not a certified LCA**.")

        fp_weight = st.number_input("Shipment weight for comparison (kg)", min_value=0.1, max_value=10000.0,
                                    value=max(cnt_kg_month + clay_kg_month + sio2_kg_month, 1.0), step=0.5,
                                    help="Defaults to your monthly raw material weight from the Scale-Up tab")

        dom_co2, sea_co2, air_co2 = estimate_co2_footprint(weight_kg=fp_weight)

        fp1, fp2, fp3 = st.columns(3)
        with fp1:
            st.metric("Domestic (UK road)", f"{dom_co2:.2f} kg CO₂e")
        with fp2:
            st.metric("Imported (sea freight)", f"{sea_co2:.2f} kg CO₂e",
                      delta=f"{sea_co2/dom_co2:.1f}× higher" if dom_co2 > 0 else None,
                      delta_color="inverse")
        with fp3:
            st.metric("Imported (air freight)", f"{air_co2:.2f} kg CO₂e",
                      delta=f"{air_co2/dom_co2:.1f}× higher" if dom_co2 > 0 else None,
                      delta_color="inverse")

        fig_fp = go.Figure(go.Bar(
            x=["Domestic (UK road)", "Import (sea freight)", "Import (air freight)"],
            y=[dom_co2, sea_co2, air_co2],
            marker_color=["#1B5E20", "#E65100", "#B71C1C"]
        ))
        fig_fp.update_layout(title="Transport CO₂e Comparison", yaxis_title="kg CO₂e",
                            height=320, template="plotly_white")
        st.plotly_chart(fig_fp, use_container_width=True)
        st.caption("Emission factors: domestic UK road ~0.012 kg CO₂e/kg (150 mile avg), sea freight Asia-UK ~0.045 kg CO₂e/kg, "
                  "air freight Asia-UK ~0.850 kg CO₂e/kg. Simplified DEFRA-style factors for illustration.")

    # TAB 11 — SAVED FORMULATIONS
    with tab11:
        st.markdown("#### 💾 Save & Compare Formulations")
        st.markdown("Save your current formulation to compare multiple candidates side by side — "
                    "useful when presenting options to a customer.")

        if "saved_formulations" not in st.session_state:
            st.session_state["saved_formulations"] = []

        sf1, sf2 = st.columns([3, 1])
        with sf1:
            formulation_label = st.text_input("Label for this formulation", value=f"Option {len(st.session_state['saved_formulations'])+1}")
        with sf2:
            st.write("")
            st.write("")
            if st.button("💾 Save current formulation", type="primary"):
                st.session_state["saved_formulations"].append({
                    "Label": formulation_label,
                    "Material": material_key,
                    "CNT wt%": cnt_wt,
                    "Clay wt%": clay_wt,
                    "SiO2 wt%": sio2_wt,
                    "Thickness (nm)": thickness_nm,
                    "ESD (Ω/sq)": f"{R_surface:.2e}",
                    "MVTR (g/m²/day)": f"{mvtr:.4f}",
                    "Hardness": pencil,
                    "Cost/m²": fmt_currency(cost_m2),
                    "Compliant": "✅ Yes" if compliance["Overall"] else "❌ No",
                })
                st.success(f"Saved as '{formulation_label}'")
                st.rerun()

        st.divider()

        if st.session_state["saved_formulations"]:
            df_saved = pd.DataFrame(st.session_state["saved_formulations"])
            st.dataframe(df_saved, use_container_width=True, hide_index=True)

            del_col1, del_col2 = st.columns([3, 1])
            with del_col1:
                to_delete = st.selectbox("Remove a saved formulation",
                                         ["—"] + [f["Label"] for f in st.session_state["saved_formulations"]])
            with del_col2:
                st.write("")
                st.write("")
                if st.button("🗑️ Remove") and to_delete != "—":
                    st.session_state["saved_formulations"] = [
                        f for f in st.session_state["saved_formulations"] if f["Label"] != to_delete
                    ]
                    st.rerun()

            if st.button("🧹 Clear all saved formulations"):
                st.session_state["saved_formulations"] = []
                st.rerun()
        else:
            st.info("No formulations saved yet — adjust the sliders, then click 'Save current formulation' above.")

if __name__ == "__main__":
    main()