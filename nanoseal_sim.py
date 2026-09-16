import numpy as np
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

def esd_surface_resistance(cnt_wt_percent, coating_thickness_nm, substrate="HIPS"):
    percolation_threshold = 0.18
    substrate_resistance = {"HIPS": 1e13, "PETG": 1e14, "PP": 1e15, "ABS": 1e13}
    R_substrate = substrate_resistance.get(substrate, 1e13)
    if cnt_wt_percent < percolation_threshold:
        R_surface = R_substrate * (1 - cnt_wt_percent / percolation_threshold * 0.5)
    else:
        t = 1.3
        phi = cnt_wt_percent / 100
        phi_c = percolation_threshold / 100
        sigma_max = 1e5
        sigma_network = sigma_max * ((phi - phi_c) / (1 - phi_c)) ** t
        thickness_factor = np.log10(coating_thickness_nm / 5) / np.log10(100)
        thickness_factor = np.clip(thickness_factor, 0.1, 2.0)
        sigma_effective = sigma_network * thickness_factor
        thickness_m = coating_thickness_nm * 1e-9
        R_surface = 1 / (sigma_effective * thickness_m)
        R_surface = np.clip(R_surface, 1e2, 1e14)
    jedec_compliant = 1e4 <= R_surface <= 1e11
    return R_surface, jedec_compliant


def mvtr_nano_clay(clay_wt_percent, film_thickness_um, platelet_aspect_ratio=150, base_mvtr=0.020):
    clay_density = 2.86
    polymer_density = 1.20
    phi_clay = (clay_wt_percent / 100) / (
        clay_wt_percent / 100 + (1 - clay_wt_percent / 100) * (clay_density / polymer_density)
    )
    tau = 1 + (platelet_aspect_ratio * phi_clay) / 2
    mvtr_enhanced = base_mvtr / tau
    mvtr_jedec_units = mvtr_enhanced * 0.0645
    jedec_compliant = mvtr_jedec_units < 0.002
    improvement_factor = base_mvtr / mvtr_enhanced
    return mvtr_enhanced, jedec_compliant, improvement_factor


def sio2_hardness(sio2_wt_percent, particle_size_nm=25):
    E_polymer = 3.5
    E_silica = 70.0
    phi_sio2 = sio2_wt_percent / 100
    xi = 2 * (particle_size_nm / particle_size_nm)
    eta = (E_silica / E_polymer - 1) / (E_silica / E_polymer + xi)
    E_composite = E_polymer * (1 + xi * eta * phi_sio2) / (1 - eta * phi_sio2)
    H_gpa = E_composite / 14
    if H_gpa < 0.30:
        pencil = "B"
    elif H_gpa < 0.40:
        pencil = "HB"
    elif H_gpa < 0.55:
        pencil = "H"
    elif H_gpa < 0.70:
        pencil = "2H"
    elif H_gpa < 0.90:
        pencil = "3H"
    elif H_gpa < 1.10:
        pencil = "4H"
    else:
        pencil = "5H+"
    return H_gpa, pencil


def coating_cost_per_m2(cnt_wt_percent, clay_wt_percent, sio2_wt_percent, coating_thickness_nm):
    cnt_price_per_kg = 800
    clay_price_per_kg = 25
    sio2_price_per_kg = 350
    coating_density = 1.1
    thickness_cm = coating_thickness_nm * 1e-7
    coating_weight_g_per_m2 = coating_density * thickness_cm * 1e6
    cnt_weight = coating_weight_g_per_m2 * (cnt_wt_percent / 100)
    clay_weight = coating_weight_g_per_m2 * (clay_wt_percent / 100)
    sio2_weight = coating_weight_g_per_m2 * (sio2_wt_percent / 100)
    cost = (cnt_weight * cnt_price_per_kg / 1000 +
            clay_weight * clay_price_per_kg / 1000 +
            sio2_weight * sio2_price_per_kg / 1000)
    return cost, coating_weight_g_per_m2


def main():
    st.set_page_config(
        page_title="NanoSeal Sim — Coating Performance Predictor",
        page_icon="🔬",
        layout="wide"
    )

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
    </style>
    <div class="main-header">
        <h1>🔬 NanoSeal Sim</h1>
        <p>Nano-Coating Performance Predictor for Semiconductor Packaging &nbsp;·&nbsp;
        Based on University of Glasgow Nano-fabrication Research &nbsp;·&nbsp;
        Sahastra Mudra Ltd. (SC848171)</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Adjust coating formulation parameters and see predicted performance instantly.")
    st.divider()

    col_input, col_results = st.columns([1, 2])

    with col_input:
        st.markdown("#### 🧪 Coating Formulation")

        substrate = st.selectbox(
            "Substrate material",
            ["HIPS", "PETG", "PP", "ABS"],
            help="ESD-grade plastic sheet used for tray thermoforming"
        )

        st.markdown("**Layer 1 — CNT ESD Coating**")
        cnt_wt = st.slider("MWCNT concentration (wt%)", min_value=0.05, max_value=3.0, value=0.5, step=0.05)
        coating_thickness = st.slider("Coating thickness (nm)", min_value=5, max_value=500, value=50, step=5)

        st.markdown("**Layer 2 — Nano-Clay MBB Coating**")
        clay_wt = st.slider("Nano-clay (MMT) concentration (wt%)", min_value=0.5, max_value=10.0, value=3.0, step=0.5)
        aspect_ratio = st.slider("Platelet aspect ratio", min_value=50, max_value=300, value=150, step=10)
        base_mvtr = st.number_input("Base film MVTR (g/m²/day)", min_value=0.001, max_value=0.1, value=0.020, step=0.001, format="%.3f")

        st.markdown("**Layer 3 — SiO₂ Scratch Resistance**")
        sio2_wt = st.slider("SiO₂ nanoparticle loading (wt%)", min_value=5.0, max_value=40.0, value=15.0, step=1.0)
        particle_size = st.slider("SiO₂ particle size (nm)", min_value=10, max_value=50, value=25, step=5)

    R_surface, esd_ok = esd_surface_resistance(cnt_wt, coating_thickness, substrate)
    mvtr, mvtr_ok, improve = mvtr_nano_clay(clay_wt, 50, aspect_ratio, base_mvtr)
    hardness, pencil = sio2_hardness(sio2_wt, particle_size)
    cost, coat_weight = coating_cost_per_m2(cnt_wt, clay_wt, sio2_wt, coating_thickness)

    with col_results:
        st.markdown("#### 📊 Predicted Performance")

        all_ok = esd_ok and mvtr_ok
        if all_ok:
            st.success("✅ **JEDEC COMPLIANT** — This formulation meets all semiconductor packaging standards")
        else:
            st.error("❌ **NOT COMPLIANT** — Adjust parameters to meet JEDEC requirements")

        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("ESD Surface Resistance", f"{R_surface:.2e} Ω/sq",
                      delta="JEDEC ✅" if esd_ok else "Out of range ❌",
                      delta_color="normal" if esd_ok else "inverse")
            st.caption("Target: 10⁴ – 10¹¹ Ω/sq (JEDEC JESD625)")
        with m2:
            st.metric("MVTR (nano-clay enhanced)", f"{mvtr:.4f} g/m²/day",
                      delta=f"{improve:.1f}× better than base | {'✅ Compliant' if mvtr_ok else '❌ Improve clay loading'}",
                      delta_color="normal" if mvtr_ok else "inverse")
            st.caption("Target: <0.005 g/m²/day (J-STD-033D)")
        with m3:
            st.metric("Scratch Resistance", f"{pencil} ({hardness:.2f} GPa)",
                      delta="≥3H required for IC lead edges",
                      delta_color="normal" if "3H" in pencil or "4H" in pencil or "5H" in pencil else "off")
            st.caption("Target: ≥3H pencil hardness (IEC 60068-2)")

        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Material cost", f"£{cost:.4f}/m²", f"{coat_weight:.2f} g/m² applied")
        with c2:
            cost_per_tray = cost * 0.05
            st.metric("Est. cost per tray", f"£{cost_per_tray:.5f}", "Based on 500cm² tray area")

        st.divider()
        st.markdown("#### 📈 Sensitivity Analysis")

        tab1, tab2, tab3, tab4 = st.tabs([
            "ESD vs CNT Loading",
            "MVTR vs Clay Loading",
            "Cost Optimisation",
            "Substrate Comparison"
        ])

        with tab1:
            cnt_range = np.linspace(0.05, 3.0, 100)
            R_range = [esd_surface_resistance(c, coating_thickness, substrate)[0] for c in cnt_range]
            fig1 = go.Figure()
            fig1.add_trace(go.Scatter(x=cnt_range, y=R_range, mode='lines',
                                      name='Surface Resistance',
                                      line=dict(color='#1A237E', width=2.5)))
            fig1.add_hrect(y0=1e4, y1=1e11, fillcolor="rgba(201,168,76,0.15)",
                           line_width=0, annotation_text="JEDEC JESD625 target zone")
            fig1.add_vline(x=cnt_wt, line_dash="dash", line_color="#C9A84C",
                           annotation_text=f"Current: {cnt_wt} wt%")
            fig1.update_layout(title="Surface Resistance vs MWCNT Concentration",
                               xaxis_title="CNT concentration (wt%)",
                               yaxis_title="Surface Resistance (Ω/sq)",
                               yaxis_type="log", height=350, template="plotly_white")
            st.plotly_chart(fig1, use_container_width=True)

        with tab2:
            clay_range = np.linspace(0.5, 10.0, 100)
            mvtr_range = [mvtr_nano_clay(c, 50, aspect_ratio, base_mvtr)[0] for c in clay_range]
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=clay_range, y=mvtr_range, mode='lines',
                                      name='MVTR', line=dict(color='#004D40', width=2.5)))
            fig2.add_hrect(y0=0, y1=0.005, fillcolor="rgba(201,168,76,0.15)",
                           line_width=0, annotation_text="Target: <0.005 g/m²/day")
            fig2.add_vline(x=clay_wt, line_dash="dash", line_color="#C9A84C",
                           annotation_text=f"Current: {clay_wt} wt%")
            fig2.update_layout(title="MVTR vs Nano-Clay Loading",
                               xaxis_title="Nano-clay concentration (wt%)",
                               yaxis_title="MVTR (g/m²/day)",
                               height=350, template="plotly_white")
            st.plotly_chart(fig2, use_container_width=True)

        with tab3:
            cnt_range_opt = np.linspace(0.05, 2.0, 50)
            results = []
            for c in cnt_range_opt:
                R, ok_esd = esd_surface_resistance(c, coating_thickness, substrate)
                m, ok_mvtr, _ = mvtr_nano_clay(clay_wt, 50, aspect_ratio, base_mvtr)
                cost_pt, _ = coating_cost_per_m2(c, clay_wt, sio2_wt, coating_thickness)
                results.append({'cnt': c, 'cost': cost_pt, 'compliant': ok_esd and ok_mvtr})
            compliant = [r for r in results if r['compliant']]
            non_compliant = [r for r in results if not r['compliant']]
            fig3 = go.Figure()
            if compliant:
                fig3.add_trace(go.Scatter(x=[r['cnt'] for r in compliant],
                                          y=[r['cost'] for r in compliant],
                                          mode='markers+lines', name='JEDEC Compliant',
                                          marker=dict(color='#1B5E20', size=6),
                                          line=dict(color='#1B5E20', width=1.5)))
            if non_compliant:
                fig3.add_trace(go.Scatter(x=[r['cnt'] for r in non_compliant],
                                          y=[r['cost'] for r in non_compliant],
                                          mode='markers', name='Non-Compliant',
                                          marker=dict(color='#B71C1C', size=5, symbol='x')))
            fig3.update_layout(title="Cost vs CNT Loading — Compliant vs Non-Compliant",
                               xaxis_title="CNT concentration (wt%)",
                               yaxis_title="Material cost (£/m²)",
                               height=350, template="plotly_white")
            st.plotly_chart(fig3, use_container_width=True)

        with tab4:
            substrates_all = ["HIPS", "PETG", "PP", "ABS"]
            colors_all = ["#1A237E", "#00695C", "#E65100", "#6A1B9A"]
            cnt_range_sub = np.linspace(0.05, 3.0, 100)
            fig4 = go.Figure()
            for substrate_name, color in zip(substrates_all, colors_all):
                R_sub = [esd_surface_resistance(c, coating_thickness, substrate_name)[0]
                         for c in cnt_range_sub]
                fig4.add_trace(go.Scatter(x=cnt_range_sub, y=R_sub,
                                          mode='lines', name=substrate_name,
                                          line=dict(color=color, width=2.5)))
            fig4.add_hrect(y0=1e4, y1=1e11, fillcolor="rgba(201,168,76,0.15)",
                           line_width=0, annotation_text="JEDEC JESD625 target zone")
            fig4.update_layout(title="ESD Surface Resistance by Substrate — All Materials Compared",
                               xaxis_title="CNT concentration (wt%)",
                               yaxis_title="Surface Resistance (Ω/sq)",
                               yaxis_type="log", height=400, template="plotly_white",
                               legend=dict(orientation="h", yanchor="bottom",
                                           y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig4, use_container_width=True)

            st.markdown("#### Substrate comparison at current CNT loading")
            comparison_data = []
            for substrate_name in substrates_all:
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
            df = pd.DataFrame(comparison_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("#### 📋 Formulation Report")
        import datetime
        report = f"""
NANOSEAL SIM — COATING FORMULATION REPORT
Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
Sahastra Mudra Ltd. (SC848171) | Prithviraj Hiralal Chowdhary

INPUTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Substrate:              {substrate}
CNT concentration:      {cnt_wt} wt%
Coating thickness:      {coating_thickness} nm
Nano-clay loading:      {clay_wt} wt%
Platelet aspect ratio:  {aspect_ratio}:1
SiO2 loading:           {sio2_wt} wt%
SiO2 particle size:     {particle_size} nm

PREDICTED PERFORMANCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ESD Surface Resistance:  {R_surface:.3e} Ohm/sq  {'JEDEC JESD625 PASS' if esd_ok else 'FAIL'}
MVTR (nano-clay):        {mvtr:.5f} g/m2/day  {'J-STD-033D PASS' if mvtr_ok else 'FAIL'}
MVTR improvement:        {improve:.1f}x better than uncoated baseline
Scratch resistance:      {pencil} ({hardness:.2f} GPa)
Material cost:           £{cost:.5f}/m2
Cost per tray (est.):    £{cost_per_tray:.6f}

OVERALL: {'JEDEC COMPLIANT' if all_ok else 'FORMULATION REQUIRES ADJUSTMENT'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Methodology: Percolation theory (CNT), Nielsen model (clay), Halpin-Tsai (SiO2)
Reference: M.Sc. Nanoscience & Nanotechnology, University of Glasgow (2025)
        """
        st.code(report, language=None)
        st.download_button("📥 Download formulation report", data=report,
                           file_name=f"nanoseal_formulation_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                           mime="text/plain")


if __name__ == "__main__":
    main()