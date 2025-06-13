import streamlit as st
import pandas as pd
from io import BytesIO

# --- Configuración de la página ---
st.set_page_config(page_title="Maestro SKU Builder", layout="wide")
st.title("🛠️ Generador Automático de Maestro de Artículos")
st.write(
    "Sube tus archivos raw exportados de Product Cloud y tu Maestro actual "
    "para obtener la tabla consolidada sin usar pivot tables."
)

# --- Sidebar: subida de archivos ---
downloads = st.sidebar.file_uploader(
    "Archivos raw de Product Cloud (.xlsx)",
    type=["xlsx"],
    accept_multiple_files=True,
    help="Sube los exports de ConsumerUnits, LogisticUnits (recipients), "
         "LogisticUnits (shipping) y/o ShipTo."
)
uploaded_master = st.sidebar.file_uploader(
    "Maestro Actual (.xlsx)",
    type=["xlsx"],
    key="master",
    help="Tu libro de Excel con la hoja 'Maestro' que contiene el listado de SKUs."
)

if st.sidebar.button("Generar Maestro Consolidado"):
    # 1) Validar subida
    if not downloads or not uploaded_master:
        st.sidebar.error("❌ Primero sube los archivos raw y luego tu Maestro actual.")
        st.stop()

    # 2) Lectura del maestro
    try:
        all_sheets = pd.read_excel(uploaded_master, sheet_name=None)
    except Exception as e:
        st.sidebar.error(f"❌ No pude leer tu Maestro: {e}")
        st.stop()

    # Intentamos hoja "Maestro" o la única si solo hay una
    if "Maestro" in all_sheets:
        master_df = all_sheets["Maestro"]
    elif len(all_sheets) == 1:
        master_df = list(all_sheets.values())[0]
    else:
        st.sidebar.error(
            "❌ No encontré hoja 'Maestro'. Hojas disponibles: "
            f"{', '.join(all_sheets.keys())}"
        )
        st.stop()

    # Limpiar nombres de columnas (quitar saltos de línea y espacios)
    master_df.columns = (
        master_df.columns
        .astype(str)
        .str.replace("\n", " ", regex=False)
        .str.strip()
    )

    # Detectar columna de SKU en el maestro
    sku_cols = [
        col for col in master_df.columns
        if "SKU" in col.upper() and "CÓDIGO" in col.upper()
    ]
    if not sku_cols:
        st.sidebar.error(
            "❌ No pude encontrar la columna de SKU en tu Maestro. "
            f"Columnas disponibles: {', '.join(master_df.columns)}"
        )
        st.stop()
    sku_col = sku_cols[0]

    # Construir df_final con la lista de SKUs
    df_final = master_df[[sku_col]].copy()
    df_final.rename(columns={sku_col: "CodigoLocal"}, inplace=True)

    # 3) Leer y detectar cada export raw
    logu = consu = shipping = None
    for f in downloads:
        name = f.name.lower()
        # todos los exports tienen su header en la fila 2 (index=1)
        df = pd.read_excel(f, header=1)
        # limpiar columnas
        df.columns = df.columns.astype(str).str.strip()

        if "consumerunits" in name or "cu_recipients" in name:
            consu = df
        elif "logisticunits" in name and "shipping" not in name:
            logu = df
        elif "shipping" in name:
            shipping = df
        # si tuvieras un shipto separado, podrías capturarlo aquí:
        # elif "shipto" in name:
        #     shipto = df

    missing = [
        label for label, df in 
        {"LogU": logu, "ConsU": consu, "Shipping": shipping}.items()
        if df is None
    ]
    if missing:
        st.sidebar.error(f"❌ Faltan las fuentes: {', '.join(missing)}")
        st.stop()

    # 4) Merge de datos
    # 4.1 Descripción desde LogU
    df_final = df_final.merge(
        logu[["PR.LogistU.ERPID", "PR.LogistU.MyOwnPortfolio"]],
        left_on="CodigoLocal", right_on="PR.LogistU.ERPID",
        how="left"
    ).rename(columns={"PR.LogistU.MyOwnPortfolio": "Descripcion"})

    # 4.2 Mercado desde ConsU
    df_final["Mercado"] = df_final["CodigoLocal"].map(
        consu.set_index("PR.ConsumU.ERPID")["PR.LiquiQual.CountryOfOrigin"]
    )

    # 4.3 ABC (constante 0)
    df_final["ABC"] = 0

    # 4.4 Pack Size (NumberOfConsumerUnit)
    df_final["Pack Size (UxC)"] = df_final["CodigoLocal"].map(
        logu.set_index("PR.LogistU.ERPID")["PR.LogistU.NumberOfConsumerUnit"]
    )

    # 4.5 Lead Times desde Shipping
    ship_idx = shipping.set_index("PR.LogistU.ERPID")
    df_final["DispatchToReceiveLeadTime"] = df_final["CodigoLocal"].map(
        ship_idx["PR.Shipping.DispatchToReceiveLeadTime"]
    )
    df_final["OrderToReceiveLeadTime"] = df_final["CodigoLocal"].map(
        ship_idx["PR.Shipping.OrderToReceiveLeadTime"]
    )

    # 4.6 Origin & Destination Warehouses
    df_final["OriginWarehouse"] = df_final["CodigoLocal"].map(
        ship_idx["PR.ShipFrom.InitiatorWarehouseName"]
    )
    df_final["DestinationWarehouse"] = df_final["CodigoLocal"].map(
        ship_idx["PR.ShipTo.RecipientWarehouseName"]
    )

    # ... aquí puedes seguir agregando más columnas como necesites ...

    # 5) Mostrar y ofrecer descarga
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


