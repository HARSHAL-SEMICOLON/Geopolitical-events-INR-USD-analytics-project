"""Rebuild the whole project by running the notebooks in 03_Notebooks in order.

    python run_pipeline.py

Each notebook is executed top to bottom and saved with its outputs, exactly as if you had
opened it in Jupyter and clicked "Run All". No internet access is needed.

Requires: pandas, numpy, openpyxl, matplotlib, nbformat, nbclient, ipykernel
(all included in Anaconda; otherwise: pip install pandas numpy openpyxl matplotlib nbclient ipykernel)
"""
import sys
import time
from pathlib import Path

NB_DIR = Path(__file__).resolve().parent / "03_Notebooks"
NOTEBOOKS = [
    "01_Ingest_Raw_Data.ipynb",
    "02_Align_and_Transform.ipynb",
    "03_Compute_Event_Windows.ipynb",
    "04_Build_Database.ipynb",
    "05_Write_Results_Report.ipynb",
    "06_Analysis_and_Charts.ipynb",
]


def main():
    try:
        import nbformat
        from nbclient import NotebookClient
    except ImportError:
        sys.exit("Missing packages - run:  pip install nbclient nbformat ipykernel\n"
                 "(or open the notebooks in Jupyter and use Run All, in order 01 -> 06)")
    for name in NOTEBOOKS:
        start = time.time()
        nb = nbformat.read(NB_DIR / name, as_version=4)
        NotebookClient(nb, timeout=900, kernel_name="python3",
                       resources={"metadata": {"path": str(NB_DIR)}}).execute()
        nbformat.write(nb, NB_DIR / name)
        print(f"  done  {name}  ({time.time() - start:.0f}s)")
    print("\nFinished. Database: 02_Database/geo_inr_analytics.db | Power BI tables: 01_Data/4_PowerBI_Tables/"
          " | Charts: 05_Documentation/Figures/")


if __name__ == "__main__":
    main()
