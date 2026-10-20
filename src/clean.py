"""Tidy the four sources into analysis-ready tables."""
from pathlib import Path
import re
import numpy as np
import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"

def ofgem():
    ws = openpyxl.load_workbook(RAW / "ofgem_annex9.xlsx", read_only=True, data_only=True)["1c Consumption adjusted levels"]
    rows = list(ws.iter_rows(values_only=True))
    # Find the 'Other Payment Method' (direct debit) section, 'Typical consumption' table, then the four horizontal fuel blocks
    start = next(i for i, r in enumerate(rows) if r[1] == "Other Payment Method")
    hdr_i = next(i for i in range(start, len(rows)) if rows[i][1] == "Typical consumption")
    fuel_row = rows[next(i for i in range(start, hdr_i) if rows[i][1] and str(rows[i][1]).startswith("Electricity: Single"))]
    blocks = {str(v).strip(): j for j, v in enumerate(fuel_row) if v}
    out = []
    for fuel, j0 in blocks.items():
        hdr = rows[hdr_i]
        cols = [j for j in range(j0 + 1, j0 + 31) if hdr[j] and re.search(r"\d{4}", str(hdr[j]))]
        for i in range(hdr_i + 1, hdr_i + 20):
            comp = rows[i][j0]
            if comp is None: continue
            comp = str(comp).strip()
            for j in cols:
                v = rows[i][j]
                out.append({"fuel": fuel, "period": str(hdr[j]).strip(), "component": comp, "gbp_per_year": pd.to_numeric(v, errors="coerce")})
            if comp == "Total inc VAT": break
    df = pd.DataFrame(out)
    df["period_start"] = pd.to_datetime(df.period.str.split(" - ").str[0].str.replace("Sept", "Sep").str.replace("June", "Jun"), format="mixed")
    return df

def ons():
    frames = []
    for name in ["cpi_electricity", "cpi_gas", "cpi_all_items"]:
        d = pd.read_csv(RAW / f"ons_{name}.csv", header=None, names=["period", "value"], skiprows=8)
        d = d[d.period.str.match(r"^\d{4} [A-Z]{3}$", na=False)]
        d["date"] = pd.to_datetime(d.period, format="%Y %b"); d["series"] = name; d["value"] = d.value.astype(float)
        frames.append(d[["date", "series", "value"]])
    return pd.concat(frames).pivot(index="date", columns="series", values="value").reset_index()

def neso():
    g = pd.read_csv(RAW / "neso_generation_mix.csv", parse_dates=["DATETIME"])
    fuels = ["GAS", "COAL", "NUCLEAR", "WIND", "WIND_EMB", "HYDRO", "IMPORTS", "BIOMASS", "OTHER", "SOLAR", "STORAGE"]
    g["year"] = g.DATETIME.dt.year
    annual = g.groupby("year")[fuels + ["GENERATION"]].sum()
    shares = annual[fuels].div(annual.GENERATION, axis=0) * 100
    shares["WIND_TOTAL"] = shares.WIND + shares.WIND_EMB
    shares["carbon_intensity"] = g.groupby("year").CARBON_INTENSITY.mean()
    shares["coal_zero_halfhours_pct"] = g.groupby("year").COAL.apply(lambda s: (s <= 0).mean() * 100)
    hh = g[["DATETIME", "CARBON_INTENSITY", "GENERATION", "WIND", "WIND_EMB", "SOLAR", "GAS", "COAL"]].copy()
    hh["wind_share"] = (hh.WIND + hh.WIND_EMB) / hh.GENERATION * 100
    hh["gas_share"] = hh.GAS / hh.GENERATION * 100
    return shares.reset_index(), hh

def desnz():
    frames = []
    xl = pd.ExcelFile(RAW / "desnz_subnational_electricity.xlsx")
    for sh in [s for s in xl.sheet_names if s.isdigit()]:
        d = pd.read_excel(xl, sheet_name=sh, header=4)
        d.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in d.columns]
        # 2005-2010 sheets label the column "Domestic"; later sheets "All Domestic"
        pick = lambda pre: next(c for c in d.columns if c.startswith(pre) and re.search(r": (All )?Domestic$", c))
        mean_col, tot_col, met_col = pick("Mean consumption"), pick("Total consumption"), pick("Number of meters")
        d = d.rename(columns={d.columns[0]: "code", d.columns[1]: "region", d.columns[2]: "local_authority",
                              mean_col: "mean_domestic_kwh", tot_col: "domestic_gwh", met_col: "domestic_meters_k"})
        d["year"] = int(sh)
        frames.append(d[["code", "region", "local_authority", "year", "mean_domestic_kwh", "domestic_gwh", "domestic_meters_k"]])
    d = pd.concat(frames)
    for c in ["mean_domestic_kwh", "domestic_gwh", "domestic_meters_k"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    return d.dropna(subset=["mean_domestic_kwh"])

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    of = ofgem(); of.to_csv(OUT / "ofgem_cap_components.csv", index=False)
    print("Ofgem:", of.fuel.unique(), of.period.nunique(), "periods")
    on = ons(); on.to_csv(OUT / "ons_cpi_energy.csv", index=False); print("ONS to", on.date.max().date())
    sh, hh = neso(); sh.to_csv(OUT / "neso_annual_mix.csv", index=False); hh.to_parquet(OUT / "neso_halfhourly.parquet", index=False)
    print("NESO to", hh.DATETIME.max())
    de = desnz(); de.to_csv(OUT / "desnz_domestic_electricity.csv", index=False); print("DESNZ", de.year.min(), "-", de.year.max(), len(de))

if __name__ == "__main__":
    main()
