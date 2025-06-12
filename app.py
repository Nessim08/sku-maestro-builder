import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Maestro SKU Builder", layout="wide")
st.title("🛠️ Generador Automático de Maestro de Artículos")
st.write("Sube tus archivos de Product Cloud y el maestro actual para generar la tabla consolidada.")

# --- Subida de archivos ---
st.sidebar.header("Carga de archivos")
uploaded_logu      = st.sidebar.file_uploader("Archivo LogU (Excel)",      type=["xlsx"], key="logu")
uploaded_consu     = st.sidebar.file_uploader("Archivo ConsU (Excel)",     type=["xlsx"], key="consu")
uploaded_lead      = st.sidebar.file_uploader("Archivo Lead Time (Excel)",  type=["xlsx"], key="lead")
uploaded_shipping  = st.sidebar.file_uploader("Archivo Shipping (Excel)",   type=["xlsx"], key="shipping")
uploaded_general   = st.sidebar.file_uploader("Archivo General (Excel)",    type=["xlsx"], key="general")
uploaded_master    = st.sidebar.file_uploader("Maestro Actual (Todos SKU ok(2))", type=["xlsx"], key="master")

if st.sidebar.button("Generar Maestro Consolidado"):
    # Verificación mínima
    if not all([uploaded_logu, uploaded_consu, uploaded_lead, uploaded_shipping, uploaded_general, uploaded_master]):
        st.sidebar.error("Por favor sube todos los archivos antes de generar.")
    else:
        # Leer cada hoja con pandas
        logu       = pd.read_excel(uploaded_logu,      sheet_name="LogU",        header=1)
        consu      = pd.read_excel(uploaded_consu,     sheet_name="ConsU",       header=1)
        lead_time  = pd.read_excel(uploaded_lead,      sheet_name="Lead Time",   header=1)
        shipping   = pd.read_excel(uploaded_shipping,  sheet_name="Shipping",    header=1)
        general    = pd.read_excel(uploaded_general,   sheet_name="General",     header=1)
        master_old = pd.read_excel(uploaded_master,    sheet_name="Todos SKU ok(2)", header=1)

        # --- Lógica de consolidación ---
        # Partimos de la lista de SKUs del maestro actual
        df = master_old[["SKU\nCódigo local"]].copy()
        df.columns = ["CodigoLocal"]

        # Ejemplo: descripción desde LogU
        df = df.merge(
            logu[["PR.LogistU.ERPID", "PR.LogistU.MyOwnPortfolio"]],
            left_on="CodigoLocal", right_on="PR.LogistU.ERPID", how="left"
        ).rename(columns={"PR.LogistU.MyOwnPortfolio": "Descripcion"})

        # Ejemplo: mercado usando Glosario intermedio
        # 1) extraer UOM
        uom_map = logu.set_index("PR.LogistU.ERPID")["PR.LogistU.UOM"]
        df["UOM"] = df["CodigoLocal"].map(uom_map)
        # 2) traducir con tabla de "General"
        glos = general[["Key", "Value"]]  # Ajusta nombres a los reales
        glos_map = dict(zip(glos["Key"], glos["Value"]))
        df["Mercado"] = df["UOM"].map(glos_map)

        # (Sigue añadiendo los merges y cálculos según tus fórmulas XLOOKUP)

        # --- Resultado final y descarga ---
        st.subheader("Vista Previa del Maestro Consolidado")
        st.dataframe(df.head(10))

        # Generar archivo Excel en memoria
        output = BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)
        st.download_button(
            label="⬇️ Descargar Maestro Consolidado",
            data=output,
            file_name="Maestro_Consolidado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

st.markdown("---")
st.text("Hecho con Streamlit • Ajusta los nombres de hojas y columnas al tuyo.")
