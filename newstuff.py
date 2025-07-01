# newstuff.py

import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta
import json
import os

# Configuración avanzada
CONFIG_AVANZADA_FILE = "config_avanzada.json"

# Cargar configuración avanzada o crear por defecto
def cargar_config_avanzada():
    if os.path.exists(CONFIG_AVANZADA_FILE):
        with open(CONFIG_AVANZADA_FILE, "r") as f:
            return json.load(f)
    else:
        # Configuración por defecto
        config_default = {
            "filtros": {
                "volumen_minimo": 0,
                "confirmacion_patrones": True,
                "tolerancia_patrones": 0.03,
                "min_velas_patron": 3
            },
            "indicadores": {
                "usar_bollinger": False,
                "usar_fibonacci": False,
                "usar_ichimoku": False,
                "usar_atr": False
            },
            "alertas": {
                "nivel_fiabilidad": "medio",  # bajo, medio, alto
                "mostrar_probabilidad": True
            },
            "patrones_vela": {
                "doji": True,
                "morning_star": True,
                "evening_star": True,
                "harami": True,
                "shooting_star": True
            },
            "rendimiento": {
                "analisis_paralelo": False,
                "max_pares_simultaneos": 10
            }
        }
        with open(CONFIG_AVANZADA_FILE, "w") as f:
            json.dump(config_default, f, indent=2)
        return config_default

# Guardar configuración avanzada
def guardar_config_avanzada(config):
    with open(CONFIG_AVANZADA_FILE, "w") as f:
        json.dump(config, f, indent=2)

# Función para mostrar la sección de configuración avanzada
def mostrar_configuracion_avanzada():
    config = cargar_config_avanzada()

    st.markdown("### ⚙️ Configuración Avanzada")

    with st.expander("Filtros de Patrones"):
        col1, col2 = st.columns(2)
        with col1:
            config["filtros"]["volumen_minimo"] = st.number_input(
                "Volumen mínimo (BTC)",
                min_value=0.0,
                value=float(config["filtros"]["volumen_minimo"]),
                step=0.1
            )
            config["filtros"]["tolerancia_patrones"] = st.slider(
                "Tolerancia de patrones (%)",
                min_value=0.5,
                max_value=10.0,
                value=float(config["filtros"]["tolerancia_patrones"] * 100),
                step=0.5
            ) / 100
        with col2:
            config["filtros"]["confirmacion_patrones"] = st.checkbox(
                "Requerir confirmación de patrones",
                value=config["filtros"]["confirmacion_patrones"]
            )
            config["filtros"]["min_velas_patron"] = st.number_input(
                "Mínimo de velas para patrón",
                min_value=2,
                max_value=10,
                value=int(config["filtros"]["min_velas_patron"])
            )

    with st.expander("Indicadores Adicionales"):
        col1, col2 = st.columns(2)
        with col1:
            config["indicadores"]["usar_bollinger"] = st.checkbox(
                "Bandas de Bollinger",
                value=config["indicadores"]["usar_bollinger"]
            )
            config["indicadores"]["usar_fibonacci"] = st.checkbox(
                "Retrocesos de Fibonacci",
                value=config["indicadores"]["usar_fibonacci"]
            )
        with col2:
            config["indicadores"]["usar_ichimoku"] = st.checkbox(
                "Ichimoku Cloud",
                value=config["indicadores"]["usar_ichimoku"]
            )
            config["indicadores"]["usar_atr"] = st.checkbox(
                "ATR (Average True Range)",
                value=config["indicadores"]["usar_atr"]
            )

    with st.expander("Configuración de Alertas"):
        config["alertas"]["nivel_fiabilidad"] = st.select_slider(
            "Nivel de fiabilidad requerido",
            options=["bajo", "medio", "alto"],
            value=config["alertas"]["nivel_fiabilidad"]
        )
        config["alertas"]["mostrar_probabilidad"] = st.checkbox(
            "Mostrar probabilidad en alertas",
            value=config["alertas"]["mostrar_probabilidad"]
        )

    with st.expander("Patrones de Vela Adicionales"):
        col1, col2 = st.columns(2)
        with col1:
            config["patrones_vela"]["doji"] = st.checkbox(
                "Doji",
                value=config["patrones_vela"]["doji"]
            )
            config["patrones_vela"]["morning_star"] = st.checkbox(
                "Morning Star",
                value=config["patrones_vela"]["morning_star"]
            )
            config["patrones_vela"]["harami"] = st.checkbox(
                "Harami",
                value=config["patrones_vela"]["harami"]
            )
        with col2:
            config["patrones_vela"]["evening_star"] = st.checkbox(
                "Evening Star",
                value=config["patrones_vela"]["evening_star"]
            )
            config["patrones_vela"]["shooting_star"] = st.checkbox(
                "Shooting Star",
                value=config["patrones_vela"]["shooting_star"]
            )

    with st.expander("Optimización de Rendimiento"):
        config["rendimiento"]["analisis_paralelo"] = st.checkbox(
            "Análisis en paralelo (experimental)",
            value=config["rendimiento"]["analisis_paralelo"]
        )
        if config["rendimiento"]["analisis_paralelo"]:
            config["rendimiento"]["max_pares_simultaneos"] = st.slider(
                "Máximo de pares simultáneos",
                min_value=5,
                max_value=50,
                value=int(config["rendimiento"]["max_pares_simultaneos"])
            )

    if st.button("Guardar Configuración Avanzada"):
        guardar_config_avanzada(config)
        st.success("✅ Configuración guardada correctamente")

    return config

# Función para calcular indicadores adicionales
def calcular_indicadores_adicionales(df, config):
    # Bandas de Bollinger
    if config["indicadores"]["usar_bollinger"]:
        bollinger = ta.bbands(df['close'], length=20, std=2)
        df['bb_upper'] = bollinger['BBU_20_2.0']
        df['bb_middle'] = bollinger['BBM_20_2.0']
        df['bb_lower'] = bollinger['BBL_20_2.0']

    # ATR (Average True Range)
    if config["indicadores"]["usar_atr"]:
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)

    # Ichimoku Cloud
    if config["indicadores"]["usar_ichimoku"]:
        ichimoku = ta.ichimoku(df['high'], df['low'], df['close'])
        df['tenkan'] = ichimoku['ITS_9']
        df['kijun'] = ichimoku['IKS_26']
        df['senkou_a'] = ichimoku['ISA_9_26']
        df['senkou_b'] = ichimoku['ISB_9_26']

    # Fibonacci no se calcula como columna, se usa en el análisis

    return df

# Función para detectar patrones de vela adicionales
def detectar_patrones_vela(df, config):
    patrones_detectados = {}

    if config["patrones_vela"]["doji"]:
        df['doji'] = ta.cdl_pattern(df['open'], df['high'], df['low'], df['close'], name='doji')
        patrones_detectados['doji'] = df['doji'].iloc[-1] != 0

    if config["patrones_vela"]["morning_star"]:
        df['morning_star'] = ta.cdl_pattern(df['open'], df['high'], df['low'], df['close'], name='morningstar')
        patrones_detectados['morning_star'] = df['morning_star'].iloc[-1] != 0

    if config["patrones_vela"]["evening_star"]:
        df['evening_star'] = ta.cdl_pattern(df['open'], df['high'], df['low'], df['close'], name='eveningstar')
        patrones_detectados['evening_star'] = df['evening_star'].iloc[-1] != 0

    if config["patrones_vela"]["harami"]:
        df['harami'] = ta.cdl_pattern(df['open'], df['high'], df['low'], df['close'], name='harami')
        patrones_detectados['harami'] = df['harami'].iloc[-1] != 0

    if config["patrones_vela"]["shooting_star"]:
        df['shooting_star'] = ta.cdl_pattern(df['open'], df['high'], df['low'], df['close'], name='shootingstar')
        patrones_detectados['shooting_star'] = df['shooting_star'].iloc[-1] != 0

    return df, patrones_detectados

# Función mejorada para detectar doble/triple suelo con mayor tolerancia
def detectar_doble_triple_suelo_mejorado(df, config, ventana=20):
    tolerancia = config["filtros"]["tolerancia_patrones"]
    min_velas = config["filtros"]["min_velas_patron"]

    suelos = []
    precios = df['close'].tail(ventana).values
    idxs = df['close'].tail(ventana).index
    fechas = df['timestamp'].tail(ventana).values
    volumenes = df['volume'].tail(ventana).values if 'volume' in df.columns else None

    # Detectar mínimos locales
    for i in range(min_velas, len(precios)-min_velas):
        # Verificar si es un mínimo local en una ventana de min_velas
        es_minimo = True
        for j in range(1, min_velas+1):
            if precios[i] > precios[i-j] or precios[i] > precios[i+j]:
                es_minimo = False
                break

        if es_minimo:
            # Verificar volumen mínimo si está configurado
            if volumenes is not None and config["filtros"]["volumen_minimo"] > 0:
                if volumenes[i] < config["filtros"]["volumen_minimo"]:
                    continue

            suelos.append((idxs[i], precios[i], fechas[i]))

    # Buscar patrones de doble y triple suelo
    doble = False
    triple = False
    idx_doble = None
    idx_triple = None
    fechas_doble = None
    fechas_triple = None
    fiabilidad_doble = 0
    fiabilidad_triple = 0

    if len(suelos) >= 2:
        for i in range(len(suelos)-1):
            p1 = suelos[i][1]
            p2 = suelos[i+1][1]

            # Calcular diferencia porcentual
            diferencia = abs(p1 - p2) / p1

            if diferencia < tolerancia:
                doble = True
                idx_doble = (suelos[i][0], suelos[i+1][0])
                fechas_doble = (suelos[i][2], suelos[i+1][2])

                # Calcular fiabilidad (menor diferencia = mayor fiabilidad)
                fiabilidad_doble = 1.0 - (diferencia / tolerancia)

                # Buscar triple suelo
                if i+2 < len(suelos):
                    p3 = suelos[i+2][1]
                    dif1_3 = abs(p1 - p3) / p1
                    dif2_3 = abs(p2 - p3) / p2

                    if dif1_3 < tolerancia and dif2_3 < tolerancia:
                        triple = True
                        idx_triple = (suelos[i][0], suelos[i+1][0], suelos[i+2][0])
                        fechas_triple = (suelos[i][2], suelos[i+1][2], suelos[i+2][2])

                        # Calcular fiabilidad para triple suelo
                        fiabilidad_triple = 1.0 - ((dif1_3 + dif2_3 + diferencia) / (3 * tolerancia))
                        break

    return {
        'doble': doble,
        'triple': triple,
        'idx_doble': idx_doble if doble else None,
        'idx_triple': idx_triple if triple else None,
        'fechas_doble': fechas_doble if doble else None,
        'fechas_triple': fechas_triple if triple else None,
        'suelos': suelos,
        'fiabilidad_doble': fiabilidad_doble,
        'fiabilidad_triple': fiabilidad_triple
    }

# Función para calcular niveles de Fibonacci
def calcular_fibonacci(df, tendencia='alcista'):
    if tendencia == 'alcista':
        # Para tendencia alcista, calculamos desde mínimo a máximo
        precio_min = df['low'].min()
        precio_max = df['high'].max()
    else:
        # Para tendencia bajista, calculamos desde máximo a mínimo
        precio_min = df['high'].max()
        precio_max = df['low'].min()

    # Niveles de Fibonacci estándar
    rango = abs(precio_max - precio_min)
    niveles = {
        '0.0': precio_min,
        '0.236': precio_min + 0.236 * rango,
        '0.382': precio_min + 0.382 * rango,
        '0.5': precio_min + 0.5 * rango,
        '0.618': precio_min + 0.618 * rango,
        '0.786': precio_min + 0.786 * rango,
        '1.0': precio_max
    }

    return niveles

# Función para evaluar la fiabilidad de una señal
def evaluar_fiabilidad_senal(df, tipo_senal, patrones_vela, config):
    fiabilidad = 0.5  # Fiabilidad base

    # Factores que aumentan la fiabilidad
    if tipo_senal == 'doble_suelo' or tipo_senal == 'triple_suelo':
        # Mayor fiabilidad para triple suelo que para doble
        fiabilidad = 0.6 if tipo_senal == 'doble_suelo' else 0.7

        # Verificar confirmación con volumen
        if 'volume' in df.columns:
            ultimo_volumen = df['volume'].iloc[-1]
            promedio_volumen = df['volume'].tail(10).mean()
            if ultimo_volumen > promedio_volumen * 1.5:
                fiabilidad += 0.1

        # Verificar RSI en zona de sobreventa
        if 'rsi' in df.columns and df['rsi'].iloc[-1] < 30:
            fiabilidad += 0.1

        # Verificar si hay patrones de vela confirmatorios
        patrones_alcistas = ['hammer', 'morning_star', 'harami']
        for patron in patrones_alcistas:
            if patron in patrones_vela and patrones_vela[patron]:
                fiabilidad += 0.05

    elif tipo_senal == 'divergencia_alcista':
        # Verificar fuerza de la divergencia
        if 'rsi' in df.columns:
            rsi_actual = df['rsi'].iloc[-1]
            if rsi_actual < 30:
                fiabilidad += 0.15
            elif rsi_actual < 40:
                fiabilidad += 0.1

        # Verificar si hay patrones de vela confirmatorios
        if any(patrones_vela.values()):
            fiabilidad += 0.1

    # Limitar la fiabilidad entre 0 y 1
    fiabilidad = min(max(fiabilidad, 0), 1)

    # Convertir a nivel cualitativo
    if fiabilidad >= 0.7:
        nivel = "alto"
    elif fiabilidad >= 0.5:
        nivel = "medio"
    else:
        nivel = "bajo"

    return {
        'valor': fiabilidad,
        'nivel': nivel,
        'porcentaje': int(fiabilidad * 100)
    }

# Función para añadir indicadores al gráfico
def añadir_indicadores_al_grafico(fig, df, config):
    if config["indicadores"]["usar_bollinger"] and 'bb_upper' in df.columns:
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['bb_upper'],
            mode='lines',
            name='BB Superior',
            line=dict(color='rgba(250, 128, 114, 0.7)', width=1, dash='dot')
        ))
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['bb_middle'],
            mode='lines',
            name='BB Media',
            line=dict(color='rgba(128, 128, 128, 0.7)', width=1, dash='dot')
        ))
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['bb_lower'],
            mode='lines',
            name='BB Inferior',
            line=dict(color='rgba(144, 238, 144, 0.7)', width=1, dash='dot')
        ))

    if config["indicadores"]["usar_ichimoku"] and 'tenkan' in df.columns:
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['tenkan'],
            mode='lines',
            name='Tenkan-sen',
            line=dict(color='red', width=1)
        ))
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['kijun'],
            mode='lines',
            name='Kijun-sen',
            line=dict(color='blue', width=1)
        ))

        # Crear área sombreada para Kumo (nube)
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['senkou_a'],
            mode='lines',
            name='Senkou Span A',
            line=dict(color='rgba(119, 152, 191, 0.5)', width=0.5)
        ))
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['senkou_b'],
            mode='lines',
            name='Senkou Span B',
            line=dict(color='rgba(119, 152, 191, 0.5)', width=0.5),
            fill='tonexty',
            fillcolor='rgba(119, 152, 191, 0.2)'
        ))

    if config["indicadores"]["usar_fibonacci"] and len(df) > 10:
        niveles = calcular_fibonacci(df)
        for nivel, valor in niveles.items():
            fig.add_shape(
                type="line",
                x0=df['timestamp'].iloc[0],
                x1=df['timestamp'].iloc[-1],
                y0=valor,
                y1=valor,
                line=dict(color="purple", width=1, dash="dash"),
                name=f"Fib {nivel}"
            )
            fig.add_annotation(
                x=df['timestamp'].iloc[-1],
                y=valor,
                text=f"Fib {nivel}",
                showarrow=False,
                xshift=10,
                font=dict(size=8, color="purple")
            )

    return fig

# Función para generar mensaje de alerta con nivel de fiabilidad
def generar_mensaje_alerta(symbol, tipo, precio, fiabilidad, timeframe, patrones_vela):
    # Emojis según nivel de fiabilidad
    emoji_fiabilidad = "⚠️" if fiabilidad['nivel'] == "bajo" else "✅" if fiabilidad['nivel'] == "alto" else "ℹ️"

    # Emojis según tipo de señal
    emoji_tipo = {
        "DOBLE SUELO": "🔵",
        "TRIPLE SUELO": "🟣",
        "DIVERGENCIA ALCISTA": "📈",
        "DIVERGENCIA BAJISTA": "📉",
        "CAMBIO DE TENDENCIA ALCISTA": "🚀"
    }.get(tipo, "🔍")

    mensaje = (
        f"{emoji_tipo} {tipo} DETECTADO\n"
        f"Par: {symbol}\n"
        f"Temporalidad: {timeframe}\n"
        f"Precio actual: {precio:.8f}\n"
        f"{emoji_fiabilidad} Fiabilidad: {fiabilidad['porcentaje']}% ({fiabilidad['nivel']})\n"
    )

    # Añadir patrones de vela confirmatorios si existen
    patrones_presentes = [k for k, v in patrones_vela.items() if v]
    if patrones_presentes:
        mensaje += f"Patrones confirmatorios: {', '.join(patrones_presentes)}\n"

    return mensaje

# Función principal que integra todas las mejoras
def aplicar_mejoras(st_obj, df, exchange, symbols, historial_alertas, config_suelos):
    # Mostrar configuración avanzada en la barra lateral
    with st_obj.sidebar:
        st_obj.sidebar.markdown("---")
        config_avanzada = mostrar_configuracion_avanzada()

    # Si estamos analizando un par específico
    if df is not None:
        # Calcular indicadores adicionales
        df = calcular_indicadores_adicionales(df, config_avanzada)

        # Detectar patrones de vela adicionales
        df, patrones_vela = detectar_patrones_vela(df, config_avanzada)

        # Detectar patrones de suelo con tolerancia mejorada
        patrones_suelo = detectar_doble_triple_suelo_mejorado(df, config_avanzada)

        # Evaluar fiabilidad de las señales
        fiabilidad_doble_suelo = evaluar_fiabilidad_senal(df, 'doble_suelo', patrones_vela, config_avanzada)
        fiabilidad_triple_suelo = evaluar_fiabilidad_senal(df, 'triple_suelo', patrones_vela, config_avanzada)

        # Mostrar información de fiabilidad si hay patrones detectados
        if patrones_suelo['doble'] or patrones_suelo['triple']:
            st_obj.markdown("### 📊 Fiabilidad de las Señales")

            if patrones_suelo['doble']:
                nivel_color = "red" if fiabilidad_doble_suelo['nivel'] == "bajo" else "green" if fiabilidad_doble_suelo['nivel'] == "alto" else "orange"
                st_obj.markdown(f"**Doble Suelo**: <span style='color:{nivel_color};'>{fiabilidad_doble_suelo['porcentaje']}% ({fiabilidad_doble_suelo['nivel']})</span>", unsafe_allow_html=True)

            if patrones_suelo['triple']:
                nivel_color = "red" if fiabilidad_triple_suelo['nivel'] == "bajo" else "green" if fiabilidad_triple_suelo['nivel'] == "alto" else "orange"
                st_obj.markdown(f"**Triple Suelo**: <span style='color:{nivel_color};'>{fiabilidad_triple_suelo['porcentaje']}% ({fiabilidad_triple_suelo['nivel']})</span>", unsafe_allow_html=True)

        # Devolver los datos y análisis mejorados
        return {
            'df': df,
            'patrones_suelo': patrones_suelo,
            'patrones_vela': patrones_vela,
            'fiabilidad_doble_suelo': fiabilidad_doble_suelo,
            'fiabilidad_triple_suelo': fiabilidad_triple_suelo,
            'config_avanzada': config_avanzada
        }

    return None

import base64
import requests

def subir_a_github(filepath, repo, ruta_destino, rama="main"):
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("❌ GITHUB_TOKEN no está definido.")
        return

    url_api = f"https://api.github.com/repos/{repo}/contents/{ruta_destino}"
    
    with open(filepath, "rb") as f:
        contenido = f.read()
    contenido_b64 = base64.b64encode(contenido).decode("utf-8")

    # Obtener SHA del archivo si ya existe
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
    get_resp = requests.get(url_api, headers=headers, params={"ref": rama})
    
    sha = None
    if get_resp.status_code == 200:
        sha = get_resp.json()["sha"]

    payload = {
        "message": "Actualización automática de config_auto.json",
        "content": contenido_b64,
        "branch": rama
    }
    if sha:
        payload["sha"] = sha

    put_resp = requests.put(url_api, headers=headers, json=payload)
    if put_resp.status_code in [200, 201]:
        print("✅ Archivo subido a GitHub correctamente.")
    else:
        print("❌ Error al subir a GitHub:", put_resp.json())

# Guardar y subir config_auto.json
def guardar_config_auto(config, ruta="config_auto.json"):
    with open(ruta, "w") as f:
        json.dump(config, f, indent=2)
    print("✅ Configuración guardada localmente.")
    subir_a_github(ruta, repo="maximapomada/criptobot", ruta_destino="config_auto.json", rama="main")

