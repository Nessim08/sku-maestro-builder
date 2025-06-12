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
        # --- 1) Leer el Maestro actual ---
        # Ahora asumimos que la cabecera está en la primera fila (header=0)
        master_old = pd.read_excel(uploaded_master, sheet_name="Maestro", header=1)
        
        # --- 2) Detectar dinámicamente la columna de SKU/Código local ---
        cols = master_old.columns.tolist()
        sku_candidates = [c for c in cols 
                          if "SKU" in c.upper() and "CÓDIGO" in c.upper()]
        if not sku_candidates:
            st.sidebar.error(
                "❌ No he encontrado ninguna columna con 'SKU' y 'Código' en el Maestro.\n"
                f"Columnas disponibles: {', '.join(cols)}"
            )
            st.stop()
        sku_col = sku_candidates[0]

        # --- 3) Inicializar DataFrames fuente ---
        logu = consu = shipping = None
        
        # --- 4) Detectar y leer cada export ---
        for file in downloads:
            name = file.name.lower()
            df = pd.read_excel(file, sheet_name=0, header=1)
            if "consumerunits" in name or "cu_recipients" in name:
                consu = df
            elif "logisticunits" in name and "shipping" not in name:
                logu = df
            elif "shipping" in name:
                shipping = df
        
        # --- 5) Verificar que tenemos las 3 fuentes ---
        missing = [
            label for label, df in 
            {"LogU": logu, "ConsU": consu, "Shipping": shipping}.items()
            if df is None
        ]
        if missing:
            st.sidebar.error(f"❌ Faltan las fuentes: {', '.join(missing)}")
        else:
            # --- 6) Definir mapeos de columnas ---
            # Formato: "Nombre destino en df_final": (df_fuente, columna_índice, columna_valor)
            field_mappings = {
                "Descripcion":               (logu,     "PR.LogistU.ERPID", "PR.LogistU.MyOwnPortfolio"),
                "Mercado":                   (consu,    "PR.ConsumU.ERPID", "PR.LiquiQual.CountryOfOrigin"),
                "Pack Size (UxC)":           (logu,     "PR.LogistU.ERPID", "PR.LogistU.NumberOfConsumerUnit"),
                # Ajusta el nombre de la columna tal y como venga en tu export:
                "Bottle size":               (logu,     "PR.LogistU.ERPID", "PR.LogistU.TotalBeverageVolume"),
                "DispatchToReceiveLeadTime": (shipping, "PR.LogistU.ERPID", "PR.Shipping.DispatchToReceiveLeadTime"),
                "OrderToReceiveLeadTime":    (shipping, "PR.LogistU.ERPID", "PR.Shipping.OrderToReceiveLeadTime"),
                "OriginWarehouse":           (shipping, "PR.LogistU.ERPID", "PR.ShipFrom.InitiatorWarehouseName"),
                "DestinationWarehouse":      (shipping, "PR.LogistU.ERPID", "PR.ShipTo.RecipientWarehouseName"),
                # Añade aquí más mapeos si los necesitas...
            }

            # --- 7) Construir DataFrame final y aplicar mapeos ---
            df_final = master_old[[sku_col]].copy()
            df_final.columns = ["CodigoLocal"]

            for dest_col, (src_df, idx_col, val_col) in field_mappings.items():
                lookup = src_df.set_index(idx_col)[val_col]
                df_final[dest_col] = df_final["CodigoLocal"].map(lookup)

            # --- 8) Columnas adicionales ---
            df_final["ABC"] = 0

            # --- 9) Vista previa y descarga ---
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
