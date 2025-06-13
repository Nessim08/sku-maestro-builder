import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Vista SKU | Descripción | Mercado", layout="wide")
st.title("🛠️ Generador Automático de Vista SKU | Descripción | Mercado")
st.write(
    "Sube tu export **LogU** de Product Cloud y tu **Maestro** actual "
    "para obtener la vista consolidada sin tener que pasar por pivots."
)

# ----------------------------
# Sidebar: carga de archivos
# ----------------------------
logu_file = st.sidebar.file_uploader(
    "Export LogU (.xlsx)", 
    type=["xlsx"],
    help="LogisticUnitsProductsUpExport (hoja única)"
)
master_file = st.sidebar.file_uploader(
    "Maestro Actual (.xlsx)", 
    type=["xlsx"],
    help="Tu libro de Excel con la hoja 'Maestro'"
)
if st.sidebar.button("Generar Vista SKU"):
    if not logu_file or not master_file:
        st.sidebar.error("❌ Primero sube tu export LogU y luego tu Maestro.")
    else:
        # --- 1) Leer y filtrar LogU ---
        logu = pd.read_excel(logu_file, sheet_name=0, header=0)
        logu = logu[[
            "PR.LogistU.ERPID",
            "PR.LogistU.Description1#en-US",
            "PR.LogistU.MyOwnPortfolio"
        ]].copy()
        logu.columns = ["SKU", "Descripcion", "Mercado"]
        logu = logu[
            logu["SKU"].notna() &
            (logu["SKU"].astype(str).str.strip() != "")
        ]

        # --- 2) Leer Maestro actual ---
        master = pd.read_excel(master_file, sheet_name="Maestro", header=2)
        master = master[[
            "SKU\nCódigo local",
            "Descripción / Description",
            "Mercado / Market"
        ]].copy()
        master.columns = ["SKU", "Descripcion", "Mercado"]

        # --- 3) Extraer los SKUs que solo estaban en el Maestro viejo ---
        old_only = master[~master["SKU"].isin(logu["SKU"])]

        # --- 4) Concatenar y mostrar ---
        final = pd.concat([logu, old_only], ignore_index=True)
        st.subheader("👀 Vista Consolidada de SKU | Descripción | Mercado")
        st.dataframe(final, height=500)

        # --- 5) Botón de descarga ---
        buffer = BytesIO()
        final.to_excel(buffer, index=False)
        buffer.seek(0)
        st.download_button(
            label="⬇️ Descargar Vista SKU",
            data=buffer,
            file_name="Vista_SKU_Descripcion_Mercado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

st.markdown("---")
st.text("PR ANDINA • Generado con Streamlit")

