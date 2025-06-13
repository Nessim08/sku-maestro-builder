import streamlit as st
import pandas as pd
from io import StringIO

# --- Configuración de la página ---
st.set_page_config(
    page_title="Generador SKU | Descripción | Mercado", 
    layout="wide"
)

st.title("🛠️ Generador Automático de Vista SKU | Descripción | Mercado")
st.write("Sube tu export **LogU** de Product Cloud para obtener una vista con SKU, Descripción y Mercado.")

# --- Uploader único para el raw export LogU ---
logu_file = st.file_uploader(
    "📂 Export LogU (.xlsx)", 
    type=["xlsx"],
    help="Sube el raw export de LogisticUnits (LU_Recipients)"
)

if logu_file:
    try:
        # Intentamos leer asumiendo que la fila 0 es el header
        logu_df = pd.read_excel(logu_file, sheet_name=0, header=0)
        
        # Columnas que vamos a extraer
        expected_cols = [
            "PR.LogistU.ERPID",
            "PR.LogistU.Description1#en-US",
            "PR.LogistU.MyOwnPortfolio"
        ]
        
        # Verificamos que estén todas
        missing = [c for c in expected_cols if c not in logu_df.columns]
        if missing:
            st.error(
                "❌ No pude encontrar las columnas necesarias en tu export LogU.\n\n"
                f"Faltan: **{', '.join(missing)}**\n\n"
                "Columnas disponibles:\n\n"
                + ", ".join(f"`{c}`" for c in logu_df.columns.tolist())
            )
        else:
            # Extraemos y renombramos
            vista = logu_df[expected_cols].rename(columns={
                "PR.LogistU.ERPID": "SKU",
                "PR.LogistU.Description1#en-US": "Descripción",
                "PR.LogistU.MyOwnPortfolio": "Mercado"
            })
            
            st.subheader("✅ Vista Generada")
            st.dataframe(vista)
            
            # Botón de descarga en CSV
            csv_buffer = StringIO()
            vista.to_csv(csv_buffer, index=False, sep=";")
            st.download_button(
                label="⬇️ Descargar CSV (SKU_Desc_Mercado.csv)",
                data=csv_buffer.getvalue(),
                file_name="SKU_Desc_Mercado.csv",
                mime="text/csv"
            )
    except Exception as e:
        st.error(f"❌ Ocurrió un error leyendo el archivo: `{e}`")


