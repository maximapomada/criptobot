import subprocess
import sys
import os

# Obtén la ruta absoluta del archivo del bot
script_path = os.path.abspath("bot.py")

# Ejecuta el comando de Streamlit
subprocess.run([sys.executable, "-m", "streamlit", "run", script_path])
