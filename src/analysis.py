"""Price cap cost stack, consumer price inflation, generation mix decarbonisation and household electricity use."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
P, CH = ROOT / "data" / "processed", ROOT / "charts"
CH.mkdir(exist_ok=True)
COMP = {"DF": "Wholesale energy", "CM": "Capacity market", "NC": "Network costs", "PC": "Policy costs", "OC": "Operating costs",
        "SMNCC": "Smart meter costs", "EBIT": "Supplier margin (EBIT)", "HAP": "Headroom", "AA": "Adjustment allowance",
        "IC": "Industry charges", "PAAC": "Payment method adj.", "PAP": "Payment method adj.", "CO": "Operating costs",
        "DRC": "Debt-related costs", "Levelisation": "Levelisation"}

def main():
    out = {}
    # ---------- 1. Ofgem price cap ----------
    of = pd.read_csv(P / "ofgem_cap_components.csv", parse_dates=["period_start"])
    dual = of[of.fuel == "Dual fuel (implied)"]
    tot = dual[dual.component == "Total inc VAT"].set_index("period_start").gbp_per_year
    st = dual[dual.component.isin(COMP)].assign(group=lambda d: d.component.map(COMP)).pivot_table(index="period_start", columns="group", values="gbp_per_year", aggfunc="sum").fillna(0)
    main_groups = ["Wholesale energy", "Network costs", "Policy costs", "Operating costs"]
    st["Other (VAT excluded)"] = st.drop(columns=main_groups).sum(axis=1)
    st = st[main_groups + ["Other (VAT excluded)"]]
    share = st.div(st.sum(axis=1), axis=0) * 100
    out["cap_total_inc_vat"] = {str(k.date()): round(float(v)) for k, v in tot.items()}
    out["cap_peak"] = {"period": str(tot.idxmax().date()), "gbp": round(float(tot.max()))}
    out["cap_latest"] = {"period": str(tot.index.max().date()), "gbp": round(float(tot.iloc[-1]))}
    out["cap_first"] = {"period": str(tot.index.min().date()), "gbp": round(float(tot.iloc[0]))}
    out["wholesale_share"] = {str(k.date()): round(float(v), 1) for k, v in share["Wholesale energy"].items()}
    out["network_share_latest"] = round(float(share["Network costs"].iloc[-1]), 1)
    out["policy_share_latest"] = round(float(share["Policy costs"].iloc[-1]), 1)
    fig, ax = plt.subplots(figsize=(11, 5.5))
    x = np.arange(len(st)); bottom = np.zeros(len(st))
    for c, col in zip(st.columns, ["#e76f51", "#2a9d8f", "#e9c46a", "#264653", "#adb5bd"]):
        ax.bar(x, st[c], bottom=bottom, label=c, color=col); bottom += st[c].values
    ax.plot(x, tot.values, "k.-", label="Total inc VAT")
    ax.set_xticks(x, [d.strftime("%b %y") for d in st.index], rotation=60, fontsize=8)
    ax.set_ylabel("£ per year, typical dual-fuel direct debit"); ax.legend(fontsize=8)
    ax.set_title("Ofgem price cap cost stack (indicative levels at current typical consumption)")
    fig.tight_layout(); fig.savefig(CH / "01_price_cap_stack.png", dpi=150); plt.close()

    # ---------- 2. ONS CPI ----------
    cpi = pd.read_csv(P / "ons_cpi_energy.csv", parse_dates=["date"]).set_index("date")
    base = cpi.loc["2019-01-01":"2019-12-01"].mean()
    rel = cpi / base * 100
    out["cpi_vs_2019"] = {c: round(float(rel[c].iloc[-1] - 100), 1) for c in rel}
    out["cpi_latest_month"] = str(cpi.index.max().date())
    out["cpi_peak_electricity"] = {"date": str(rel.cpi_electricity.idxmax().date()), "vs_2019_pct": round(float(rel.cpi_electricity.max() - 100), 1)}
    out["cpi_peak_gas"] = {"date": str(rel.cpi_gas.idxmax().date()), "vs_2019_pct": round(float(rel.cpi_gas.max() - 100), 1)}
    fig, ax = plt.subplots(figsize=(10, 5))
    r = rel.loc["2015-01-01":]
    ax.plot(r.index, r.cpi_electricity, label="Electricity", color="#e76f51"); ax.plot(r.index, r.cpi_gas, label="Gas", color="#264653")
    ax.plot(r.index, r.cpi_all_items, label="All items (CPI)", color="grey", ls="--")
    ax.axhline(100, color="k", lw=.6); ax.set_ylabel("Index, 2019 average = 100"); ax.legend()
    ax.set_title("Consumer prices: household energy vs everything else (ONS CPI)")
    fig.tight_layout(); fig.savefig(CH / "02_cpi_energy.png", dpi=150); plt.close()

    # ---------- 3. NESO generation mix ----------
    mix = pd.read_csv(P / "neso_annual_mix.csv").set_index("year")
    full = mix.loc[:2025]
    out["mix"] = {y: {k: round(float(full.loc[y, k]), 1) for k in ["GAS", "COAL", "NUCLEAR", "WIND_TOTAL", "SOLAR", "IMPORTS", "BIOMASS", "carbon_intensity"]} for y in [2010, 2015, 2020, 2025]}
    out["mix_2026_ytd"] = {k: round(float(mix.loc[2026, k]), 1) for k in ["GAS", "COAL", "NUCLEAR", "WIND_TOTAL", "SOLAR", "carbon_intensity"]}
    fig, ax = plt.subplots(1, 2, figsize=(13, 5))
    cols = {"COAL": "#343a40", "GAS": "#e76f51", "NUCLEAR": "#9d4edd", "WIND_TOTAL": "#2a9d8f", "SOLAR": "#ffb703", "BIOMASS": "#6a994e", "IMPORTS": "#adb5bd", "HYDRO": "#219ebc"}
    full[list(cols)].plot.area(ax=ax[0], color=list(cols.values()), linewidth=0); ax[0].set_ylabel("% of GB generation"); ax[0].set_xlim(2009, 2025)
    ax[0].set_title("GB generation mix (NESO)"); ax[0].legend(fontsize=7, loc="upper left")
    ax[1].plot(mix.index, mix.carbon_intensity, "o-", color="#1d3557"); ax[1].set_ylabel("gCO₂/kWh (annual mean)"); ax[1].set_ylim(0)
    ax[1].set_title("Carbon intensity of GB electricity")
    fig.tight_layout(); fig.savefig(CH / "03_generation_mix.png", dpi=150); plt.close()

    hh = pd.read_parquet(P / "neso_halfhourly.parquet")
    recent = hh[hh.DATETIME >= "2025-01-01"].copy()
    recent["wind_band"] = pd.cut(recent.wind_share, [0, 10, 20, 30, 40, 50, 100])
    wb = recent.groupby("wind_band", observed=True).agg(carbon=("CARBON_INTENSITY", "mean"), gas=("gas_share", "mean"), n=("CARBON_INTENSITY", "size"))
    out["wind_vs_carbon_since_2025"] = {str(k): {"carbon": round(float(v.carbon)), "gas_share": round(float(v.gas), 1), "halfhours": int(v.n)} for k, v in wb.iterrows()}
    out["corr_wind_carbon"] = float(recent[["wind_share", "CARBON_INTENSITY"]].corr().iloc[0, 1])
    fig, ax = plt.subplots(figsize=(8, 5))
    s = recent.sample(min(15000, len(recent)), random_state=0)
    ax.scatter(s.wind_share, s.CARBON_INTENSITY, s=2, alpha=.2, color="#2a9d8f")
    ax.plot([i.mid for i in wb.index], wb.carbon, "ko-", label="Band mean")
    ax.set_xlabel("Wind share of generation (%)"); ax.set_ylabel("Carbon intensity (gCO₂/kWh)"); ax.legend()
    ax.set_title(f"Windy half-hours are cleaner: half-hourly data since Jan 2025 (r = {out['corr_wind_carbon']:.2f})")
    fig.tight_layout(); fig.savefig(CH / "04_wind_vs_carbon.png", dpi=150); plt.close()
    recent["hour"] = recent.DATETIME.dt.hour; recent["month"] = recent.DATETIME.dt.month
    heat = recent.pivot_table(index="month", columns="hour", values="CARBON_INTENSITY", aggfunc="mean")
    fig, ax = plt.subplots(figsize=(10, 4.5)); im = ax.imshow(heat, aspect="auto", cmap="RdYlGn_r")
    ax.set_yticks(range(len(heat)), ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][:len(heat)]); ax.set_xlabel("Hour of day (UTC)")
    plt.colorbar(im, label="gCO₂/kWh"); ax.set_title("When is electricity cleanest? Mean carbon intensity since Jan 2025")
    fig.tight_layout(); fig.savefig(CH / "05_carbon_heatmap.png", dpi=150); plt.close()
    out["cleanest_month_hour"] = list(map(int, np.unravel_index(np.nanargmin(heat.values), heat.shape)))
    out["dirtiest_month_hour"] = list(map(int, np.unravel_index(np.nanargmax(heat.values), heat.shape)))

    # ---------- 4. DESNZ household electricity ----------
    de = pd.read_csv(P / "desnz_domestic_electricity.csv")
    gb = de[de.code == "K03000001"].groupby("year").mean_domestic_kwh.first()
    london = de[de.code == "E12000007"].groupby("year").mean_domestic_kwh.first()
    out["gb_mean_domestic_kwh"] = {int(k): round(float(v)) for k, v in gb.items() if k in (2005, 2010, 2015, 2019, 2021, 2022, 2023, 2024)}
    out["london_mean_domestic_kwh"] = {int(k): round(float(v)) for k, v in london.items() if k in (2005, 2019, 2024)}
    la = de[(de.year == 2024) & ~de.local_authority.astype(str).str.contains("All local authorities|Unallocated", case=False)]
    la = la[la.code.astype(str).str.match(r"^[ESW]0[6789]")]
    out["la_lowest_2024"] = la.nsmallest(5, "mean_domestic_kwh")[["local_authority", "mean_domestic_kwh"]].round(0).to_dict("records")
    out["la_highest_2024"] = la.nlargest(5, "mean_domestic_kwh")[["local_authority", "mean_domestic_kwh"]].round(0).to_dict("records")
    ldn = de[(de.year == 2024) & de.code.astype(str).str.startswith("E09")].sort_values("mean_domestic_kwh")
    out["newham_2024"] = float(ldn[ldn.local_authority == "Newham"].mean_domestic_kwh.iloc[0]) if (ldn.local_authority == "Newham").any() else None
    fig, ax = plt.subplots(1, 2, figsize=(13, 6))
    ax[0].plot(gb.index, gb.values, "o-", label="Great Britain"); ax[0].plot(london.index, london.values, "o-", label="London")
    ax[0].axvspan(2021.5, 2023.5, color="#e76f51", alpha=.15, label="Energy crisis"); ax[0].legend(); ax[0].set_ylabel("Mean domestic kWh per meter")
    ax[0].set_title("Household electricity use (DESNZ)")
    ax[1].barh(ldn.local_authority, ldn.mean_domestic_kwh, color=["#e63946" if x == "Newham" else "#457b9d" for x in ldn.local_authority])
    ax[1].axvline(gb.loc[2024], color="k", ls="--", lw=1, label="GB mean"); ax[1].legend(fontsize=8); ax[1].tick_params(axis="y", labelsize=7)
    ax[1].set_title("London boroughs, 2024 (kWh per domestic meter)")
    fig.tight_layout(); fig.savefig(CH / "06_household_use.png", dpi=150); plt.close()

    (P / "key_findings.json").write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=1, default=str))

if __name__ == "__main__":
    main()
