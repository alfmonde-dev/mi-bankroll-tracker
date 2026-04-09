import streamlit as st
import pandas as pd
import os
import datetime
import plotly.graph_objects as go

ARCHIVO_DATOS = 'mis_apuestas.csv'

# --- INICIALIZAR VARIABLES DE ESTADO ---
if 'confirmar_borrado' not in st.session_state:
    st.session_state.confirmar_borrado = None

# --- FUNCIONES DE DATOS ---
def cargar_datos():
    if os.path.exists(ARCHIVO_DATOS):
        try:
            # Blindaje contra cabeceras repetidas y errores de formato
            df = pd.read_csv(ARCHIVO_DATOS)
            df = df[df['Fecha'] != 'Fecha'] 
            df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce').dt.date
            df = df.dropna(subset=['Fecha'])
            
            if 'Casa' not in df.columns:
                df['Casa'] = "N/A"
            return df
        except Exception:
            return pd.DataFrame(columns=['ID', 'Fecha', 'Evento', 'Casa', 'Cuota', 'Inversion', 'Estado', 'Retorno'])
    else:
        return pd.DataFrame(columns=['ID', 'Fecha', 'Evento', 'Casa', 'Cuota', 'Inversion', 'Estado', 'Retorno'])

def guardar_datos(df):
    df.to_csv(ARCHIVO_DATOS, index=False)

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Mi Gestor de Apuestas", layout="wide")
st.title("📊 Mi Bankroll Tracker Pro")

df = cargar_datos()

col_izq, col_der = st.columns([1, 1.5])

with col_izq:
    st.header("1. Añadir Apuesta")
    with st.form("form_nueva_apuesta", clear_on_submit=True):
        fecha_apuesta = st.date_input("Fecha de la apuesta", datetime.date.today())
        evento = st.text_input("Partido / Evento")
        casa = st.text_input("Casa de Apuestas (ej: Bet365, Winamax)")
        
        c1, c2 = st.columns(2)
        cuota = c1.number_input("Cuota", min_value=1.01, step=0.01, format="%.2f")
        inversion = c2.number_input("Inversión (€)", min_value=0.1, step=1.0)
        
        submit_apuesta = st.form_submit_button("Registrar Apuesta")

        if submit_apuesta and evento:
            nuevo_id = 1 if len(df) == 0 else int(df['ID'].max()) + 1
            nueva_fila = {
                'ID': nuevo_id, 'Fecha': fecha_apuesta, 'Evento': evento,
                'Casa': casa if casa else "N/A",
                'Cuota': cuota, 'Inversion': inversion, 'Estado': 'Pendiente', 'Retorno': 0.0
            }
            df = pd.concat([df, pd.DataFrame([nueva_fila])], ignore_index=True)
            guardar_datos(df)
            st.success(f"Apuesta en {casa if casa else 'N/A'} registrada.")
            st.rerun()

    st.divider()
    st.header("2. Cerrar Apuesta")
    pendientes = df[df['Estado'] == 'Pendiente']

    if not pendientes.empty:
        opcion = st.selectbox("Selecciona pendiente:", pendientes['ID'].astype(str) + " - " + pendientes['Evento'])
        id_sel = int(opcion.split(" - ")[0])
        apuesta_act = df[df['ID'].astype(int) == id_sel].iloc[0]

        with st.form("form_resolver"):
            nuevo_estado = st.radio("Resultado:", ['Ganada', 'Perdida', 'Cashout'], horizontal=True)
            valor_cierre = st.number_input("¿Cuánto cobraste? (€)", min_value=0.0, step=0.1)
                
            if st.form_submit_button("Confirmar Resultado"):
                retorno_final = 0.0
                if nuevo_estado == 'Ganada':
                    retorno_final = apuesta_act['Inversion'] * apuesta_act['Cuota']
                elif nuevo_estado == 'Cashout':
                    retorno_final = valor_cierre
                    
                df.loc[df['ID'].astype(int) == id_sel, 'Estado'] = nuevo_estado
                df.loc[df['ID'].astype(int) == id_sel, 'Retorno'] = retorno_final
                guardar_datos(df)
                st.rerun()
    else:
        st.info("No hay apuestas pendientes.")

with col_der:
    st.header("3. Análisis de Beneficios")
    resueltas = df[df['Estado'].isin(['Ganada', 'Perdida', 'Cashout'])].copy()

    if not resueltas.empty:
        resueltas['Beneficio_Neto'] = pd.to_numeric(resueltas['Retorno']) - pd.to_numeric(resueltas['Inversion'])
        resueltas['Fecha'] = pd.to_datetime(resueltas['Fecha'])
        
        filtro_tiempo = st.radio("Ver datos de:", ['Todo', 'Hoy', 'Esta Semana', 'Este Mes', 'Este Año'], horizontal=True)
        
        hoy = pd.Timestamp(datetime.date.today())
        if filtro_tiempo == 'Hoy':
            resueltas = resueltas[resueltas['Fecha'].dt.date == hoy.date()]
        elif filtro_tiempo == 'Esta Semana':
            inicio_semana = hoy - pd.Timedelta(days=hoy.weekday())
            resueltas = resueltas[resueltas['Fecha'] >= inicio_semana]
        elif filtro_tiempo == 'Este Mes':
            resueltas = resueltas[(resueltas['Fecha'].dt.month == hoy.month) & (resueltas['Fecha'].dt.year == hoy.year)]
        elif filtro_tiempo == 'Este Año':
            resueltas = resueltas[resueltas['Fecha'].dt.year == hoy.year]

        resueltas = resueltas.sort_values(['Fecha', 'ID']) 

        if not resueltas.empty:
            # Preparar datos
            datos_grafica = resueltas.copy()
            datos_grafica['Eje_X'] = range(1, len(datos_grafica) + 1) 
            datos_grafica['Acumulado'] = datos_grafica['Beneficio_Neto'].cumsum()

            # Empezar en 0 y curvar
            x_vals = [0] + list(datos_grafica['Eje_X'])
            y_vals = [0.0] + list(datos_grafica['Acumulado'])

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=x_vals, 
                y=y_vals,
                mode='lines+markers', 
                line=dict(color='#2ad29a', width=3, shape='spline', smoothing=1.3),
                fill='tozeroy', 
                fillcolor='rgba(42, 210, 154, 0.1)'
            ))
            
            # Gráfica bloqueada para evitar zoom accidental
            fig.update_layout(
                template="plotly_dark", 
                height=350, 
                margin=dict(l=0,r=0,t=20,b=0),
                xaxis=dict(fixedrange=True), 
                yaxis=dict(fixedrange=True), 
                dragmode=False 
            )
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

            # --- MÉTRICAS ---
            m1, m2, m3 = st.columns(3)
            m1.metric("Beneficio Periodo", f"{resueltas['Beneficio_Neto'].sum():.2f} €")
            m2.metric("Nº Apuestas", f"{len(resueltas)}")
            m3.metric("Yield Periodo %", f"{(resueltas['Beneficio_Neto'].sum() / resueltas['Inversion'].sum() * 100) if resueltas['Inversion'].sum() > 0 else 0:.1f} %")

            # --- HISTORIAL COLOREADO ---
            st.subheader("Historial del Periodo")
            df_hist = resueltas[['ID', 'Fecha', 'Evento', 'Casa', 'Estado', 'Inversion', 'Beneficio_Neto']].sort_values(['Fecha', 'ID'], ascending=[False, False])
            
            def p_estado(val):
                color = '#2ad29a' if val == 'Ganada' else '#ff4b4b' if val == 'Perdida' else '#faca2b'
                return f'color: {color}; font-weight: bold;'

            def p_beneficio(val):
                color = '#2ad29a' if val > 0 else '#ff4b4b' if val < 0 else 'white'
                return f'color: {color}; font-weight: bold;'

            st.dataframe(
                df_hist.style
                .map(p_estado, subset=['Estado'])
                .map(p_beneficio, subset=['Beneficio_Neto'])
                .format({'Fecha': lambda x: x.strftime('%Y-%m-%d'), 'Inversion': "{:.2f} €", 'Beneficio_Neto': "{:.2f} €"}),
                use_container_width=True, hide_index=True
            )
        else:
            st.info("No hay datos cerrados en este periodo.")

        # --- SISTEMA DE BORRADO ---
        st.divider()
        st.markdown("🗑️ **Eliminar apuesta del sistema**")
        cd1, cd2 = st.columns([3, 1])
        with cd1:
            opciones_borrar = df['ID'].astype(str) + " - " + df['Evento']
            apuesta_borrar_str = st.selectbox("Selecciona para borrar:", opciones_borrar, label_visibility="collapsed")
        with cd2:
            if st.button("🗑️ Eliminar", use_container_width=True):
                st.session_state.confirmar_borrado = int(apuesta_borrar_str.split(" - ")[0])
                st.rerun()

        if st.session_state.confirmar_borrado is not None:
            st.error(f"⚠️ **¿Confirmas borrar el ID {st.session_state.confirmar_borrado}?**")
            c_si, c_no = st.columns(2)
            if c_si.button("✅ Sí"):
                df = df[df['ID'].astype(int) != st.session_state.confirmar_borrado]
                guardar_datos(df)
                st.session_state.confirmar_borrado = None
                st.rerun()
            if c_no.button("❌ No"):
                st.session_state.confirmar_borrado = None
                st.rerun()
    else:
        st.warning("Añade y cierra alguna apuesta.")
