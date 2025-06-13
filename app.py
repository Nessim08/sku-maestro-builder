import streamlit as st
import pandas as pd
from io import BytesIO

# ----------------------------------------
# Configuración de la app
# ----------------------------------------
st.set_page_config(page_title="Maestro SKU Builder", layout="wide")
st.title("🛠️ Generador Automático de Maestro de Artículos")
st.write(
    "Sube tus archivos raw exportados de Product Cloud y tu Maestro actual "
    "para obtener la tabla consolidada sin usar pivot tables."
)

# ----------------------------------------
# Sidebar: subir archivos
# ----------------------------------------
raw_files = st.sidebar.file_uploader(
    "Archivos raw de Product Cloud (.xlsx)", 
    type=["xlsx"], 
    accept_multiple_files=True,
    help="""
    Debes subir:
      • LU_Recipients (LogU)  
      • CU_Recipients (ConsU)  
      • ShipTo_Recipients (Stock Cover)  
      • Shipping  
    Cada uno debe llevar su hoja única con datos en la fila 1 como cabecera.
    """
)

uploaded_master = st.sidebar.file_uploader(
    "Maestro Actual (.xlsx)", 
    type=["xlsx"], 
    key="master",
    help="Tu libro de Excel con la hoja ‘Maestro’ (header en fila 2)."
)

if st.sidebar.button("Generar Maestro Consolidado"):
    if not raw_files or not uploaded_master:
        st.sidebar.error("❌ Necesitas subir TODOS los archivos raw y el Maestro.", icon="🚨")
    else:
        # 1) Leemos el Maestro actual
        master_df = pd.read_excel(uploaded_master, sheet_name="Maestro", header=1)
        
        # 2) Inicializamos variables
        df_logu = df_cu = df_shipto = df_shipping = None
        
        # 3) Detectamos y leemos cada raw file
        for f in raw_files:
            name = f.name.lower()
            df = pd.read_excel(f, sheet_name=0)  # asumimos header en row 0
            if "lu_recipients" in name or "logisticunits" in name:
                df_logu = df
            elif "cu_recipients" in name or "consumerunits" in name:
                df_cu = df
            elif "shipto" in name or "stock cover" in name:
                df_shipto = df
            elif "shipping" in name and "shipto" not in name:
                df_shipping = df
        
        # 4) Verificamos que todo exista
        missing = [
            label for label, df in {
                "LogU": df_logu,
                "ConsU": df_cu,
                "ShipTo": df_shipto,
                "Shipping": df_shipping
            }.items() if df is None
        ]
        if missing:
            st.sidebar.error(f"❌ Faltan los raw files: {', '.join(missing)}", icon="🚨")
        else:
            # 5) Partimos del listado de SKUs del Maestro
            df_final = master_df[["SKU\nCódigo local"]].copy()
            df_final.columns = ["CodigoLocal"]
            
            # 6) Descripción (MyOwnPortfolio) desde LogU
            df_final = (
                df_final
                .merge(
                    df_logu[["PR.LogistU.ERPID", "PR.LogistU.MyOwnPortfolio"]],
                    left_on="CodigoLocal", right_on="PR.LogistU.ERPID",
                    how="left"
                )
                .rename(columns={"PR.LogistU.MyOwnPortfolio": "Descripcion"})
                .drop(columns=["PR.LogistU.ERPID"])
            )
            
            # 7) Mercado (CountryOfOrigin) desde CU
            df_final["Mercado"] = df_final["CodigoLocal"].map(
                df_cu.set_index("PR.ConsumU.ERPID")["PR.LiquiQual.CountryOfOrigin"]
            )
            
            # 8) ABC (inicializamos en 0)
            df_final["ABC"] = 0
            
            # 9) Pack Size (NumberOfConsumerUnit) desde LogU
            df_final["Pack Size (UxC)"] = df_final["CodigoLocal"].map(
                df_logu.set_index("PR.LogistU.ERPID")["PR.LogistU.NumberOfConsumerUnit"]
            )
            
            # 10) Bottle size si existe
            if "PR.LogistU.TotalBeverageVolume" in df_logu.columns:
                df_final["Bottle size"] = df_final["CodigoLocal"].map(
                    df_logu.set_index("PR.LogistU.ERPID")["PR.LogistU.TotalBeverageVolume"]
                )
            
            # 11) Lead Times desde Shipping
            ship_idx = df_shipping.set_index("PR.LogistU.ERPID")
            df_final["DispatchToReceiveLeadTime"] = df_final["CodigoLocal"].map(
                ship_idx["PR.Shipping.DispatchToReceiveLeadTime"]
            )
            df_final["OrderToReceiveLeadTime"] = df_final["CodigoLocal"].map(
                ship_idx["PR.Shipping.OrderToReceiveLeadTime"]
            )
            
            # 12) Origen y Destino de almacén desde Shipping
            df_final["OriginWarehouse"] = df_final["CodigoLocal"].map(
                ship_idx["PR.ShipFrom.InitiatorWarehouseName"]
            )
            df_final["DestinationWarehouse"] = df_final["CodigoLocal"].map(
                ship_idx["PR.ShipTo.RecipientWarehouseName"]
            )
            
            # 13) Stock Cover (ejemplo: días de cobertura) desde ShipTo
            if "PR.ShipTo.StockCoverDays" in df_shipto.columns:
                df_final["StockCoverDays"] = df_final["CodigoLocal"].map(
                    df_shipto.set_index("PR.ShipTo.ERPID")["PR.ShipTo.StockCoverDays"]
                )
            
            # 14) Vista previa y descarga
            st.subheader("🔍 Vista Previa Maestro Consolidado")
            st.dataframe(df_final.head(10))
            
            buffer = BytesIO()
            df_final.to_excel(buffer, index=False)
            buffer.seek(0)
            st.download_button(
                label="⬇️ Descargar Maestro_Consolidado.xlsx",
                data=buffer,
                file_name="Maestro_Consolidado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

st.markdown("---")
st.text("PR ANDINA • Generado con Streamlit")

