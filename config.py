# config.py
# Configuración de la estrategia RSI para IQ Option - Multi-Activos

# Credenciales IQ Option
IQ_EMAIL = "tu_correo"
IQ_PASSWORD = "Tu_contraseña"  # Añadir tu contraseña aquí
ACCOUNT_TYPE = "PRACTICE"  # "PRACTICE" o "REAL"

# Lista de activos multi-mercado
TRADING_ASSETS = [
    "US500",   # S&P 500 - El más confiable
    "EURUSD",  # Rey del Forex
    "GER30",   # DAX - Muy técnico
    "GBPUSD",  # Cable - Líquido y predecible
    "XAUUSD",  # Oro - Respeta niveles
    "USDJPY",  # Yen - Movimientos claros
    "UK100",   # FTSE - Buen comportamiento
    "EURGBP",  # Euro/Libra - Menos volátil
    "AUDUSD",  # Aussie - Commodity currency
    "JP225",   # Nikkei - Técnicamente limpio
    "EURJPY",  # Euro/Yen - Buenos rebotes      # La más técnica de las acciones     # Plata - Sigue al oro        # Microsoft - Tendencias claras
    "GBPJPY",  # Libra/Yen - Para más volatilidad
]

# Mapeo OPCIONAL - Solo para casos especiales donde el nombre es muy diferente
# Comenta o elimina las líneas de activos que quieres que busquen cualquier variante
ASSET_IQ_MAPPING = {
    "US500": "SP500",     # S&P se llama SP500 en IQ Option
    # Los demás los dejamos buscar cualquier variante disponible
}

# Configuración RSI - LÓGICA INVERTIDA
RSI_PERIOD = 14
OVERSOLD_LEVEL = 35    # Nivel para señal PUT (invertido)
OVERBOUGHT_LEVEL = 65  # Nivel para señal CALL (invertido)

# Configuración de opciones binarias
EXPIRY_MINUTES = 5  # Tiempo de expiración en minutos
CANDLE_TIMEFRAME = 900  # 15 minutos en segundos (para RSI)

# Gestión de riesgo - Stop Loss
ABSOLUTE_STOP_LOSS_PERCENT = 0.75  # 75% de pérdida del capital inicial
MONTHLY_STOP_LOSS_PERCENT = 0.40   # 40% de pérdida mensual

# Tamaño de posición
POSITION_SIZE_PERCENT = 0.01  # 1% del capital disponible
MIN_POSITION_SIZE = 1.00       # Mínimo $1 (ajustar según el mínimo de IQ Option)

# Control de operaciones
MIN_TIME_BETWEEN_SIGNALS = 60  # Minutos entre señales del mismo activo (1 hora)
MAX_CONSECUTIVE_LOSSES = 999   # Prácticamente desactivado

# Configuración de activos
ALLOWED_ASSET_SUFFIXES = ["-OTC", "-op", ""]
PRIORITY_SUFFIX = None  # Sin prioridad - usa cualquier variante disponible

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