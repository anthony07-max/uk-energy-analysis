"""Download UK energy open data: Ofgem price cap model (Annex 9), ONS CPI energy indices,
NESO historic generation mix, and DESNZ subnational electricity consumption."""
from pathlib import Path
import requests

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
UA = {"User-Agent": "Mozilla/5.0 (portfolio data analysis)"}
FILES = {
    # Ofgem: final levelised cap rates model (Annex 9), Oct-Dec 2026 version, includes historical cap levels back to Apr 2017
    "ofgem_annex9.xlsx": "https://www.ofgem.gov.uk/sites/default/files/2026-08/Annex-9-Levelisation-allowance-methodology-and-levelised-cap-levels-v1.11.xlsx",
    # NESO: historic GB generation mix and carbon intensity (half-hourly, 2009 onwards)
    "neso_generation_mix.csv": "https://api.neso.energy/dataset/88313ae5-94e4-4ddc-a790-593554d8c6b9/resource/f93d1835-75bc-43e5-84ad-12472b180a98/download/df_fuel_ckan.csv",
    # DESNZ: subnational electricity consumption statistics 2005-2024
    "desnz_subnational_electricity.xlsx": "https://assets.publishing.service.gov.uk/media/69426e905431f4f94d7f0b5e/Subnational_electricity_consumption_statistics_2005-2024.xlsx",
}
ONS = {"cpi_electricity": "d7dt", "cpi_gas": "d7du", "cpi_all_items": "d7bt"}
ONS_URL = "https://www.ons.gov.uk/generator?format=csv&uri=/economy/inflationandpriceindices/timeseries/{cdid}/mm23"

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        r = requests.get(url, headers=UA, timeout=600); r.raise_for_status()
        (RAW / name).write_bytes(r.content); print(name, len(r.content) // 1000, "KB")
    for name, cdid in ONS.items():
        r = requests.get(ONS_URL.format(cdid=cdid), headers=UA, timeout=120); r.raise_for_status()
        (RAW / f"ons_{name}.csv").write_bytes(r.content); print(name)

if __name__ == "__main__":
    main()
