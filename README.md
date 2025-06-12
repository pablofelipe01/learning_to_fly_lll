# learning_to_fly_lll
Estrategia RSI Multi-Divisa para IQ Option
Adaptación de estrategia RSI de QuantConnect para opciones binarias en IQ Option.

📋 Características
Estrategia RSI: Señales CALL cuando RSI ≤ 30, PUT cuando RSI ≥ 70
Multi-divisa: Opera con 17 pares de forex simultáneamente
Gestión de riesgo avanzada:
Stop loss absoluto: 75% de pérdida del capital inicial
Stop loss mensual: 40% de pérdida en el mes
Bloqueo automático tras 2 pérdidas consecutivas por par
Tamaño de posición dinámico: 5% del capital (mín $5k, máx $20k)
Expiración: 5 minutos
Sin restricción horaria: Opera cuando el usuario lo desee
🚀 Instalación
1. Requisitos previos
# Python 3.7 o superior
python --version

# Instalar pip si no lo tienes
python -m ensurepip --upgrade
2. Instalar dependencias
pip install iqoptionapi
pip install numpy
pip install pytz
3. Configuración
Edita el archivo config.py con tus credenciales:

# Credenciales IQ Option
IQ_EMAIL = "tu_email@example.com"
IQ_PASSWORD = "tu_password"
ACCOUNT_TYPE = "PRACTICE"  # Usa "REAL" para cuenta real
📖 Uso
Ejecución básica
python main.py
Con parámetros personalizados
# Especificar credenciales por línea de comandos
python main.py --email tu_email@example.com --password tu_password

# Usar cuenta real
python main.py --account REAL

# Modo prueba (solo verifica conexión)
python main.py --test
📊 Estructura del proyecto
├── config.py      # Configuración de la estrategia
├── main.py        # Punto de entrada principal
├── strategy.py    # Lógica de la estrategia RSI
├── utils.py       # Funciones auxiliares
└── README.md      # Esta guía
⚙️ Configuración avanzada
Ajustar niveles RSI
En config.py:

OVERSOLD_LEVEL = 30    # Nivel para señal CALL
OVERBOUGHT_LEVEL = 70  # Nivel para señal PUT
Modificar gestión de riesgo
# Stop loss
ABSOLUTE_STOP_LOSS_PERCENT = 0.75  # 75% de pérdida total
MONTHLY_STOP_LOSS_PERCENT = 0.40   # 40% de pérdida mensual

# Tamaño de posición
POSITION_SIZE_PERCENT = 0.05  # 5% del capital
MIN_POSITION_SIZE = 5000      # Mínimo $5,000
MAX_POSITION_SIZE = 20000     # Máximo $20,000
Agregar o quitar pares
En config.py, modifica la lista FOREX_PAIRS:

FOREX_PAIRS = [
    "EURUSD", "GBPUSD", "USDJPY",  # etc...
]
📈 Monitoreo
La estrategia genera logs detallados en iqoption_strategy.log:

Señales de trading
Resultados de operaciones
Estado del capital
Alertas de stop loss
Ver logs en tiempo real
# Linux/Mac
tail -f iqoption_strategy.log

# Windows PowerShell
Get-Content iqoption_strategy.log -Wait
🛡️ Gestión de riesgo
Siempre prueba primero en cuenta PRACTICE
El stop loss absoluto detiene toda operación al perder 75%
El stop loss mensual pausa operaciones al perder 40% en el mes
Los pares se bloquean automáticamente tras 2 pérdidas consecutivas
⚠️ Advertencias
Las opciones binarias conllevan alto riesgo
Rendimientos pasados no garantizan resultados futuros
Opera solo con capital que puedas permitirte perder
Esta herramienta es solo para fines educativos
🔧 Solución de problemas
Error de conexión
Verifica credenciales en config.py
Si tienes 2FA activado, desactívalo temporalmente
Asegúrate de tener conexión a internet estable
No encuentra pares disponibles
IQ Option puede tener diferentes activos disponibles según tu región
Los activos OTC solo están disponibles fuera del horario de mercado
Verifica que los pares en FOREX_PAIRS existan en tu cuenta
La estrategia no genera señales
Verifica que el RSI esté llegando a los niveles configurados
Puede ser necesario ajustar OVERSOLD_LEVEL y OVERBOUGHT_LEVEL
Revisa los logs para más detalles
📝 Estado guardado
La estrategia guarda su estado en strategy_state.json:

Operaciones activas
Estadísticas acumuladas
Estado de stop loss
Al reiniciar, la estrategia recupera automáticamente su estado anterior.

🤝 Contribuciones
Si encuentras bugs o tienes sugerencias, por favor abre un issue o envía un pull request.

📄 Licencia
Este proyecto es solo para fines educativos. Úsalo bajo tu propio riesgo.# ai-trading-bot

Mejorando el esquema

estructura_bot