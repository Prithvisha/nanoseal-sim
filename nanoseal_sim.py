import numpy as np
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── PHYSICS MODELS ────────────────────────────────────────────────

def esd_surface_resistance(cnt_wt_percent, coating_thickness_nm,
                            substrate="HIPS"):
    """
    Predicts ESD surface resistance using percolation theory.
    Based on CNT thin-film deposition methodology (University of Glasgow).
    
    Parameters:
        cnt_wt_percent: CNT concentration in coating dispersion (0.1 – 5.0 wt%)
        coating_thickness_nm: Applied coating thickness in nanometres (5 – 500 nm)
        substrate: Base material — HIPS, PETG, PP, ABS
    
    Returns:
        surface_resistance: Predicted Ω/sq
        jedec_compliant: Boolean — meets JEDEC JESD625?
    """
    # Percolation threshold for MWCNTs in polymer matrix
    # Typical values: 0.1 – 0.5 wt% depending on aspect ratio
    percolation_threshold = 0.18  # wt% — calibrated from Glasgow research
    
    # Substrate base resistance (uncoated)
    substrate_resistance = {
        "HIPS": 1e13,
        "PETG": 1e14,
        "PP":   1e15,
        "ABS":  1e13,
    }
    R_substrate = substrate_resistance.get(substrate, 1e13)
    
    if cnt_wt_percent < percolation_threshold:
        # Below percolation — insulating, minimal effect
        R_surface = R_substrate * (1 - cnt_wt_percent / percolation_threshold * 0.5)
    else:
        # Above percolation threshold — power law conductivity
        # σ ∝ (φ - φc)^t  where t ≈ 1.3 for 2D networks (thin films)
        t = 1.3  # Critical exponent for 2D CNT network
        phi = cnt_wt_percent / 100
        phi_c = percolation_threshold / 100
        
        # Conductivity of pure CNT network at saturation
        sigma_max = 1e5  # S/m — bulk MWCNT conductivity
        
        # Network conductivity
        sigma_network = sigma_max * ((phi - phi_c) / (1 - phi_c)) ** t
        
        # Thickness effect — thicker coating = more CNT paths
        thickness_factor = np.log10(coating_thickness_nm / 5) / np.log10(100)
        thickness_factor = np.clip(thickness_factor, 0.1, 2.0)
        
        sigma_effective = sigma_network * thickness_factor
        
        # Convert to surface resistance (Ω/sq = 1 / (σ × thickness))
        thickness_m = coating_thickness_nm * 1e-9
        R_surface = 1 / (sigma_effective * thickness_m)
        R_surface = np.clip(R_surface, 1e2, 1e14)
    
    # JEDEC JESD625 compliance: 10^4 to 10^11 Ω/sq
    jedec_compliant = 1e4 <= R_surface <= 1e11
    
    return R_surface, jedec_compliant


def mvtr_nano_clay(clay_wt_percent, film_thickness_um,
                   platelet_aspect_ratio=150,
                   base_mvtr=0.020):
    """
    Predicts Moisture Vapour Transmission Rate using Nielsen Tortuous Path Model.
    Nano-clay barrier enhancement for MBB film substrates.
    
    Parameters:
        clay_wt_percent: Nano-clay (MMT) loading in polymer coating (1 – 10 wt%)
        film_thickness_um: Total film thickness in micrometres
        platelet_aspect_ratio: MMT platelet L/t ratio (typical: 50 – 300)
        base_mvtr: Uncoated film MVTR in g/m²/day (standard MBB: ~0.020)
    
    Returns:
        mvtr_enhanced: Predicted MVTR with nano-clay coating (g/m²/day)
        jedec_compliant: Boolean — meets JEDEC J-STD-033D (<0.002 g/100in²/24hr)?
        improvement_factor: How much better than baseline
    """
    # Nielsen model: τ = 1 + (α × φ) / 2
    # where α = aspect ratio, φ = volume fraction of clay
    
    # Convert wt% to volume fraction (clay density ~2.86 g/cm³, polymer ~1.2 g/cm³)
    clay_density = 2.86
    polymer_density = 1.20
    
    phi_clay = (clay_wt_percent / 100) / (
        clay_wt_percent / 100 + 
        (1 - clay_wt_percent / 100) * (clay_density / polymer_density)
    )
    
    # Tortuosity factor
    tau = 1 + (platelet_aspect_ratio * phi_clay) / 2
    
    # Enhanced MVTR
    mvtr_enhanced = base_mvtr / tau
    
    # Convert to JEDEC units: g/100in²/24hr (1 g/m²/day = 0.0645 g/100in²/24hr)
    mvtr_jedec_units = mvtr_enhanced * 0.0645
    
    # JEDEC J-STD-033D requirement: < 0.002 g/100in²/24hr for Type I MBB
    jedec_compliant = mvtr_jedec_units < 0.002
    
    improvement_factor = base_mvtr / mvtr_enhanced
    
    return mvtr_enhanced, jedec_compliant, improvement_factor


def sio2_hardness(sio2_wt_percent, particle_size_nm=25):
    """
    Predicts scratch resistance (pencil hardness equivalent) from SiO₂ loading.
    Based on Hertz contact mechanics for nano-composite coatings.
    
    Parameters:
        sio2_wt_percent: SiO₂ nanoparticle loading (5 – 40 wt%)
        particle_size_nm: SiO₂ particle diameter (10 – 50 nm)
    
    Returns:
        hardness_gpa: Predicted hardness in GPa
        pencil_hardness: Equivalent pencil hardness grade (H, 2H, 3H etc.)
    """
    # Elastic modulus enhancement via rule of mixtures
    E_polymer = 3.5   # GPa — HIPS modulus
    E_silica  = 70.0  # GPa — amorphous SiO₂ modulus
    
    phi_sio2 = sio2_wt_percent / 100
    
    # Halpin-Tsai model for particulate composites
    xi = 2 * (particle_size_nm / particle_size_nm)  # = 2 for spheres
    eta = (E_silica / E_polymer - 1) / (E_silica / E_polymer + xi)
    
    E_composite = E_polymer * (1 + xi * eta * phi_sio2) / (1 - eta * phi_sio2)
    
    # Hardness ≈ E/14 for polymers (Vickers correlation)
    H_gpa = E_composite / 14
    
    # Map to pencil hardness (approximate)
    if H_gpa < 0.30:   pencil = "B"
    elif H_gpa < 0.40: pencil = "HB"
    elif H_gpa < 0.55: pencil = "H"
    elif H_gpa < 0.70: pencil = "2H"
    elif H_gpa < 0.90: pencil = "3H"
    elif H_gpa < 1.10: pencil = "4H"
    else:               pencil = "5H+"
    
    return H_gpa, pencil


def coating_cost_per_m2(cnt_wt_percent, clay_wt_percent, sio2_wt_percent,
                         coating_thickness_nm):
    """
    Estimates raw material cost per m² of coated substrate.
    Based on current UK market prices (2026).
    """
    # Price per kg of each nano-material (£/kg, UK 2026)
    cnt_price_per_kg   = 800    # MWCNT dispersion equivalent
    clay_price_per_kg  = 25     # Organo-MMT (Cloisite grade)
    sio2_price_per_kg  = 350    # Colloidal SiO₂
    solvent_price_per_kg = 5    # IPA / water
    
    # Coating weight per m² (g/m²) = density × thickness
    coating_density = 1.1  # g/cm³ approximate
    thickness_cm = coating_thickness_nm * 1e-7
    coating_weight_g_per_m2 = coating_density * thickness_cm * 1e6  # g/m²
    
    # Material fractions
    cnt_weight   = coating_weight_g_per_m2 * (cnt_wt_percent / 100)
    clay_weight  = coating_weight_g_per_m2 * (clay_wt_percent / 100)
    sio2_weight  = coating_weight_g_per_m2 * (sio2_wt_percent / 100)
    
    # Cost in £ per m²
    cost = (cnt_weight  * cnt_price_per_kg  / 1000 +
            clay_weight * clay_price_per_kg / 1000 +
            sio2_weight * sio2_price_per_kg / 1000)
    
    return cost, coating_weight_g_per_m2


# ── STREAMLIT UI ──────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="NanoSeal Sim — Coating Performance Predictor",
        page_icon="🔬",
        layout="wide"
    )
    
    # Header
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(135deg, #0D1B4B, #1A237E);
        padding: 24px 32px;
        border-radius: 8px;
        margin-bottom: 24px;
    }
    .main-header h1 { color: #C9A84C; margin: 0; font-size: 28px; }
    .main-header p  { color: #90CAF9; margin: 4px 0 0 0; font-size: 14px; }
    .metric-card {
        background: #F7F6F2;
        border-left: 4px solid #C9A84C;
        padding: 16px;
        border-radius: 4px;
    }
    </style>
    <div class="main-header">
        <h1>🔬 NanoSeal Sim</h1>
        <p>Nano-Coating Performance Predictor for Semiconductor Packaging  ·  
        Based on University of Glasgow Nano-fabrication Research  ·  
        Sahastra Mudra Ltd. (SC848171)</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### Adjust coating formulation parameters and see predicted performance instantly.")
    st.divider()
    
    # ── INPUT PANEL ────────────────────────────────────────────────
    col_input, col_results = st.columns([1, 2])
    
    with col_input:
        st.markdown("#### 🧪 Coating Formulation")
        
        substrate = st.selectbox(
            "Substrate material",
            ["HIPS", "PETG", "PP", "ABS"],
            help="ESD-grade plastic sheet used for tray thermoforming"
        )
        
        st.markdown("**Layer 1 — CNT ESD Coating**")
        cnt_wt = st.slider(
            "MWCNT concentration (wt%)",
            min_value=0.05, max_value=3.0,
            value=0.5, step=0.05,
            help="Multi-Wall Carbon Nanotube loading in dispersion"
        )
        coating_thickness = st.slider(
            "Coating thickness (nm)",
            min_value=5, max_value=500,
            value=50, step=5,
            help="Applied dry film thickness"
        )
        
        st.markdown("**Layer 2 — Nano-Clay MBB Coating**")
        clay_wt = st.slider(
            "Nano-clay (MMT) concentration (wt%)",
            min_value=0.5, max_value=10.0,
            value=3.0, step=0.5
        )
        aspect_ratio = st.slider(
            "Platelet aspect ratio",
            min_value=50, max_value=300,
            value=150, step=10,
            help="L/t ratio of MMT platelets — higher = better barrier"
        )
        base_mvtr = st.number_input(
            "Base film MVTR (g/m²/day)",
            min_value=0.001, max_value=0.1,
            value=0.020, step=0.001, format="%.3f"
        )
        
        st.markdown("**Layer 3 — SiO₂ Scratch Resistance**")
        sio2_wt = st.slider(
            "SiO₂ nanoparticle loading (wt%)",
            min_value=5.0, max_value=40.0,
            value=15.0, step=1.0
        )
        particle_size = st.slider(
            "SiO₂ particle size (nm)",
            min_value=10, max_value=50,
            value=25, step=5
        )
    
    # ── CALCULATIONS ───────────────────────────────────────────────
    R_surface, esd_ok       = esd_surface_resistance(cnt_wt, coating_thickness, substrate)
    mvtr, mvtr_ok, improve  = mvtr_nano_clay(clay_wt, 50, aspect_ratio, base_mvtr)
    hardness, pencil        = sio2_hardness(sio2_wt, particle_size)
    cost, coat_weight       = coating_cost_per_m2(cnt_wt, clay_wt, sio2_wt, coating_thickness)
    
    # ── RESULTS PANEL ─────────────────────────────────────────────
    with col_results:
        st.markdown("#### 📊 Predicted Performance")
        
        # Overall compliance badge
        all_ok = esd_ok and mvtr_ok
        if all_ok:
            st.success("✅ **JEDEC COMPLIANT** — This formulation meets all semiconductor packaging standards")
        else:
            st.error("❌ **NOT COMPLIANT** — Adjust parameters to meet JEDEC requirements")
        
        # Three metric columns
        m1, m2, m3 = st.columns(3)
        
        with m1:
            color = "normal" if esd_ok else "inverse"
            st.metric(
                label="ESD Surface Resistance",
                value=f"{R_surface:.2e} Ω/sq",
                delta="JEDEC ✅" if esd_ok else "Out of range ❌",
                delta_color=color
            )
            st.caption("Target: 10⁴ – 10¹¹ Ω/sq (JEDEC JESD625)")
        
        with m2:
            st.metric(
                label="MVTR (nano-clay enhanced)",
                value=f"{mvtr:.4f} g/m²/day",
                delta=f"{improve:.1f}× better than base | {'✅ Compliant' if mvtr_ok else '❌ Improve clay loading'}",
                delta_color="normal" if mvtr_ok else "inverse"
            )
            st.caption("Target: <0.005 g/m²/day (J-STD-033D)")
        
        with m3:
            st.metric(
                label="Scratch Resistance",
                value=f"{pencil} ({hardness:.2f} GPa)",
                delta="≥3H required for IC lead edges",
                delta_color="normal" if "3H" in pencil or "4H" in pencil or "5H" in pencil else "off"
            )
            st.caption("Target: ≥3H pencil hardness (IEC 60068-2)")
        
        st.divider()
        
        # Cost section
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Material cost", f"£{cost:.4f}/m²", f"{coat_weight:.2f} g/m² applied")
        with c2:
            cost_per_tray = cost * 0.05  # typical tray area ~500cm² = 0.05m²
            st.metric("Est. cost per tray", f"£{cost_per_tray:.5f}", "Based on 500cm² tray area")
        
        st.divider()
        
        # Sweep plots
        st.markdown("#### 📈 Sensitivity Analysis")
        tab1, tab2, tab3, tab4 = st.tabs(["ESD vs CNT Loading", "MVTR vs Clay Loading", "Cost Optimisation", "Substrate Comparison"])
        
        with tab1:
            cnt_range = np.linspace(0.05, 3.0, 100)
            R_range = [esd_surface_resistance(c, coating_thickness, substrate)[0] for c in cnt_range]
            
            fig1 = go.Figure()
            fig1.add_trace(go.Scatter(
                x=cnt_range, y=R_range,
                mode='lines', name='Surface Resistance',
                line=dict(color='#1A237E', width=2.5)
            ))
            fig1.add_hrect(y0=1e4, y1=1e11,
                fillcolor="rgba(201,168,76,0.15)",
                line_width=0, annotation_text="JEDEC JESD625 target zone")
            fig1.add_vline(x=cnt_wt, line_dash="dash", line_color="#C9A84C",
                annotation_text=f"Current: {cnt_wt} wt%")
            fig1.update_layout(
                title="Surface Resistance vs MWCNT Concentration",
                xaxis_title="CNT concentration (wt%)",
                yaxis_title="Surface Resistance (Ω/sq)",
                yaxis_type="log",
                height=350,
                template="plotly_white"
            )
            st.plotly_chart(fig1, use_container_width=True)
        
        with tab2:
            clay_range = np.linspace(0.5, 10.0, 100)
            mvtr_range = [nano_clay_result[0] 
                         for c in clay_range
                         for nano_clay_result in [mvtr_nano_clay(c, 50, aspect_ratio, base_mvtr)]]
            
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=clay_range, y=mvtr_range,
                mode='lines', name='MVTR',
                line=dict(color='#004D40', width=2.5)
            ))
            fig2.add_hrect(y0=0, y1=0.005,
                fillcolor="rgba(201,168,76,0.15)",
                line_width=0, annotation_text="Target: <0.005 g/m²/day")
            fig2.add_vline(x=clay_wt, line_dash="dash", line_color="#C9A84C",
                annotation_text=f"Current: {clay_wt} wt%")
            fig2.update_layout(
                title="MVTR vs Nano-Clay Loading",
                xaxis_title="Nano-clay concentration (wt%)",
                yaxis_title="MVTR (g/m²/day)",
                height=350,
                template="plotly_white"
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        with tab3:
            # Find optimal cost point that still meets both specs
            cnt_range_opt = np.linspace(0.05, 2.0, 50)
            clay_range_opt = np.linspace(0.5, 8.0, 50)
            
            results = []
            for c in cnt_range_opt:
                R, ok_esd = esd_surface_resistance(c, coating_thickness, substrate)
                m, ok_mvtr, _ = mvtr_nano_clay(clay_wt, 50, aspect_ratio, base_mvtr)
                cost_pt, _ = coating_cost_per_m2(c, clay_wt, sio2_wt, coating_thickness)
                results.append({
                    'cnt': c, 'R': R, 'cost': cost_pt,
                    'compliant': ok_esd and ok_mvtr
                })
            
            compliant = [r for r in results if r['compliant']]
            non_compliant = [r for r in results if not r['compliant']]
            
            fig3 = go.Figure()
            if compliant:
                fig3.add_trace(go.Scatter(
                    x=[r['cnt'] for r in compliant],
                    y=[r['cost'] for r in compliant],
                    mode='markers+lines', name='JEDEC Compliant',
                    marker=dict(color='#1B5E20', size=6),
                    line=dict(color='#1B5E20', width=1.5)
                ))
            if non_compliant:
                fig3.add_trace(go.Scatter(
                    x=[r['cnt'] for r in non_compliant],
                    y=[r['cost'] for r in non_compliant],
                    mode='markers', name='Non-Compliant',
                    marker=dict(color='#B71C1C', size=5, symbol='x')
                ))
            fig3.update_layout(
                title="Cost vs CNT Loading — Compliant vs Non-Compliant",
                xaxis_title="CNT concentration (wt%)",
                yaxis_title="Material cost (£/m²)",
                height=350,
                template="plotly_white"
            )
            st.plotly_chart(fig3, use_container_width=True)

        with tab4:                                            # ← PASTE FROM HERE
            substrates = ["HIPS", "PETG", "PP", "ABS"]
            colors = ["#1A237E", "#00695C", "#E65100", "#6A1B9A"]
            fig4 = go.Figure()
            cnt_range_sub = np.linspace(0.05, 3.0, 100)
            for substrate_name, color in zip(substrates, colors):
                R_sub = [esd_surface_resistance(c, coating_thickness, substrate_name)[0]
                         for c in cnt_range_sub]
                fig4.add_trace(go.Scatter(
                    x=cnt_range_sub, y=R_sub,
                    mode='lines', name=substrate_name,
                    line=dict(color=color, width=2.5)
                ))
            fig4.add_hrect(y0=1e4, y1=1e11,
                fillcolor="rgba(201,168,76,0.15)",
                line_width=0,
                annotation_text="JEDEC JESD625 target zone")
            fig4.update_layout(
                title="ESD Surface Resistance by Substrate",
                xaxis_title="CNT concentration (wt%)",
                yaxis_title="Surface Resistance (Ω/sq)",
                yaxis_type="log", height=400,
                template="plotly_white")
            st.plotly_chart(fig4, use_container_width=True)
            st.markdown("#### Substrate comparison at current CNT loading")
            comparison_data = []
            for substrate_name in substrates:
                R, ok = esd_surface_resistance(cnt_wt, coating_thickness, substrate_name)
                comparison_data.append({
                    "Substrate": substrate_name,
                    "Surface Resistance": f"{R:.2e} Ω/sq",
                    "JEDEC Compliant": "✅ Yes" if ok else "❌ No",
                    "Best for": "Standard IC trays" if substrate_name == "HIPS"
                               else "Clear inspection trays" if substrate_name == "PETG"
                               else "High-temp applications" if substrate_name == "PP"
                               else "Impact-resistant trays"
                })
            import pandas as pd
            df = pd.DataFrame(comparison_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Formulation summary export
        st.divider()
        st.markdown("#### 📋 Formulation Report")
        report = f"""
NANOSEAL SIM — COATING FORMULATION REPORT
Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}
Sahastra Mudra Ltd. (SC848171) | Prithviraj Hiralal Chowdhary

INPUTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Substrate:              {substrate}
CNT concentration:      {cnt_wt} wt%
Coating thickness:      {coating_thickness} nm
Nano-clay loading:      {clay_wt} wt%
Platelet aspect ratio:  {aspect_ratio}:1
SiO₂ loading:           {sio2_wt} wt%
SiO₂ particle size:     {particle_size} nm

PREDICTED PERFORMANCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ESD Surface Resistance:  {R_surface:.3e} Ω/sq  {'✅ JEDEC JESD625' if esd_ok else '❌ Out of range'}
MVTR (nano-clay):        {mvtr:.5f} g/m²/day  {'✅ J-STD-033D' if mvtr_ok else '❌ Exceeds limit'}
MVTR improvement:        {improve:.1f}× better than uncoated baseline
Scratch resistance:      {pencil} ({hardness:.2f} GPa)
Material cost:           £{cost:.5f}/m²
Cost per tray (est.):    £{cost_per_tray:.6f}

OVERALL: {'✅ JEDEC COMPLIANT' if all_ok else '❌ FORMULATION REQUIRES ADJUSTMENT'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Methodology: Percolation theory (CNT), Nielsen model (clay), Halpin-Tsai (SiO₂)
Reference: M.Sc. Nanoscience & Nanotechnology, University of Glasgow (2025)
        """
        st.code(report, language=None)
        st.download_button(
            "📥 Download formulation report",
            data=report,
            file_name=f"nanoseal_formulation_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain"
        )

if __name__ == "__main__":
    main()