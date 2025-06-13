import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Maestro SKU Builder", layout="wide")
st.title("🛠️ Generador Automático de Vista SKU | Descripción | Mercado")
st.write(
    "Sube tu export LogU de Product Cloud y tu Maestro actual "
    "para obtener una vista con SKU, Descripción y Mercado."
)

# ----------------------------
# Subida de archivos
# ----------------------------
downloads = st.sidebar.file_uploader(
    "Archivo raw LogU (.xlsx)", 
    type=["xlsx"], 
    accept_multiple_files=True,
    help="LogisticUnitsProductsUpExport_for_Affiliate_lu_recipients"
)
uploaded_master = st.sidebar.file_uploader(
    "Maestro Actual (.xlsx)", 
    type=["xlsx"], 
    key="master",
    help="Libro con la hoja 'Maestro' (encabezados en la fila 3)."
)

if st.sidebar.button("Generar Vista"):
    # 1) Validaciones iniciales
    if not downloads or not uploaded_master:
        st.sidebar.error("❌ Sube el export LogU y tu Maestro actual primero.")
        st.stop()

    # 2) Leer Maestro actual (header=2 → tercera fila)
    master_old = pd.read_excel(uploaded_master, sheet_name="Maestro", header=2)

    # 3) Detectar columna SKU en Maestro
    sku_col = next((c for c in master_old.columns if "SKU" in str(c)), None)
    if sku_col is None:
        st.sidebar.error(
            "❌ No encontré la columna SKU en tu Maestro. "
            f"Columnas disponibles: {', '.join(master_old.columns.astype(str))}"
        )
        st.stop()

    # 4) Leer export LogU
    logu = None
    for f in downloads:
        name = f.name.lower()
        if "logisticunits" in name and "recipients" in name:
            logu = pd.read_excel(f, header=0)

    if logu is None:
        st.sidebar.error("❌ No encontré un archivo LogU válido entre los subidos.")
        st.stop()

    # 5) Construir df_final con las 3 columnas
    df_final = master_old[[sku_col]].copy()
    df_final.columns = ["CodigoLocal"]

    # Preparamos el índice de lookup
    lookup = logu.set_index("PR.LogistU.ERPID")

    # 5.1) Descripción
    df_final["Descripcion"] = df_final["CodigoLocal"].map(
        lookup["PR.LogistU.Description1#en-US"]
    )

    # 5.2) Mercado
    df_final["Mercado"] = df_final["CodigoLocal"].map(
        lookup["PR.LogistU.MyOwnPortfolio"]
    )

    # 6) Mostrar en pantalla
    st.subheader("Vista: SKU | Descripción | Mercado")
    st.dataframe(df_final.head(20))

    # 7) Botón de descarga
    buffer = BytesIO()
    df_final.to_excel(buffer, index=False)
    buffer.seek(0)
    st.download_button(
        label="⬇️ Descargar Vista",
        data=buffer,
        file_name="Vista_SKU_Desc_Mercado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.markdown("---")
st.text("PR ANDINA • Generado con Streamlit")


