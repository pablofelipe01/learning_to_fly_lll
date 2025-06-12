# utils.py
# Funciones auxiliares para la estrategia

import numpy as np
from datetime import datetime
import pytz
import logging

def setup_logger(name, log_file, level=logging.INFO):
    """Configurar logger con formato personalizado"""
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para archivo
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Configurar logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def calculate_rsi(candles, period=14):
    """
    Calcular RSI a partir de velas
    
    Args:
        candles: Lista de velas con formato IQ Option
        period: Período para el cálculo del RSI
    
    Returns:
        float: Valor del RSI o None si no hay suficientes datos
    """
    if not candles or len(candles) < period + 1:
        return None
    
    try:
        # Extraer precios de cierre
        closes = [float(candle['close']) for candle in candles]
        
        # Calcular cambios de precio
        price_changes = []
        for i in range(1, len(closes)):
            price_changes.append(closes[i] - closes[i-1])
        
        # Separar ganancias y pérdidas
        gains = [change if change > 0 else 0 for change in price_changes]
        losses = [-change if change < 0 else 0 for change in price_changes]
        
        # Calcular promedios iniciales
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        # Aplicar suavizado exponencial
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        # Calcular RSI
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
        
    except Exception as e:
        logging.error(f"Error calculando RSI: {str(e)}")
        return None

def is_market_open():
    """
    Verificar si el mercado Forex está abierto
    Sin restricciones de horario según lo solicitado
    
    Returns:
        bool: True (siempre abierto para operar cuando el usuario quiera)
    """
    # Sin restricción de horario según lo solicitado
    # El usuario puede operar cuando quiera
    return True

def get_iqoption_pair_mapping(pair_name):
    """
    Obtener el nombre correcto del par para IQ Option
    
    Args:
        pair_name: Nombre del par (ej: "EURUSD")
    
    Returns:
        str: Nombre formateado para IQ Option
    """
    # IQ Option usa nombres en mayúsculas para forex
    return pair_name.upper()

def format_currency(amount):
    """
    Formatear cantidad como moneda
    
    Args:
        amount: Cantidad a formatear
    
    Returns:
        str: Cantidad formateada
    """
    return f"${amount:,.2f}"

def calculate_win_rate(wins, losses):
    """
    Calcular tasa de éxito
    
    Args:
        wins: Número de operaciones ganadoras
        losses: Número de operaciones perdedoras
    
    Returns:
        float: Porcentaje de éxito
    """
    total = wins + losses
    if total == 0:
        return 0.0
    return (wins / total) * 100

def calculate_profit_factor(total_profit, total_loss):
    """
    Calcular factor de beneficio
    
    Args:
        total_profit: Ganancias totales
        total_loss: Pérdidas totales
    
    Returns:
        float: Factor de beneficio
    """
    if total_loss == 0:
        return float('inf') if total_profit > 0 else 0
    return abs(total_profit / total_loss)

def seconds_to_expiry(expiry_time):
    """
    Calcular segundos hasta la expiración
    
    Args:
        expiry_time: datetime de expiración
    
    Returns:
        float: Segundos hasta expiración
    """
    return (expiry_time - datetime.now()).total_seconds()

def validate_forex_pairs(pairs, available_assets):
    """
    Validar qué pares están disponibles
    
    Args:
        pairs: Lista de pares a validar
        available_assets: Activos disponibles en IQ Option
    
    Returns:
        list: Lista de pares válidos
    """
    valid_pairs = []
    for pair in pairs:
        # Verificar versión estándar
        if pair.upper() in available_assets:
            valid_pairs.append(pair)
        # Verificar versión OTC
        elif f"{pair.upper()}-OTC" in available_assets:
            valid_pairs.append(pair)
    
    return valid_pairs