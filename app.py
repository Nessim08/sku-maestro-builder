import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Maestro SKU Builder", layout="wide")
st.title("🛠️ Generador Automático de Maestro de Artículos")
st.write("Sube tus archivos descargados de Product Cloud y tu Maestro actual para generar tu tabla consolidada.")

# --- Subida de archivos ---
st.sidebar.header("Carga de archivos PC")
# Subida de múltiples archivos fuente
uploaded_sources = st.sidebar.file_uploader(
    "Archivos fuente descargados (Excel)",
    type=["xlsx"],
    accept_multiple_files=True,
    help="Sube aquí los archivos tal como los descargas de Product Cloud"
)
# Subida del maestro actual
uploaded_master = st.sidebar.file_uploader(
    "Maestro Actual", type=["xlsx"], key="master"
)

if st.sidebar.button("Generar Maestro Consolidado"):
    # Validación de carga
    if not uploaded_sources or not uploaded_master:
        st.sidebar.error("Por favor sube los archivos fuente y el maestro actual.")
    else:
        # Leer maestro actual
        master_old = pd.read_excel(uploaded_master, sheet_name="Todos SKU ok(2)", header=1)
        # Inicializar contenedores para las hojas
        sources = {"LogU": None, "ConsU": None, "Lead Time": None, "Shipping": None, "General": None}
        # Detectar y leer cada hoja desde los archivos subidos
        for file in uploaded_sources:
            xls = pd.ExcelFile(file)
            for sheet in sources.keys():
                if sheet in xls.sheet_names:
                    sources[sheet] = pd.read_excel(file, sheet_name=sheet, header=1)
        # Verificar que todas las hojas fueron encontradas
        missing = [s for s, df in sources.items() if df is None]
        if missing:
            st.sidebar.error(f"Faltan fuentes para: {', '.join(missing)}. Revisa tus archivos.")
        else:
            logu       = sources["LogU"]
            consu      = sources["ConsU"]
            lead_time  = sources["Lead Time"]
            shipping   = sources["Shipping"]
            general    = sources["General"]

            # --- Lógica de consolidación ---
            df = master_old[["SKU\nCódigo local"]].copy()
            df.columns = ["CodigoLocal"]

            # Ejemplo: descripción desde LogU
            df = df.merge(
                logu[["PR.LogistU.ERPID", "PR.LogistU.MyOwnPortfolio"]],
                left_on="CodigoLocal", right_on="PR.LogistU.ERPID", how="left"
            ).rename(columns={"PR.LogistU.MyOwnPortfolio": "Descripcion"})

            # Ejemplo: mercado usando tabla General
            uom_map = logu.set_index("PR.LogistU.ERPID")["PR.LogistU.UOM"]
            df["UOM"] = df["CodigoLocal"].map(uom_map)
            glos_map = dict(zip(
                general.iloc[:,0], # Ajusta índice de columna clave
                general.iloc[:,1]  # Ajusta índice de columna valor
            ))
            df["Mercado"] = df["UOM"].map(glos_map)

            # ...(agrega aquí el resto de merges y cálculos según tus fórmulas XLOOKUP)...

            # --- Resultado final y descarga ---
            st.subheader("Vista Previa del Maestro Consolidado")
            st.dataframe(df.head(10))

            buffer = BytesIO()
            df.to_excel(buffer, index=False)
            buffer.seek(0)
            st.download_button(
                label="⬇️ Descargar Maestro Consolidado",
                data=buffer,
                file_name="Maestro_Consolidado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

st.markdown("---")
st.text("Hecho con Streamlit • Ajusta sheet_name y columnas según tu caso.")

