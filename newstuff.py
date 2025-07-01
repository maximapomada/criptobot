import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import requests
import io
import json
import os
from datetime import datetime, timedelta
import newstuff

st.set_page_config(
    page_title="Bot de Análisis Crypto - Poloniex", 
    layout="wide",
    initial_sidebar_state="expanded"
)


# === NUEVO: Scheduler para autoanálisis ===
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import pytz
import threading
import time

# === CONFIGURACIÓN DE TELEGRAM ===
TELEGRAM_TOKEN = os.environ.get("TGT")
TELEGRAM_CHAT_ID = os.environ.get("TGID")

# === HISTORIAL DE ALERTAS ===
HISTORIAL_FILE = "historial_alertas.json"
if os.path.exists(HISTORIAL_FILE):
    with open(HISTORIAL_FILE, "r") as f:
        historial_alertas = json.load(f)
else:
    historial_alertas = {}

def guardar_historial():
    with open(HISTORIAL_FILE, "w") as f:
        json.dump(historial_alertas, f, indent=2, default=str)

def alerta_ya_enviada(par, tipo, timestamp):
    clave = f"{par}_{tipo}_{timestamp}"
    return clave in historial_alertas

def registrar_alerta(par, tipo, timestamp):
    clave = f"{par}_{tipo}_{timestamp}"
    historial_alertas[clave] = str(datetime.now())
    guardar_historial()

# === CONFIGURACIÓN DE RECENCIA POR MONEDA ===
CONFIG_FILE = "config_suelos.json"
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r") as f:
        config_suelos = json.load(f)
else:
    config_suelos = {}

def guardar_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_suelos, f, indent=2)

def get_recencia_config(par):
    if par in config_suelos:
        return config_suelos[par].get("recencia_velas", 2), config_suelos[par].get("recencia_dias", 0)
    else:
        return 2, 0

def set_recencia_config(par, recencia_velas, recencia_dias):
    config_suelos[par] = {"recencia_velas": recencia_velas, "recencia_dias": recencia_dias}
    guardar_config()

# === CONFIGURACIÓN DE AUTOANÁLISIS ===
AUTO_CONFIG_FILE = "config_auto.json"

def cargar_auto_config():
    ejemplo = {
        "BTC/USDT": {
            "1d": 3,
            "1w": 1,
            "1M": {"por_semana": 5},
            "1y": {"por_mes": 2}
        },
        "ETH/USDT": {
            "1d": 2,
            "1w": 1
        }
    }
    if os.path.exists(AUTO_CONFIG_FILE):
        with open(AUTO_CONFIG_FILE, "r") as f:
            return json.load(f)
    else:
        with open(AUTO_CONFIG_FILE, "w") as f:
            json.dump(ejemplo, f, indent=2)
        return ejemplo

def guardar_auto_config(config_auto):
    with open(AUTO_CONFIG_FILE, "w") as f:
        json.dump(config_auto, f, indent=2)

def set_auto_config(symbol, timeframe, valor):
    config = cargar_auto_config()
    if symbol not in config:
        config[symbol] = {}
    config[symbol][timeframe] = valor
    guardar_auto_config(config)

def remove_auto_config(symbol, timeframe=None):
    config = cargar_auto_config()
    if symbol in config:
        if timeframe and timeframe in config[symbol]:
            del config[symbol][timeframe]
            if not config[symbol]:  # Si no quedan timeframes, eliminar el símbolo
                del config[symbol]
        else:
            del config[symbol]
        guardar_auto_config(config)

# === FUNCIONES DE ALERTA Y ANÁLISIS ===
def send_telegram_alert(message, symbol, timestamp, tipo):
    if alerta_ya_enviada(symbol, tipo, timestamp):
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            registrar_alerta(symbol, tipo, timestamp)
            return True
        else:
            print(f"Error en Telegram: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error al enviar alerta: {e}")
        return False

# === PATRONES DE VELA ===
PATRONES_VELA = {
    'hammer': ('🔨 Martillo', 'Patrón de reversión alcista'),
    'engulfing': ('🟢 Envolvente', 'Patrón de reversión'),
    'doji': ('✴️ Doji', 'Indecisión del mercado'),
    'morning_star': ('🌅 Estrella Matutina', 'Reversión alcista'),
    'evening_star': ('🌇 Estrella Vespertina', 'Reversión bajista'),
    'harami': ('🕯️ Harami', 'Patrón de reversión'),
    'shooting_star': ('🌠 Estrella Fugaz', 'Reversión bajista')
}

def obtener_patrones_vela(df):
    patrones_encontrados = []
    ultimo = df.iloc[-1]

    for patron, (emoji_nombre, descripcion) in PATRONES_VELA.items():
        if patron in df.columns and ultimo[patron] != 0:
            patrones_encontrados.append({
                'patron': patron,
                'nombre': emoji_nombre,
                'descripcion': descripcion,
                'valor': ultimo[patron]
            })

    return patrones_encontrados

# === SCHEDULER ===
scheduler = BackgroundScheduler(timezone=pytz.utc)
scheduler_started = False

def minutos_por_ejecucion(timeframe, freq):
    if timeframe == "1d":
        return 1440 // freq  # 1440 minutos = 24 horas
    if timeframe == "1w":
        return 10080 // freq  # 10080 minutos = 7 días
    return None

def programar_tareas_auto(symbols):
    global scheduler_started
    cfg = cargar_auto_config()

    # Limpiar trabajos existentes
    scheduler.remove_all_jobs()

    for symbol, tf_cfg in cfg.items():
        if symbol not in symbols:
            continue

        for tf, valor in tf_cfg.items():
            try:
                if tf in ["1d", "1w"]:
                    minutos = minutos_por_ejecucion(tf, int(valor))
                    if minutos:
                        scheduler.add_job(
                            analizar_simbolo_auto,
                            trigger=IntervalTrigger(minutes=minutos),
                            args=[symbol, tf],
                            id=f"auto_{symbol}_{tf}",
                            replace_existing=True
                        )
                else:
                    # Para mensual y anual
                    if isinstance(valor, dict):
                        unidad, veces = list(valor.items())[0]
                        if tf == "1M":
                            if unidad == "por_dia":
                                trigger = CronTrigger(hour=f"*/{24//veces}")
                            elif unidad == "por_semana":
                                dias_semana = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][:veces]
                                trigger = CronTrigger(day_of_week=",".join(dias_semana), hour="8")
                            elif unidad == "por_2semanas":
                                trigger = CronTrigger(day="1,15", hour="8")
                            elif unidad == "por_3semanas":
                                trigger = CronTrigger(day="1,10,20", hour="8")
                            elif unidad == "por_mes":
                                trigger = CronTrigger(day="1", hour="8")
                            else:
                                trigger = CronTrigger(day="1", hour="8")
                        elif tf == "1y":
                            # Para anual, ejecutar X veces al mes
                            dias_mes = list(range(1, 32, 32//veces))[:veces]
                            trigger = CronTrigger(day=",".join(map(str, dias_mes)), hour="8")
                        else:
                            continue

                        scheduler.add_job(
                            analizar_simbolo_auto,
                            trigger=trigger,
                            args=[symbol, tf],
                            id=f"auto_{symbol}_{tf}",
                            replace_existing=True
                        )
            except Exception as e:
                print(f"Error programando {symbol} {tf}: {e}")

    # Análisis masivo diario a las 08:00 UTC
    scheduler.add_job(
        analisis_masivo_diario,
        trigger=CronTrigger(hour=8, minute=0),
        id="analisis_masivo_diario",
        replace_existing=True
    )

    if not scheduler_started:
        scheduler.start()
        scheduler_started = True

# === EXCHANGE Y SÍMBOLOS ===
@st.cache_resource
def init_exchange():
    return ccxt.poloniex()

exchange = init_exchange()

@st.cache_data(ttl=3600)
def get_symbols():
    try:
        markets = exchange.load_markets()
        return list(markets.keys())
    except Exception as e:
        st.error(f"Error cargando símbolos: {e}")
        return ["BTC/USDT", "ETH/USDT"]

symbols = get_symbols()

# === FUNCIONES DE ANÁLISIS ===
@st.cache_data(ttl=300)
def get_ohlcv_data(symbol, timeframe):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=250)
        if not ohlcv or len(ohlcv) < 2:
            return None
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"Error obteniendo datos para {symbol}: {e}")
        return None

def analizar_simbolo_auto(symbol, timeframe):
    """Función para análisis automático desde el scheduler"""
    try:
        alertas_resumen = {}
        resultado = analizar_simbolo(symbol, timeframe, alertas_resumen)

        if alertas_resumen:
            enviar_resumen_telegram(alertas_resumen, timeframe, f"AUTO-{timeframe}")

    except Exception as e:
        print(f"Error en análisis automático de {symbol} {timeframe}: {e}")

def analisis_masivo_diario():
    """Análisis masivo diario de todas las monedas"""
    try:
        alertas_resumen = {}
        total_analizados = 0

        for symbol in symbols:
            try:
                resultado = analizar_simbolo(symbol, "1d", alertas_resumen)
                if resultado:
                    total_analizados += 1
                time.sleep(0.1)  # Pequeña pausa entre análisis
            except Exception as e:
                print(f"Error analizando {symbol}: {e}")
                continue

        if alertas_resumen:
            mensaje_extra = f"\n📊 Total analizados: {total_analizados} pares"
            enviar_resumen_telegram(alertas_resumen, "1d", "MASIVO-DIARIO", mensaje_extra)

    except Exception as e:
        print(f"Error en análisis masivo diario: {e}")

def analizar_simbolo(symbol, timeframe, alertas_resumen):
    try:
        df = get_ohlcv_data(symbol, timeframe)
        if df is None or len(df) < 20:
            return None

        # Aplicar mejoras de newstuff
        try:
            mejoras = newstuff.aplicar_mejoras(st, df, exchange, symbols, historial_alertas, config_suelos)
            if mejoras:
                df = mejoras['df']
                patrones_suelo = mejoras['patrones_suelo']
                patrones_vela = mejoras['patrones_vela']
                fiabilidad_doble_suelo = mejoras.get('fiabilidad_doble_suelo', 0)
                fiabilidad_triple_suelo = mejoras.get('fiabilidad_triple_suelo', 0)
            else:
                patrones_suelo = {}
                patrones_vela = {}
                fiabilidad_doble_suelo = 0
                fiabilidad_triple_suelo = 0
        except Exception as e:
            print(f"Error aplicando mejoras: {e}")
            patrones_suelo = {}
            patrones_vela = {}
            fiabilidad_doble_suelo = 0
            fiabilidad_triple_suelo = 0

        # Indicadores básicos
        if 'ema50' not in df.columns:
            df['ema50'] = ta.ema(df['close'], length=50)
        if 'ema200' not in df.columns:
            df['ema200'] = ta.ema(df['close'], length=200)
        if 'macd' not in df.columns:
            macd = ta.macd(df['close'])
            df['macd'] = macd['MACD_12_26_9']
            df['macd_signal'] = macd['MACDs_12_26_9']
        if 'rsi' not in df.columns:
            df['rsi'] = ta.rsi(df['close'], length=14)

        # Patrones de vela básicos
        if 'hammer' not in df.columns:
            df['hammer'] = ta.cdl_pattern(df['open'], df['high'], df['low'], df['close'], name='hammer')
        if 'engulfing' not in df.columns:
            df['engulfing'] = ta.cdl_pattern(df['open'], df['high'], df['low'], df['close'], name='engulfing')

        ultimo = df.iloc[-1]
        penultimo = df.iloc[-2] if len(df) > 1 else ultimo

        # Análisis de señales
        cruce_ema = (penultimo['ema50'] < penultimo['ema200']) and (ultimo['ema50'] > ultimo['ema200'])
        macd_alcista = (ultimo['macd'] > ultimo['macd_signal'])
        patron_reversion = (ultimo['hammer'] != 0) or (ultimo['engulfing'] == 100)

        # Obtener patrones de vela actuales
        patrones_vela_actuales = obtener_patrones_vela(df)

        # Generar alertas
        if symbol not in alertas_resumen:
            alertas_resumen[symbol] = []

        if patrones_suelo.get('doble', False):
            alertas_resumen[symbol].append({
                'tipo': 'DOBLE SUELO',
                'emoji': '🔵',
                'precio': ultimo['close'],
                'fiabilidad': fiabilidad_doble_suelo,
                'patrones_vela': patrones_vela_actuales
            })

        if patrones_suelo.get('triple', False):
            alertas_resumen[symbol].append({
                'tipo': 'TRIPLE SUELO',
                'emoji': '🟣',
                'precio': ultimo['close'],
                'fiabilidad': fiabilidad_triple_suelo,
                'patrones_vela': patrones_vela_actuales
            })

        if cruce_ema and macd_alcista and patron_reversion:
            alertas_resumen[symbol].append({
                'tipo': 'CAMBIO DE TENDENCIA ALCISTA',
                'emoji': '🚀',
                'precio': ultimo['close'],
                'fiabilidad': 75,
                'patrones_vela': patrones_vela_actuales
            })

        # Si no hay alertas, eliminar el símbolo del resumen
        if not alertas_resumen[symbol]:
            del alertas_resumen[symbol]

        return {
            'symbol': symbol,
            'precio': ultimo['close'],
            'cruce_ema': cruce_ema,
            'macd_alcista': macd_alcista,
            'patron_reversion': patron_reversion,
            'doble_suelo': patrones_suelo.get('doble', False),
            'triple_suelo': patrones_suelo.get('triple', False),
            'patrones_vela': patrones_vela_actuales,
            'df': df
        }

    except Exception as e:
        print(f"Error analizando {symbol}: {e}")
        return None

def enviar_resumen_telegram(alertas_resumen, timeframe, tipo_analisis="MANUAL", mensaje_extra=""):
    if not alertas_resumen:
        return

    mensaje = f"🔍 RESUMEN DE ANÁLISIS {tipo_analisis}\n"
    mensaje += f"⏰ Timeframe: {timeframe}\n"
    mensaje += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
    mensaje += f"🎯 Señales encontradas: {len(alertas_resumen)}\n\n"

    for symbol, alertas in alertas_resumen.items():
        for alerta in alertas:
            mensaje += f"{alerta['emoji']} **{symbol}**\n"
            mensaje += f"   📊 {alerta['tipo']}\n"
            mensaje += f"   💰 Precio: {alerta['precio']:.8f}\n"

            if 'fiabilidad' in alerta and isinstance(alerta['fiabilidad'], (int, float)) and alerta['fiabilidad'] > 0:
                mensaje += f"   🎯 Fiabilidad: {alerta['fiabilidad']}%\n"

            if alerta.get('patrones_vela'):
                patrones_txt = " | ".join([p['nombre'] for p in alerta['patrones_vela']])
                mensaje += f"   🕯️ Velas: {patrones_txt}\n"

            mensaje += "\n"

    if mensaje_extra:
        mensaje += mensaje_extra

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    send_telegram_alert(mensaje, f"RESUMEN_{tipo_analisis}", timestamp, "analisis_resumen")

# === INICIALIZACIÓN DEL SCHEDULER ===
def start_scheduler_once():
    if not hasattr(st.session_state, "scheduler_started"):
        try:
            threading.Thread(target=programar_tareas_auto, args=(symbols,), daemon=True).start()
            st.session_state.scheduler_started = True
        except Exception as e:
            print(f"Error iniciando scheduler: {e}")

# === STREAMLIT UI ===

st.title("🤖 Bot de Análisis de Criptomonedas - Poloniex")
st.markdown("*Detección automática de patrones, suelos y cambios de tendencia*")

# === SIDEBAR CONFIGURACIÓN ===
st.sidebar.header("⚙️ Configuración Principal")

selected_symbol = st.sidebar.selectbox(
    "Seleccionar Par de Trading",
    symbols,
    index=symbols.index('BTC/USDT') if 'BTC/USDT' in symbols else 0
)

timeframe = st.sidebar.selectbox(
    "Intervalo de Tiempo",
    ['12h', '1d', '3d', '1w', '1M'],
    index=1
)

refresh_rate_min = st.sidebar.slider("Actualizar cada (minutos)", 1, 300, 5, step=1)

# === CONFIGURACIÓN DE RECENCIA ===
st.sidebar.markdown("---")
st.sidebar.markdown("**🎯 Configuración de Suelos**")
recencia_velas = st.sidebar.number_input(
    "Máx. velas desde último mínimo", 
    min_value=1, max_value=10, 
    value=get_recencia_config(selected_symbol)[0], 
    step=1
)
recencia_dias = st.sidebar.number_input(
    "Máx. días desde último mínimo (0=ignorar)", 
    min_value=0, max_value=30, 
    value=get_recencia_config(selected_symbol)[1], 
    step=1
)

if st.sidebar.button("💾 Guardar configuración de suelos"):
    set_recencia_config(selected_symbol, recencia_velas, recencia_dias)
    st.sidebar.success("✅ Configuración guardada")

# === CONFIGURACIÓN DE AUTOANÁLISIS ===
st.sidebar.markdown("---")
st.sidebar.markdown("**🔄 Autoanálisis**")

with st.sidebar.expander("Configurar Autoanálisis", expanded=False):
    auto_symbol = st.selectbox("Par para autoanálisis", symbols, key="auto_symbol")
    auto_timeframe = st.selectbox("Timeframe", ["1d", "1w", "1M", "1y"], key="auto_tf")

    if auto_timeframe in ["1d", "1w"]:
        max_freq = 4 if auto_timeframe == "1d" else 2
        auto_freq = st.slider(f"Veces al día", 1, max_freq, 1, key="auto_freq")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Guardar", key="save_auto"):
                set_auto_config(auto_symbol, auto_timeframe, auto_freq)
                st.success("✅ Guardado")
                # Reprogramar tareas
                programar_tareas_auto(symbols)

        with col2:
            if st.button("🗑️ Eliminar", key="del_auto"):
                remove_auto_config(auto_symbol, auto_timeframe)
                st.success("✅ Eliminado")
                programar_tareas_auto(symbols)

    else:  # 1M o 1y
        if auto_timeframe == "1M":
            unidades = ["por_dia", "por_semana", "por_2semanas", "por_3semanas", "por_mes"]
            max_veces = 25
        else:  # 1y
            unidades = ["por_mes"]
            max_veces = 10

        auto_unidad = st.selectbox("Unidad", unidades, key="auto_unidad")
        auto_veces = st.number_input("Veces", 1, max_veces, 1, key="auto_veces")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Guardar", key="save_auto_complex"):
                set_auto_config(auto_symbol, auto_timeframe, {auto_unidad: int(auto_veces)})
                st.success("✅ Guardado")
                programar_tareas_auto(symbols)

        with col2:
            if st.button("🗑️ Eliminar", key="del_auto_complex"):
                remove_auto_config(auto_symbol, auto_timeframe)
                st.success("✅ Eliminado")
                programar_tareas_auto(symbols)

# Mostrar configuración actual
config_actual = cargar_auto_config()
if config_actual:
    st.sidebar.markdown("**📋 Configuración Actual:**")
    for sym, cfg in config_actual.items():
        st.sidebar.text(f"• {sym}")
        for tf, freq in cfg.items():
            st.sidebar.text(f"  {tf}: {freq}")

# === BOTONES DE ACCIÓN ===
st.sidebar.markdown("---")
col1, col2 = st.sidebar.columns(2)

with col1:
    if st.button("🔄 Analizar Todas", key="analyze_all"):
        with st.spinner("Analizando todas las monedas..."):
            alertas_resumen = {}
            progress_bar = st.progress(0)

            for i, symbol in enumerate(symbols[:50]):  # Limitar a 50
                try:
                    analizar_simbolo(symbol, timeframe, alertas_resumen)
                    progress_bar.progress((i + 1) / min(50, len(symbols)))
                except:
                    continue

            if alertas_resumen:
                enviar_resumen_telegram(alertas_resumen, timeframe, "MANUAL")
                st.success(f"✅ Análisis completado. {len(alertas_resumen)} señales encontradas.")
            else:
                st.info("ℹ️ No se encontraron señales relevantes.")

with col2:
    if st.button("📱 Test Telegram", key="test_telegram"):
        mensaje_test = f"🧪 Test desde Bot Poloniex\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        if send_telegram_alert(mensaje_test, "TEST", datetime.now().strftime('%Y%m%d_%H%M%S'), "test"):
            st.success("✅ Mensaje enviado")
        else:
            st.error("❌ Error enviando mensaje")

# === ANÁLISIS PRINCIPAL ===
st.markdown("---")

# Iniciar scheduler
start_scheduler_once()

# Obtener y analizar datos
df = get_ohlcv_data(selected_symbol, timeframe)

if df is not None and len(df) > 20:
    alertas_resumen = {}
    resultado = analizar_simbolo(selected_symbol, timeframe, alertas_resumen)

    if resultado:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("💰 Precio Actual", f"{resultado['precio']:.8f}")

        with col2:
            st.metric("📈 EMA Cross", "✅ SÍ" if resultado['cruce_ema'] else "❌ NO")

        with col3:
            st.metric("📊 MACD Alcista", "✅ SÍ" if resultado['macd_alcista'] else "❌ NO")

        with col4:
            st.metric("🕯️ Patrón Reversión", "✅ SÍ" if resultado['patron_reversion'] else "❌ NO")

        # Mostrar patrones de vela
        if resultado['patrones_vela']:
            st.markdown("### 🕯️ Patrones de Vela Detectados")
            for patron in resultado['patrones_vela']:
                st.info(f"{patron['nombre']} - {patron['descripcion']}")
        else:
            st.markdown("### 🕯️ Patrones de Vela Detectados")
            st.info("No se detectaron patrones de vela relevantes en la última vela.")

        # Mostrar alertas si las hay
        if alertas_resumen:
            st.markdown("### 🚨 Señales Detectadas")
            for symbol, alertas in alertas_resumen.items():
                for alerta in alertas:
                    st.success(f"{alerta['emoji']} **{alerta['tipo']}** - Precio: {alerta['precio']:.8f}")

        # Gráfico
        if 'df' in resultado:
            df_plot = resultado['df']
            fig = go.Figure()

            # Candlesticks
            fig.add_trace(go.Candlestick(
                x=df_plot['timestamp'],
                open=df_plot['open'],
                high=df_plot['high'],
                low=df_plot['low'],
                close=df_plot['close'],
                name="Precio"
            ))

            # EMAs
            if 'ema50' in df_plot.columns:
                fig.add_trace(go.Scatter(
                    x=df_plot['timestamp'],
                    y=df_plot['ema50'],
                    name="EMA 50",
                    line=dict(color='orange', width=1)
                ))

            if 'ema200' in df_plot.columns:
                fig.add_trace(go.Scatter(
                    x=df_plot['timestamp'],
                    y=df_plot['ema200'],
                    name="EMA 200",
                    line=dict(color='red', width=1)
                ))

            fig.update_layout(
                title=f"{selected_symbol} - {timeframe}",
                xaxis_title="Fecha",
                yaxis_title="Precio",
                height=600
            )

            st.plotly_chart(fig, use_container_width=True)

        # Opción de descarga
        if st.button("📥 Descargar Datos CSV"):
            csv = df.to_csv(index=False)
            st.download_button(
                label="💾 Descargar CSV",
                data=csv,
                file_name=f"{selected_symbol}_{timeframe}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

else:
    st.error(f"❌ No se pudieron obtener datos para {selected_symbol}")

# === INFORMACIÓN ===
st.markdown("---")
st.markdown("""
### ℹ️ Información del Bot

**Funcionalidades:**
- 🔍 Detección automática de doble y triple suelo
- 📈 Análisis de cruces de EMAs y señales MACD
- 🕯️ Reconocimiento de patrones de vela
- 📱 Alertas automáticas por Telegram
- 🔄 Autoanálisis programable por par y timeframe
- 📊 Análisis masivo diario de todas las monedas

**Autoanálisis:**
- Configura la frecuencia de análisis para cada par
- Análisis automático 24/7 sin intervención manual
- Resúmenes automáticos por Telegram

**Timeframes soportados:** 12h, 1d, 3d, 1w, 1M
""")

# Auto-refresh
time.sleep(refresh_rate_min * 60)
st.rerun()
