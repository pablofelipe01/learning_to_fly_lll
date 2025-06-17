# config.py
# Configuración de la estrategia RSI para IQ Option

# Credenciales IQ Option
IQ_EMAIL = "pablofelipe@me.com"
IQ_PASSWORD = "DaMa0713"  # Añadir tu contraseña aquí
ACCOUNT_TYPE = "REAL"  # "PRACTICE" o "REAL"

# Pares de divisas a operar
FOREX_PAIRS = [
    "AUDCHF", "CADCHF", "EURAUD", "EURCAD", "EURCHF", "EURNZD",
    "GBPAUD", "GBPCAD", "GBPCHF", "GBPNZD", "GBPJPY", "NZDUSD",
    "EURGBP", "EURJPY", "EURUSD", "GBPUSD", 
]

# Configuración RSI - LÓGICA INVERTIDA
RSI_PERIOD = 14
OVERSOLD_LEVEL = 35    # Nivel para señal PUT (invertido)
OVERBOUGHT_LEVEL = 65  # Nivel para señal CALL (invertido)

# Configuración de opciones binarias
EXPIRY_MINUTES = 2  # Tiempo de expiración en minutos
CANDLE_TIMEFRAME = 300  # 5 minutos en segundos (para RSI)

# Gestión de riesgo - Stop Loss
ABSOLUTE_STOP_LOSS_PERCENT = 0.75  # 75% de pérdida del capital inicial
MONTHLY_STOP_LOSS_PERCENT = 0.40   # 40% de pérdida mensual

# Tamaño de posición
POSITION_SIZE_PERCENT = 0.025  # 2.5% del capital disponible
MIN_POSITION_SIZE = 4000       # Mínimo $1 (ajustar según el mínimo de IQ Option)
# MAX_POSITION_SIZE = 10000    # ELIMINADO - Sin límite máximo

# Control de operaciones
MIN_TIME_BETWEEN_SIGNALS = 60  # Minutos entre señales del mismo par (1 hora)
MAX_CONSECUTIVE_LOSSES = 999   # Prácticamente desactivado

# Configuración de activos
ALLOWED_ASSET_SUFFIXES = ["-OTC", "-op", ""]
PRIORITY_SUFFIX = None

# Modo de estrategia
STRATEGY_MODE = "CALL_PUT"

# Configuración de logging
LOG_LEVEL = "INFO"
LOG_FILE = "iqoption_strategy.log"

# Configuración de caché y timeouts
API_TIMEOUT = 10
SAVE_STATE_INTERVAL = 30

# Archivo de estado
STATE_FILE = "strategy_state.json"

# Configuración de debugging
USE_POSITION_HISTORY = True
POSITION_HISTORY_TIMEOUT = 5
DEBUG_ORDER_RESULTS = True