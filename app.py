import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Maestro SKU Builder", layout="wide")
st.title("🛠️ Generador Automático de Maestro de Artículos")
st.write("Sube tus archivos descargados de Product Cloud y tu Maestro actual para generar tu tabla consolidada.")

# --- Subida de archivos ---
st.sidebar.header("Carga de archivos PC")
# Permite subir múltiples archivos fuente descargados de Product Cloud
downloads = st.sidebar.file_uploader(
    "Archivos fuente descargados (Excel)",
    type=["xlsx"],
    accept_multiple_files=True,
    help="Sube los archivos tal como los descargas de Product Cloud"
)
# Subida del maestro actual
uploaded_master = st.sidebar.file_uploader(
    "Maestro Actual (Todos SKU ok(2))", type=["xlsx"], key="master"
)

if st.sidebar.button("Generar Maestro Consolidado"):
    if not downloads or not uploaded_master:
        st.sidebar.error("Por favor sube los archivos fuente y el maestro actual.")
    else:
        # Leer maestro actual
        master_old = pd.read_excel(uploaded_master, sheet_name="Maestro PR", header=1)
        # Inicializar variables para cada fuente
        logu = consu = shipping = shipto = lead_time = general = None
        # Detectar y leer cada archivo según su nombre
        for file in downloads:
            fname = file.name.lower()
            xls = pd.ExcelFile(file)
            # Asumimos que cada Excel tiene sólo una hoja relevante:
            sheet = xls.sheet_names[0]
            if "consumerunits" in fname or "cu_recipients" in fname:
                consu = pd.read_excel(file, sheet_name=sheet, header=1)
            elif "lu_recipients" in fname or "logisticunits" in fname:
                logu = pd.read_excel(file, sheet_name=sheet, header=1)
            elif "shipping.xlsx" in fname and "shipto" not in fname:
                shipping = pd.read_excel(file, sheet_name=sheet, header=1)
            elif "shipto" in fname:
                shipto = pd.read_excel(file, sheet_name=sheet, header=1)
            elif "lead" in fname or "time" in fname:
                lead_time = pd.read_excel(file, sheet_name=sheet, header=1)
            else:
                general = pd.read_excel(file, sheet_name=sheet, header=1)
        # Verificar que todas las fuentes se leyeron
        missing = [name for name, df in {
            "LogU": logu,
            "ConsU": consu,
            "Shipping": shipping,
            "ShipTo": shipto,
            "Lead Time": lead_time,
            "General": general
        }.items() if df is None]
        if missing:
            st.sidebar.error(f"Faltan fuentes para: {', '.join(missing)}. Revisa tus archivos.")
        else:
            # --- Lógica de consolidación ---
            df = master_old[["SKU\nCódigo local"]].copy()
            df.columns = ["CodigoLocal"]

            # Descripción (ejemplo from LogU)
            df = df.merge(
                logu[["PR.LogistU.ERPID", "PR.LogistU.MyOwnPortfolio"]],
                left_on="CodigoLocal", right_on="PR.LogistU.ERPID", how="left"
            ).rename(columns={"PR.LogistU.MyOwnPortfolio": "Descripcion"})

            # Mercado: extraer UOM + traducir con tabla General
            uom_map = logu.set_index("PR.LogistU.ERPID")["PR.LogistU.UOM"]
            df["UOM"] = df["CodigoLocal"].map(uom_map)
            glos_map = dict(zip(general.iloc[:,0], general.iloc[:,1]))
            df["Mercado"] = df["UOM"].map(glos_map)

            # ...(añade aquí los merges/cálculos restantes según tus XLOOKUP)...

            # --- Mostrar y descargar resultado ---
            st.subheader("Vista Previa del Maestro Consolidado")
            st.dataframe(df.head(10))

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
st.text("PR Andina-Supply.")
