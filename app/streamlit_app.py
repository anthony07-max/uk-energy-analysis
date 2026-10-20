from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

P = Path(__file__).resolve().parents[1] / "data" / "processed"
st.set_page_config(page_title="UK energy", layout="wide")
st.title("UK energy: prices, generation and household use")
st.caption("Ofgem, ONS, NESO and DESNZ open data. By Anthony Adusei-Poku (@anthony07-max)")
t1, t2, t3, t4 = st.tabs(["Price cap", "Consumer prices", "Generation mix", "Household use by area"])
with t1:
    of = pd.read_csv(P / "ofgem_cap_components.csv")
    fuel = st.selectbox("Fuel", of.fuel.unique().tolist(), index=3)
    d = of[(of.fuel == fuel) & ~of.component.isin(["Total_GB average", "Total inc VAT"])]
    st.plotly_chart(px.bar(d, x="period_start", y="gbp_per_year", color="component", title="Cap components, £/year (excl. VAT)"), use_container_width=True)
with t2:
    cpi = pd.read_csv(P / "ons_cpi_energy.csv")
    st.plotly_chart(px.line(cpi, x="date", y=["cpi_electricity", "cpi_gas", "cpi_all_items"], title="CPI index (2015 = 100)"), use_container_width=True)
with t3:
    mix = pd.read_csv(P / "neso_annual_mix.csv")
    st.plotly_chart(px.area(mix, x="year", y=["COAL", "GAS", "NUCLEAR", "WIND_TOTAL", "SOLAR", "BIOMASS", "IMPORTS", "HYDRO"], title="% of GB generation"), use_container_width=True)
    st.plotly_chart(px.line(mix, x="year", y="carbon_intensity", markers=True, title="Carbon intensity (gCO2/kWh)"), use_container_width=True)
with t4:
    de = pd.read_csv(P / "desnz_domestic_electricity.csv")
    de = de[de.code.astype(str).str.match(r"^[ESW]0[6789]")]
    las = sorted(de.local_authority.dropna().unique())
    pick = st.multiselect("Local authorities", las, default=[x for x in ["Newham", "Tower Hamlets", "Westminster"] if x in las])
    st.plotly_chart(px.line(de[de.local_authority.isin(pick)], x="year", y="mean_domestic_kwh", color="local_authority", markers=True), use_container_width=True)
