import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Maestro SKU Builder", layout="wide")
st.title("🛠️ Generador Automático de Maestro de Artículos")
st.write(
    "Sube tus archivos raw exportados de Product Cloud y tu Maestro actual "
    "para ver solo SKU, Descripción y Mercado."
)

# ----------------------------
# Subida de archivos
# ----------------------------
downloads = st.sidebar.file_uploader(
    "Archivos raw de Product Cloud (.xlsx)", 
    type=["xlsx"], 
    accept_multiple_files=True,
    help="ConsumerUnits, LogisticUnits (recipients), etc."
)
uploaded_master = st.sidebar.file_uploader(
    "Maestro Actual (.xlsx)", 
    type=["xlsx"], 
    key="master",
    help="Libro con la hoja 'Maestro' (encabezados en la fila 3)."
)

if st.sidebar.button("Generar Vista"):
    if not downloads or not uploaded_master:
        st.sidebar.error("❌ Primero sube todos los exports y tu Maestro.")
        st.stop()

    # 1) Leer Maestro detectando header real
    master_old = pd.read_excel(uploaded_master, sheet_name="Maestro", header=2)
    # 2) Detectar columna SKU
    sku_col = next((c for c in master_old.columns if "SKU" in str(c)), None)
    if sku_col is None:
        st.sidebar.error(
            "❌ No encontré la columna SKU. Columnas disponibles: " +
            ", ".join(master_old.columns.astype(str))
        )
        st.stop()

    # 3) Inicializar DataFrames
    logu = consu = None

    # 4) Leer cada export
    for f in downloads:
        n = f.name.lower()
        df = pd.read_excel(f, header=1)
        if "consumerunits" in n and "recipients" in n:
            consu = df
        elif "logisticunits" in n and "lu_recipients" in n:
            logu = df

    # 5) Verificar
    if logu is None or consu is None:
        faltan = []
        if logu is None: faltan.append("LogU")
        if consu is None: faltan.append("ConsU")
        st.sidebar.error(f"❌ Faltan: {', '.join(faltan)}")
        st.stop()

    # 6) Construir df_final con solo 3 columnas
    df_final = master_old[[sku_col]].copy()
    df_final.columns = ["CodigoLocal"]

    # 7) Descripción desde LogU
    df_final = df_final.merge(
        logu.set_index("PR.LogistU.ERPID")[["PR.LogistU.MyOwnPortfolio"]],
        left_on="CodigoLocal", right_index=True, how="left"
    ).rename(columns={"PR.LogistU.MyOwnPortfolio": "Descripcion"})

    # 8) Mercado desde ConsU
    df_final["Mercado"] = df_final["CodigoLocal"].map(
        consu.set_index("PR.ConsumU.ERPID")["PR.LiquiQual.CountryOfOrigin"]
    )

    # 9) Mostrar
    st.subheader("SKU | Descripción | Mercado")
    st.dataframe(df_final.head(20))

    # 10) Descargar (opcional)
    buffer = BytesIO()
    df_final.to_excel(buffer, index=False)
    buffer.seek(0)
    st.download_button(
        "⬇️ Descargar Vista",
        data=buffer,
        file_name="Vista_SKU_Desc_Mercado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.markdown("---")
st.text("PR ANDINA")


