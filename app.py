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
        master_old = pd.read_excel(uploaded_master, sheet_name="Maestro", header=1)
        
        # --- 2) Inicializar DataFrames fuente ---
        logu = consu = shipping = None
        
        # --- 3) Detectar y leer cada export ---
        for file in downloads:
            name = file.name.lower()
            # cada workbook tiene UNA sola pestaña, la cargamos por índice 0
            df = pd.read_excel(file, sheet_name=0, header=1)
            
            if "consumerunits" in name or "cu_recipients" in name:
                consu = df
            elif "lo​​gisticunits" in name and "shipping" not in name:
                logu = df
            elif "shipping" in name:
                shipping = df
        
        # --- 4) Verificar que tenemos las 3 fuentes ---
        missing = [
            label for label, df in 
            {"LogU": logu, "ConsU": consu, "Shipping": shipping}.items()
            if df is None
        ]
        if missing:
            st.sidebar.error(f"❌ Faltan las fuentes: {', '.join(missing)}")
        else:
            # --- 5) Construir el DataFrame base con la lista de SKUs ---
            df_final = master_old[["SKU\nCódigo local"]].copy()
            df_final.columns = ["CodigoLocal"]
            
            # --- 6) Descripción desde LogU ---
            df_final = df_final.merge(
                logu[["PR.LogistU.ERPID","PR.LogistU.MyOwnPortfolio"]],
                left_on="CodigoLocal", right_on="PR.LogistU.ERPID",
                how="left"
            ).rename(columns={"PR.LogistU.MyOwnPortfolio":"Descripcion"})
            
            # --- 7) Mercado desde ConsU (CountryOfOrigin) ---
            df_final["Mercado"] = df_final["CodigoLocal"].map(
                consu.set_index("PR.ConsumU.ERPID")["PR.LiquiQual.CountryOfOrigin"]
            )
            
            # --- 8) ABC (constante 0) ---
            df_final["ABC"] = 0
            
            # --- 9) Pack Size (NumberOfConsumerUnit) ---
            df_final["Pack Size (UxC)"] = df_final["CodigoLocal"].map(
                logu.set_index("PR.LogistU.ERPID")["PR.LogistU.NumberOfConsumerUnit"]
            )
            
            # --- 10) Bottle size (Volume) ---
            # Ejemplo: si tu export LogU tuviera 'PR.LogistU.TotalBeverageVolume':
            # df_final["Bottle size"] = df_final["CodigoLocal"].map(
            #     logu.set_index("PR.LogistU.ERPID")["PR.LogistU.TotalBeverageVolume"]
            # )
            # Ajusta la columna según tu export.
            
            # --- 11) Lead Times desde Shipping ---
            shipping_idx = shipping.set_index("PR.LogistU.ERPID")
            df_final["DispatchToReceiveLeadTime"] = df_final["CodigoLocal"].map(
                shipping_idx["PR.Shipping.DispatchToReceiveLeadTime"]
            )
            df_final["OrderToReceiveLeadTime"] = df_final["CodigoLocal"].map(
                shipping_idx["PR.Shipping.OrderToReceiveLeadTime"]
            )
            
            # --- 12) Origin & Destination Warehouses ---
            df_final["OriginWarehouse"] = df_final["CodigoLocal"].map(
                shipping_idx["PR.ShipFrom.InitiatorWarehouseName"]
            )
            df_final["DestinationWarehouse"] = df_final["CodigoLocal"].map(
                shipping_idx["PR.ShipTo.RecipientWarehouseName"]
            )
            
            # ... aquí puedes seguir agregando columnas replicando tus XLOOKUP ...
            
            # --- 13) Mostrar y permitir descarga ---
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
st.text("PR ANDINA • Generado con Streamlit")```

**Puntos clave para ajustar a tu caso**:

- Verifica que los fragmentos de nombre en el `if "consumerunits" in name` coincidan con tus archivos.  
- Asegúrate de que las columnas referenciadas existen en cada export (por ejemplo, `PR.LogistU.NumberOfConsumerUnit`, `PR.LiquiQual.CountryOfOrigin`, `PR.Shipping.DispatchToReceiveLeadTime`, etc.).  
- Si necesitas campos adicionales, sigue el mismo patrón: extraer de `logu`, `consu` o `shipping` con `.map(...)` o `.merge(...)`.

Con esto ya tienes el script completo listo para subir a GitHub y desplegar. ¡Prueba y me dices si hace falta pulir algo más!

