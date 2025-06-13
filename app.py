import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Maestro SKU Builder", layout="wide")
st.title("🛠️ Generador Automático de Maestro de Artículos")
st.write(
    "Sube tus archivos raw exportados de Product Cloud y tu Maestro actual "
    "para obtener la tabla consolidada sin usar pivot tables."
)

# ----------------------------
# Subida de archivos
# ----------------------------
downloads = st.sidebar.file_uploader(
    "Archivos raw de Product Cloud (.xlsx)", 
    type=["xlsx"], 
    accept_multiple_files=True,
    help="Sube los exports: ConsumerUnits, LogisticUnits (recipients, shipfrom), Shipping y ShipTo."
)
uploaded_master = st.sidebar.file_uploader(
    "Maestro Actual (.xlsx)", 
    type=["xlsx"], 
    key="master",
    help="Tu libro de Excel con la hoja 'Maestro' (incluye encabezados en la fila 3)."
)

if st.sidebar.button("Generar Maestro Consolidado"):
    if not downloads or not uploaded_master:
        st.sidebar.error("❌ Primero sube todos los exports y luego tu archivo Maestro.")
        st.stop()

    # --- 1) Leer el Maestro actual detectando el header ---
    try:
        master_old = pd.read_excel(uploaded_master, sheet_name="Maestro", header=2)
    except Exception as e:
        st.sidebar.error(f"❌ Error leyendo el Maestro: {e}")
        st.stop()

    # --- 2) Detectar columna de SKU local ---
    sku_col = next((c for c in master_old.columns if "SKU" in str(c)), None)
    if sku_col is None:
        st.sidebar.error(
            "❌ No pude encontrar la columna de SKU en tu Maestro. "
            f"Columnas disponibles: {', '.join(master_old.columns.astype(str))}"
        )
        st.stop()

    # --- 3) Inicializar DataFrames fuente ---
    consu = logu = shipping = shipto = None

    # --- 4) Leer cada export raw ---
    for file in downloads:
        name = file.name.lower()
        df = pd.read_excel(file, header=1)  # header=1 si tus raw tienen encabezado en segunda fila
        if "consumerunits" in name and "recipients" in name:
            consu = df
        elif "logisticunits" in name and "lu_recipients" in name:
            logu = df
        elif "logisticunits" in name and "shipfrom" in name:
            shipfrom = df
        elif "logisticunits" in name and "shipping" in name:
            shipping = df
        elif "logisticunits" in name and "shipto" in name:
            shipto = df

    # --- 5) Verificar fuentes ---
    missing = [lbl for lbl, df in {"ConsU": consu, "LogU": logu, "ShipFrom": shipfrom, "Shipping": shipping, "ShipTo": shipto}.items() if df is None]
    if missing:
        st.sidebar.error(f"❌ Faltan las fuentes raw: {', '.join(missing)}")
        st.stop()

    # --- 6) Construir df_final con la lista de SKUs del Maestro ---
    df_final = master_old[[sku_col]].copy()
    df_final.columns = ["CodigoLocal"]

    # --- 7) Descripción desde LogU ---
    df_final = df_final.merge(
        logu.set_index("PR.LogistU.ERPID")[["PR.LogistU.MyOwnPortfolio"]],
        left_on="CodigoLocal", right_index=True, how="left"
    ).rename(columns={"PR.LogistU.MyOwnPortfolio": "Descripcion"})

    # --- 8) Mercado desde ConsU ---
    df_final["Mercado"] = df_final["CodigoLocal"].map(
        consu.set_index("PR.ConsumU.ERPID")["PR.LiquiQual.CountryOfOrigin"]
    )

    # --- 9) ABC (constante) ---
    df_final["ABC"] = 0

    # --- 10) Pack Size (NumberOfConsumerUnit) ---
    df_final["Pack Size (UxC)"] = df_final["CodigoLocal"].map(
        logu.set_index("PR.LogistU.ERPID")["PR.LogistU.NumberOfConsumerUnit"]
    )

    # --- 11) Bottle size (TotalBeverageVolume) ---
    df_final["Bottle size"] = df_final["CodigoLocal"].map(
        logu.set_index("PR.LogistU.ERPID")["PR.LogistU.TotalBeverageVolume"]
    )

    # --- 12) Lead Times desde Shipping ---
    ship_idx = shipping.set_index("PR.LogistU.ERPID")
    df_final["DispatchToReceiveLeadTime"] = df_final["CodigoLocal"].map(
        ship_idx["PR.Shipping.DispatchToReceiveLeadTime"]
    )
    df_final["OrderToReceiveLeadTime"] = df_final["CodigoLocal"].map(
        ship_idx["PR.Shipping.OrderToReceiveLeadTime"]
    )

    # --- 13) Origin & Destination Warehouses desde ShipTo y ShipFrom ---
    df_final["OriginWarehouse"] = df_final["CodigoLocal"].map(
        shipfrom.set_index("PR.LogistU.ERPID")["PR.ShipFrom.InitiatorWarehouseName"]
    )
    df_final["DestinationWarehouse"] = df_final["CodigoLocal"].map(
        shipto.set_index("PR.LogistU.ERPID")["PR.ShipTo.RecipientWarehouseName"]
    )

    # ... agrega aquí las columnas adicionales que necesites con más .map(...) ...

    # --- 14) Mostrar y permitir descarga ---
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
st.text("PR ANDINA")


