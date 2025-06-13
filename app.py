import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Maestro SKU Builder", layout="wide")
st.title("🛠️ Generador Automático de Maestro de Artículos")
st.write(
    "Sube tus 3 archivos exportados de Product Cloud (hoja única) y tu Maestro actual "
    "para obtener la tabla consolidada."
)

# ----------------------------
# Subida de archivos
# ----------------------------
downloads = st.sidebar.file_uploader(
    "Archivos fuente de Product Cloud (.xlsx)", 
    type=["xlsx"], 
    accept_multiple_files=True,
    help="Sube los tres exports: LogU, ConsU y Shipping, cada uno con su única hoja."
)
uploaded_master = st.sidebar.file_uploader(
    "Maestro Actual (Maestro)", 
    type=["xlsx"], 
    key="master",
    help="Tu libro de Excel con la hoja 'Maestro' que contiene el listado de SKUs."
)

if st.sidebar.button("Generar Maestro Consolidado"):
    if not downloads or not uploaded_master:
        st.sidebar.error("❌ Primero sube los tres exports y luego tu archivo Maestro.")
    else:
        # 1) Leer el Maestro actual (cabeceras en fila 3 → header=2)
        master_old = pd.read_excel(uploaded_master, sheet_name="Maestro", header=2)

        # 2) Inicializar DataFrames fuente
        logu = consu = shipping = None

        # 3) Detectar y leer cada export (cabeceras en fila 3 → header=2)
        for file in downloads:
            name = file.name.lower()
            df = pd.read_excel(file, sheet_name=0, header=2)
            if "consumerunits" in name or "cu_recipients" in name:
                consu = df
            elif "logisticunits" in name and "shipping" not in name:
                logu = df
            elif "shipping" in name:
                shipping = df

        # 4) Verificar que tenemos las 3 fuentes
        missing = [
            label for label, df in 
            {"LogU": logu, "ConsU": consu, "Shipping": shipping}.items()
            if df is None
        ]
        if missing:
            st.sidebar.error(f"❌ Faltan las fuentes: {', '.join(missing)}")
        else:
            # 5) Construir DataFrame base con SKUs
            df_final = master_old[["SKU\nCódigo local"]].copy()
            df_final.columns = ["CodigoLocal"]

            # 6) SKU, Descripción y Mercado desde LogU
            logu_idx = logu.set_index("PR.LogistU.ERPID")

            # asigna el mismo CódigoLocal solo si existe en LogU
            df_final["SKU"] = df_final["CodigoLocal"].where(
                df_final["CodigoLocal"].isin(logu_idx.index)
            )
            df_final["Descripcion"] = df_final["SKU"].map(
                logu_idx["PR.LogistU.Description1#en-US"]
            )
            df_final["Mercado"] = df_final["SKU"].map(
                logu_idx["PR.LogistU.MyOwnPortfolio"]
            )

            # 7) Pack Size (UxC) desde LogU
            df_final["Pack Size (UxC)"] = df_final["SKU"].map(
                logu_idx["PR.LogistU.NumberOfConsumerUnit"]
            )

            # 8) Bottle size desde LogU multiplicado por 10
            df_final["Bottle size"] = (
                df_final["SKU"]
                .map(logu_idx["PR.BranQualSiz.Size"])
                .astype(float)
                * 10
            )

            # 9) Eliminamos filas sin SKU
            df_final = df_final.dropna(subset=["SKU"])

            # 10) Mostrar y descargar
            st.subheader("Vista Previa Maestro Consolidado")
            st.dataframe(df_final.head(10))

            buffer = BytesIO()
            df_final.to_excel(buffer, index=False)
            buffer.seek(0)
            st.download_button(
                label="⬇️ Descargar Maestro Consolidado",
                data=buffer,
                file_name="Maestro_Consolidado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

st.markdown("---")
st.text("PR ANDINA • Generado con Streamlit")



