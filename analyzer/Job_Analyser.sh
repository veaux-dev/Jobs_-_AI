#!/usr/bin/env bash

# Definir rutas
DIR="/home/aizen/Projects/Python/Jobspy/analyzer/"
LOGfile="$DIR/logs/mi_script.log"
VENV="/home/aizen/Projects/Python/Jobspy/.venvlinux/bin/python"

# Moverse al directorio
cd "$DIR"

# ESCRIBIR ENCABEZADO EN EL LOG
echo "========================================================" >> "$LOGfile"
echo "🕒 INICIO DE EJECUCIÓN: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOGfile"
echo "========================================================" >> "$LOGfile"

# EJECUTAR EL SCRIPT
# Usamos el python del venv directamente
"$VENV" run_analyzer.py >> "$LOGfile" 2>&1

# ESCRIBIR PIE DE PÁGINA
echo "" >> "$LOGfile"
echo "🏁 FIN DE EJECUCIÓN: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOGfile"
echo "--------------------------------------------------------" >> "$LOGfile"
