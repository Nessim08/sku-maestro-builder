import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Maestro SKU Builder", layout="wide")
st.title("🛠️ Generador Automático de Maestro de Artículos")
st.write("Sube los archivos exportados de Product Cloud (hoja ‘Export’) y tu Maestro actual para obtener la tabla consolidada.")

# Subida de archivos: múltiples fuentes y maestro actual
downloads = st.sidebar.file_uploader(
    "Archivos fuente descargados (Excel) - hoja 'Export'", type=["xlsx"],
    accept_multiple_files=True,
    help="Sube todos los Excel que descargas de Product Cloud, cada uno con pestaña 'Export'"
)
uploaded_master = st.sidebar.file_uploader(
    "Maestro PR ANDINA (Maestro)", type=["xlsx"], key="master"
)

if st.sidebar.button("Generar Maestro Consolidado"):
    if not downloads or not uploaded_master:
        st.sidebar.error("Por favor sube los archivos fuente (Export) y tu maestro actual.")
    else:
        # Leer maestro actual
        master_old = pd.read_excel(uploaded_master, sheet_name="Maestro", header=1)
        # Inicializar variables para cada fuente
        logu = consu = shipping = shipto = lead_time = general = None
        # Leer cada archivo asumiendo hoja 'Export'
        for file in downloads:
            fname = file.name.lower()
            df_export = pd.read_excel(file, sheet_name="Export", header=1)
            if "consumerunits" in fname or "cu_recipients" in fname:
                consu = df_export
            elif "logisticunits" in fname and "shipto" not in fname:
                logu = df_export
            elif "shipping" in fname and "shipto" not in fname:
                shipping = df_export
            elif "shipto" in fname:
                shipto = df_export
            elif "lead" in fname and "time" in fname:
                lead_time = df_export
            else:
                # Si hay otro export genérico se considera tabla General
                general = df_export
        # Verificar que todas las tablas se cargaron
        missing = [name for name, df in {
            "LogU": logu,
            "ConsU": consu,
            "Shipping": shipping,
            "ShipTo": shipto,
            "Lead Time": lead_time,
            "General": general
        }.items() if df is None]
        if missing:
            st.sidebar.error(f"Faltan las tablas: {', '.join(missing)}. Revisa los archivos subidos.")
        else:
            # Construir DataFrame base con lista de SKUs
            df = master_old[["SKU\nCódigo local"]].copy()
            df.columns = ["CodigoLocal"]

            # 1) Descripción desde LogU
            df = df.merge(
                logu[["PR.LogistU.ERPID","PR.LogistU.MyOwnPortfolio"]],
                left_on="CodigoLocal", right_on="PR.LogistU.ERPID", how="left"
            ).rename(columns={"PR.LogistU.MyOwnPortfolio":"Descripcion"})

            # 2) Mercado usando tabla General
            uom_map = logu.set_index("PR.LogistU.ERPID")["PR.LogistU.UOM"]
            df["UOM"] = df["CodigoLocal"].map(uom_map)
            glos_map = dict(zip(general.iloc[:,0], general.iloc[:,1]))
            df["Mercado"] = df["UOM"].map(glos_map)

            # 3) Pack Size (UxC)
            df["Pack Size (UxC)"] = df["CodigoLocal"].map(
                logu.set_index("PR.LogistU.ERPID")["PR.LogistU.F"]
            )

            # 4) Bottle size (multiplicación x10)
            df["Bottle size"] = df["CodigoLocal"].map(
                logu.set_index("PR.LogistU.ERPID")["PR.LogistU.G"]
            ) * 10

            # 5) Lead Time
            df = df.merge(
                lead_time[[lead_time.columns[0], "Lead Time"]],
                left_on="CodigoLocal", right_on=lead_time.columns[0], how="left"
            )
            # 6) Shipping origin
            df = df.merge(
                shipping[[shipping.columns[0], shipping.columns[1]]].rename(
                    columns={shipping.columns[1]: "OriginWarehouse"}
                ),
                left_on="CodigoLocal", right_on=shipping.columns[0], how="left"
            )

            # (Agrega el resto de campos según tus XLOOKUP)

            # Mostrar y descargar
            st.subheader("Vista Previa Maestro Consolidado")
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
st.text("PR ANDINA-SUPPLY")
