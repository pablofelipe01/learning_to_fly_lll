# strategy.py
# Estrategia RSI adaptada de QuantConnect para IQ Option - Multi-Activos

import warnings
import threading

# Suprimir errores de threads secundarios
threading.excepthook = lambda args: None

import time
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
import logging
import pytz
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from iqoptionapi.stable_api import IQ_Option

from config import (
    IQ_EMAIL, IQ_PASSWORD, ACCOUNT_TYPE, TRADING_ASSETS, ASSET_IQ_MAPPING,
    RSI_PERIOD, OVERSOLD_LEVEL, OVERBOUGHT_LEVEL, EXPIRY_MINUTES, CANDLE_TIMEFRAME,
    ABSOLUTE_STOP_LOSS_PERCENT, MONTHLY_STOP_LOSS_PERCENT, POSITION_SIZE_PERCENT,
    MIN_POSITION_SIZE, MIN_TIME_BETWEEN_SIGNALS, MAX_CONSECUTIVE_LOSSES,
    ALLOWED_ASSET_SUFFIXES, PRIORITY_SUFFIX, STRATEGY_MODE, LOG_LEVEL, LOG_FILE,
    API_TIMEOUT, SAVE_STATE_INTERVAL, STATE_FILE, USE_POSITION_HISTORY,
    POSITION_HISTORY_TIMEOUT, DEBUG_ORDER_RESULTS
)
from utils import calculate_rsi, is_market_open, format_currency, calculate_win_rate, setup_logger

class MultiAssetRSIBinaryOptionsStrategy:
    def __init__(self, email, password, account_type="PRACTICE"):
        """
        Inicializar la estrategia de opciones binarias con RSI
        Adaptada de QuantConnect para IQ Option - Multi-Activos
        """
        # Configurar logger
        self.logger = setup_logger(__name__, LOG_FILE, getattr(logging, LOG_LEVEL))
        self.logger.info("🎯 INICIANDO ESTRATEGIA RSI MULTI-ACTIVOS (LÓGICA INVERTIDA)")
        self.logger.info(f"📊 Configuración: PUT <= {OVERSOLD_LEVEL}, CALL >= {OVERBOUGHT_LEVEL}")
        self.logger.info("⚡ LÓGICA INVERTIDA: PUT en sobreventa, CALL en sobrecompra")
        
        # Conexión a IQ Option
        self._connect_to_iq_option(email, password, account_type)
        
        # Capital inicial y gestión de riesgo
        self.initial_capital = self.iqoption.get_balance()
        self.logger.info(f"💰 Capital inicial: {format_currency(self.initial_capital)}")
        
        # Umbrales de stop loss
        self.absolute_stop_loss_threshold = self.initial_capital * (1 - ABSOLUTE_STOP_LOSS_PERCENT)
        self.absolute_stop_loss_activated = False
        
        # Configuración de posiciones
        self.position_size_percent = POSITION_SIZE_PERCENT
        self.min_position_size = MIN_POSITION_SIZE
        
        # Parámetros de trading
        self.trading_assets = TRADING_ASSETS
        self.asset_mapping = ASSET_IQ_MAPPING
        self.expiry_minutes = EXPIRY_MINUTES
        self.oversold_level = OVERSOLD_LEVEL
        self.overbought_level = OVERBOUGHT_LEVEL
        self.rsi_period = RSI_PERIOD
        self.candle_timeframe = CANDLE_TIMEFRAME
        self.min_time_between_signals = MIN_TIME_BETWEEN_SIGNALS
        
        # Gestión de operaciones activas
        self.active_options = defaultdict(list)
        self.last_signal_time = defaultdict(lambda: datetime.min)
        self.consecutive_losses = defaultdict(int)
        self.daily_lockouts = defaultdict(lambda: False)
        
        # Stop loss mensual
        self.monthly_stop_loss = False
        self.stop_loss_triggered_month = None
        self.monthly_starting_capital = {}
        self.current_month = None
        
        # Estadísticas de trading
        self.wins = defaultdict(int)
        self.losses = defaultdict(int)
        self.ties = defaultdict(int)  # Contador de empates
        self.total_profit = 0.0
        self.daily_profit = 0.0
        self.monthly_profits = defaultdict(float)
        self.last_date = None
        self.min_capital = self.initial_capital
        
        # Daily profit lock (parar cuando el día es rentable)
        self.daily_profit_lock = False
        self.daily_profit_lock_amount = 0.0
        self.daily_profit_lock_time = None
        
        # Daily loss lock (parar después de 3 pérdidas consecutivas)
        self.daily_consecutive_losses = 0
        self.daily_loss_lock = False
        self.daily_loss_lock_time = None
        self.max_daily_consecutive_losses = 3
        
        # Control de sistema
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.last_activity_time = time.time()
        self.start_time = time.time()
        
        # Período de calentamiento (1 hora sin operaciones)
        self.warmup_period = 3600  # 1 hora en segundos
        self.warmup_end_time = self.start_time + self.warmup_period
        self.logger.info(f"⏳ Período de calentamiento activo por 1 hora")
        self.logger.info(f"🕐 Primera operación posible a las: {datetime.fromtimestamp(self.warmup_end_time).strftime('%H:%M:%S')}")
        
        # Cache para optimización
        self.opcode_cache = {}
        self.opcode_cache_timestamp = 0
        self.asset_open_status_cache = {}
        self.asset_open_status_timestamp = 0
        
        # Mapeo de activos
        self.asset_option_types = {}
        self.iqoption_assets = {}
        self.valid_assets = []
        
        # Cargar estado previo si existe
        self.load_state()
        
        # Verificar si es un nuevo día al iniciar
        current_date = datetime.now().date()
        if self.last_date != current_date:
            self.logger.info(f"🌅 Detectado nuevo día al iniciar: {current_date}")
            self.on_new_day()
            self.last_date = current_date
        
        # Validar activos disponibles
        self.check_valid_assets()
        
    def _connect_to_iq_option(self, email, password, account_type):
        """Conectar a IQ Option con manejo de errores"""
        self.logger.info("🔗 Conectando a IQ Option...")
        self.iqoption = IQ_Option(email, password)
        login_status, login_reason = self.iqoption.connect()
        
        if not login_status:
            self.logger.error(f"❌ Error al conectar: {login_reason}")
            if "2FA" in str(login_reason).upper():
                self.logger.info("🔑 Se requiere autenticación de dos factores (2FA)")
            raise Exception(f"Error al conectar a IQ Option: {login_reason}")
        
        self.logger.info("✅ Conexión exitosa")
        self.iqoption.change_balance(account_type)
        balance = self.iqoption.get_balance()
        self.logger.info(f"💰 Balance actual: {format_currency(balance)}")
    
    def api_call_with_timeout(self, func, *args, timeout=API_TIMEOUT, **kwargs):
        """Ejecutar llamada API con timeout"""
        self.last_activity_time = time.time()
        try:
            future = self.executor.submit(func, *args, **kwargs)
            result = future.result(timeout=timeout)
            return result
        except FutureTimeoutError:
            self.logger.error(f"⚠️ TIMEOUT: {func.__name__} tardó más de {timeout}s")
            return None
        except Exception as e:
            self.logger.error(f"❌ Error en {func.__name__}: {str(e)}")
            return None
    
    def check_valid_assets(self):
        """Verificar qué activos están disponibles para operar"""
        self.logger.info("🔍 Verificando activos disponibles...")
        
        # Actualizar lista de activos
        self.api_call_with_timeout(self.iqoption.update_ACTIVES_OPCODE)
        opcodes = self.api_call_with_timeout(self.iqoption.get_all_ACTIVES_OPCODE)
        
        if not opcodes:
            self.logger.error("❌ No se pudieron obtener los activos disponibles")
            return []
        
        # Obtener estado de activos
        all_assets = self.api_call_with_timeout(self.iqoption.get_all_open_time)
        if not all_assets:
            self.logger.error("❌ No se pudo obtener el estado de los activos")
            return []
        
        self.valid_assets = []
        self.asset_option_types = {}
        self.iqoption_assets = {}
        
        # Verificar cada activo
        for asset in self.trading_assets:
            # Si tenemos un mapeo conocido, usarlo directamente
            if asset in self.asset_mapping:
                iq_name = self.asset_mapping[asset]
                found = False
                
                # Buscar en opciones turbo y binarias (preferir binarias)
                for option_type in ["binary", "turbo"]:
                    if option_type not in all_assets:
                        continue
                    
                    if iq_name in all_assets[option_type]:
                        if all_assets[option_type][iq_name].get("open", False):
                            self.valid_assets.append(asset)
                            self.asset_option_types[asset] = option_type
                            self.iqoption_assets[asset] = iq_name
                            self.logger.info(f"✅ {asset}: Disponible como {iq_name} ({option_type})")
                            found = True
                            break
                
                if not found:
                    self.logger.warning(f"⚠️ {asset}: No disponible ({iq_name})")
            else:
                # Buscar variantes si no hay mapeo (compatibilidad con versión anterior)
                asset_upper = asset.upper()
                found = False
                available_options = []
                
                # Buscar en opciones turbo y binarias
                for option_type in ["turbo", "binary"]:
                    if option_type not in all_assets:
                        continue
                    
                    # Lista de variantes a verificar
                    variants_to_check = [
                        asset_upper,
                        f"{asset_upper}-OTC",
                        f"{asset_upper}-op"
                    ]
                    
                    # Buscar cada variante
                    for variant in variants_to_check:
                        if variant in all_assets[option_type]:
                            if all_assets[option_type][variant].get("open", False):
                                available_options.append({
                                    'asset': asset,
                                    'option_type': option_type,
                                    'iq_name': variant,
                                    'is_otc': variant.endswith('-OTC')
                                })
                                self.logger.info(f"✅ {asset}: Encontrado como {variant} ({option_type})")
                
                # Seleccionar la mejor opción disponible
                if available_options:
                    best_option = available_options[0]  # Primera disponible
                    self.valid_assets.append(best_option['asset'])
                    self.asset_option_types[best_option['asset']] = best_option['option_type']
                    self.iqoption_assets[best_option['asset']] = best_option['iq_name']
                else:
                    self.logger.warning(f"⚠️ {asset}: No disponible en ninguna variante")
        
        # Log resumen
        self.logger.info(f"📊 Total activos disponibles: {len(self.valid_assets)}")
        if self.valid_assets:
            self.logger.info("📋 Activos habilitados:")
            for asset in self.valid_assets:
                self.logger.info(f"   - {asset} → {self.iqoption_assets[asset]} ({self.asset_option_types[asset]})")
        
        return self.valid_assets
    
    def test_check_order_result(self, order_id):
        """
        Método de prueba para verificar el resultado de una orden específica
        Útil para debugging
        """
        self.logger.info(f"🔍 PRUEBA: Verificando orden {order_id}")
        self.logger.info(f"   Tipo de ID: {type(order_id)}, Valor: {order_id}")
        
        # Convertir a int si es necesario
        try:
            order_id_int = int(order_id)
        except:
            order_id_int = order_id
        
        # Método 1: get_async_order
        self.logger.info("📋 Método 1: get_async_order")
        result1 = self.api_call_with_timeout(self.iqoption.get_async_order, order_id, timeout=5)
        if result1:
            self.logger.info(f"   Resultado: {result1}")
            if isinstance(result1, dict):
                for key, value in result1.items():
                    self.logger.info(f"   {key}: {value}")
        else:
            self.logger.info("   No se obtuvo resultado")
        
        # Método 2: Buscar en historial con sintaxis correcta
        self.logger.info("📋 Método 2: Buscar en historial de posiciones")
        try:
            history = self.api_call_with_timeout(
                self.iqoption.get_position_history,
                "binary-option",  # Argumento requerido
                timeout=5
            )
            
            positions = []
            if history:
                # Manejar formato tupla
                if isinstance(history, tuple):
                    for element in history:
                        if isinstance(element, list) and element:
                            if isinstance(element[0], dict) and 'id' in element[0]:
                                positions = element
                                break
                elif isinstance(history, dict) and 'positions' in history:
                    positions = history['positions']
                elif isinstance(history, list):
                    positions = history
                
                found = False
                for position in positions[:50]:  # Buscar en las últimas 50
                    if str(position.get('id')) == str(order_id):
                        found = True
                        self.logger.info("   ✅ Orden encontrada en historial:")
                        self.logger.info(f"   Status: {position.get('status')}")
                        self.logger.info(f"   Win: {position.get('win')}")
                        self.logger.info(f"   Amount: ${position.get('amount', 0):,.2f}")
                        self.logger.info(f"   Win Amount: ${position.get('win_amount', 0):,.2f}")
                        self.logger.info(f"   Created: {position.get('created')}")
                        self.logger.info(f"   Expired: {position.get('expired')}")
                        break
                
                if not found:
                    self.logger.info("   ❌ Orden no encontrada en historial")
                    # Mostrar algunas órdenes recientes para referencia
                    self.logger.info("   📋 Últimas 3 órdenes en historial:")
                    for i, pos in enumerate(positions[:3]):
                        self.logger.info(f"      {i+1}. ID: {pos.get('id')}, Asset: {pos.get('active')}")
        except Exception as e:
            self.logger.error(f"   Error buscando en historial: {str(e)}")
        
        # Método 3: get_position_history_v2 si existe
        if hasattr(self.iqoption, 'get_position_history_v2'):
            self.logger.info("📋 Método 3: get_position_history_v2")
            try:
                # Necesita 4 argumentos: limit, offset, start, end
                import time as time_module
                limit = 10
                offset = 0
                start = int(time_module.time() - 3600)  # 1 hora atrás
                end = int(time_module.time())
                
                history_v2 = self.api_call_with_timeout(
                    self.iqoption.get_position_history_v2,
                    "binary-option",
                    limit,
                    offset,
                    start,
                    end,
                    timeout=5
                )
                if history_v2:
                    self.logger.info(f"   ✅ Funciona. Tipo: {type(history_v2)}")
            except Exception as e:
                self.logger.info(f"   ❌ Error: {str(e)}")
        
        return result1, None
    
    def check_recent_orders_results(self, minutes=30):
        """
        Verificar resultados de órdenes recientes para debugging
        Esto ayudará a identificar problemas con la detección de resultados
        """
        self.logger.info(f"🔍 Verificando órdenes recientes...")
        
        # Intentar obtener historial de órdenes
        try:
            # Método principal: get_position_history con sintaxis correcta
            self.logger.info(f"📋 Obteniendo historial de posiciones...")
            history = self.api_call_with_timeout(
                self.iqoption.get_position_history, 
                "binary-option",  # Argumento requerido
                timeout=5
            )
            
            positions = []
            if history:
                # Manejar formato tupla (formato real)
                if isinstance(history, tuple):
                    self.logger.info(f"✅ Historial obtenido (formato tupla)")
                    for element in history:
                        if isinstance(element, list) and element:
                            if isinstance(element[0], dict) and 'id' in element[0]:
                                positions = element
                                break
                # Manejar otros formatos
                elif isinstance(history, dict) and 'positions' in history:
                    positions = history['positions']
                    self.logger.info(f"✅ Historial obtenido (formato dict)")
                elif isinstance(history, list):
                    positions = history
                    self.logger.info(f"✅ Historial obtenido (formato lista)")
                else:
                    self.logger.warning(f"⚠️ Formato desconocido: {type(history)}")
                
                if positions:
                    self.logger.info(f"📊 Total de posiciones: {len(positions)}")
                    self.logger.info(f"📋 Mostrando últimas 10 órdenes:")
                    
                    for i, pos in enumerate(positions[:10]):
                        win = pos.get('win', 'unknown')
                        amount = pos.get('amount', 0)
                        win_amount = pos.get('win_amount', 0)
                        
                        # Determinar emoji y resultado
                        if win == 'win':
                            emoji = "✅"
                            result = f"+${win_amount - amount:.2f}"
                        elif win == 'loose':
                            emoji = "❌"
                            result = f"-${amount:.2f}"
                        elif win == 'equal':
                            emoji = "🟡"
                            result = "$0"
                        else:
                            emoji = "❓"
                            result = "?"
                        
                        self.logger.info(f"\n   Orden {i+1}: {emoji}")
                        self.logger.info(f"   ID: {pos.get('id')}")
                        self.logger.info(f"   Asset: {pos.get('active')}")
                        self.logger.info(f"   Direction: {pos.get('direction')}")
                        self.logger.info(f"   Amount: ${amount:,.2f}")
                        self.logger.info(f"   Result: {result}")
                        self.logger.info(f"   Created: {pos.get('created')}")
                else:
                    self.logger.info("❌ No se encontraron posiciones")
            else:
                self.logger.info("❌ No se pudo obtener historial")
                
            # Método alternativo: get_position_history_v2
            if hasattr(self.iqoption, 'get_position_history_v2'):
                self.logger.info("\n📋 Probando get_position_history_v2...")
                try:
                    import time as time_module
                    limit = 10
                    offset = 0
                    start = int(time_module.time() - 3600)
                    end = int(time_module.time())
                    
                    history_v2 = self.api_call_with_timeout(
                        self.iqoption.get_position_history_v2,
                        "binary-option",
                        limit,
                        offset,
                        start,
                        end,
                        timeout=5
                    )
                    if history_v2:
                        self.logger.info(f"✅ get_position_history_v2 funciona")
                except Exception as e:
                    self.logger.info(f"❌ get_position_history_v2 falló: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo historial: {str(e)}")
            self.logger.error(f"Detalles: {traceback.format_exc()}")
    
    def debug_show_all_available_assets(self):
        """
        Método de debugging para mostrar TODOS los activos disponibles
        Útil para ver qué está realmente disponible en IQ Option
        """
        self.logger.info("="*60)
        self.logger.info("🔍 DEBUG: MOSTRANDO TODOS LOS ACTIVOS DISPONIBLES")
        self.logger.info("="*60)
        
        # Obtener todos los activos
        all_assets = self.api_call_with_timeout(self.iqoption.get_all_open_time)
        if not all_assets:
            self.logger.error("❌ No se pudieron obtener los activos")
            return
        
        # Tipos de opciones a verificar
        option_types = ["turbo", "binary", "digital"]
        
        # Recopilar todos los activos por categoría
        categories = {
            'forex': [],
            'indices': [],
            'stocks': [],
            'commodities': [],
            'crypto': []
        }
        
        for option_type in option_types:
            if option_type not in all_assets:
                continue
                
            self.logger.info(f"\n📊 Tipo: {option_type.upper()}")
            self.logger.info("-" * 40)
            
            for asset_name, asset_data in all_assets[option_type].items():
                if asset_data.get("open", False):
                    # Categorizar
                    currency_codes = ["EUR", "USD", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"]
                    indices_keywords = ["500", "100", "225", "30", "40", "NASDAQ", "DAX", "FTSE", "NIKKEI"]
                    commodity_keywords = ["XAU", "XAG", "GOLD", "SILVER", "OIL", "GAS"]
                    crypto_keywords = ["BTC", "ETH", "LTC", "XRP", "CRYPTO"]
                    
                    categorized = False
                    
                    # Detectar categoría
                    if any(keyword in asset_name.upper() for keyword in crypto_keywords):
                        categories['crypto'].append((asset_name, option_type))
                        categorized = True
                    elif any(keyword in asset_name.upper() for keyword in commodity_keywords):
                        categories['commodities'].append((asset_name, option_type))
                        categorized = True
                    elif any(keyword in asset_name.upper() for keyword in indices_keywords):
                        categories['indices'].append((asset_name, option_type))
                        categorized = True
                    elif "#" in asset_name or "-US" in asset_name or "_US" in asset_name:
                        categories['stocks'].append((asset_name, option_type))
                        categorized = True
                    elif sum(1 for curr in currency_codes if curr in asset_name) >= 2:
                        categories['forex'].append((asset_name, option_type))
                        categorized = True
                    
                    # Si no se categorizó, ponerlo en commodities
                    if not categorized:
                        categories['commodities'].append((asset_name, option_type))
        
        # Mostrar por categorías
        category_names = {
            'forex': '💱 FOREX',
            'indices': '📈 ÍNDICES',
            'stocks': '🏢 ACCIONES',
            'commodities': '🏗️ COMMODITIES',
            'crypto': '🪙 CRIPTO'
        }
        
        for cat_key, cat_name in category_names.items():
            if categories[cat_key]:
                self.logger.info(f"\n{cat_name} ({len(categories[cat_key])} activos):")
                seen = set()
                for asset_name, opt_type in sorted(categories[cat_key]):
                    if asset_name not in seen:
                        seen.add(asset_name)
                        self.logger.info(f"   • {asset_name} ({opt_type})")
        
        # Buscar específicamente nuestros activos configurados
        self.logger.info(f"\n🎯 ESTADO DE NUESTROS ACTIVOS CONFIGURADOS:")
        self.logger.info("-" * 40)
        
        for asset in self.trading_assets:
            if asset in self.asset_mapping:
                iq_name = self.asset_mapping[asset]
                found = False
                
                for option_type in ["binary", "turbo"]:
                    if option_type in all_assets and iq_name in all_assets[option_type]:
                        if all_assets[option_type][iq_name].get("open", False):
                            self.logger.info(f"✅ {asset}: Disponible como {iq_name} ({option_type})")
                            found = True
                            break
                
                if not found:
                    self.logger.info(f"❌ {asset}: NO disponible como {iq_name}")
            else:
                self.logger.info(f"⚠️ {asset}: Sin mapeo definido")
        
        self.logger.info("="*60)
    
    def verify_asset_tradeable(self, asset):
        """
        Verificar si un activo realmente se puede operar
        Útil para detectar activos que aparecen abiertos pero están suspendidos
        """
        try:
            asset_name = self.iqoption_assets[asset]
            
            # Intentar obtener el profit del activo
            profit = self.api_call_with_timeout(
                self.iqoption.get_digital_spot_profit_after_sale,
                asset_name
            )
            
            if profit and profit > 0:
                return True
            
            # Si no hay profit, verificar de otra manera
            all_assets = self.api_call_with_timeout(self.iqoption.get_all_open_time)
            option_type = self.asset_option_types[asset]
            
            if all_assets and option_type in all_assets:
                if asset_name in all_assets[option_type]:
                    return all_assets[option_type][asset_name].get("open", False)
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Error verificando {asset}: {str(e)}")
            return False
    
    def handle_trading_error(self, asset, error_message):
        """
        Manejar errores de trading y cambiar a activo alternativo si es necesario
        """
        self.logger.warning(f"⚠️ Error con {self.iqoption_assets[asset]}: {error_message}")
        
        # Si el activo no está disponible, intentar con una variante alternativa
        if "not available" in error_message or "suspended" in error_message:
            self.logger.info(f"🔄 Buscando alternativa para {asset}...")
            
            # Obtener estado actual de activos
            all_assets = self.api_call_with_timeout(self.iqoption.get_all_open_time)
            if not all_assets:
                return False
            
            current_asset = self.iqoption_assets[asset]
            
            # Para activos con mapeo fijo, no hay alternativas
            if asset in self.asset_mapping:
                self.logger.warning(f"❌ {asset} tiene mapeo fijo, no hay alternativas")
                if asset in self.valid_assets:
                    self.valid_assets.remove(asset)
                return False
            
            # Para otros activos, buscar alternativas
            asset_upper = asset.upper()
            alternatives = [
                f"{asset_upper}-OTC",
                asset_upper,
                f"{asset_upper}-op"
            ]
            
            # Quitar el activo actual de las alternativas
            alternatives = [alt for alt in alternatives if alt != current_asset]
            
            # Buscar una alternativa funcional
            for alt_asset in alternatives:
                for option_type in ["binary", "turbo"]:
                    if option_type in all_assets and alt_asset in all_assets[option_type]:
                        if all_assets[option_type][alt_asset].get("open", False):
                            # Actualizar a la alternativa
                            self.logger.info(f"✅ Cambiando {asset} de {current_asset} a {alt_asset} ({option_type})")
                            self.iqoption_assets[asset] = alt_asset
                            self.asset_option_types[asset] = option_type
                            return True
            
            # Si no hay alternativas, eliminar el activo temporalmente
            self.logger.warning(f"❌ No hay alternativas disponibles para {asset}, eliminándolo temporalmente")
            if asset in self.valid_assets:
                self.valid_assets.remove(asset)
            return False
        
        return True
    
    def calculate_position_size(self):
        """Calcular tamaño de posición basado en el capital actual (2.5% sin límite máximo)"""
        current_capital = self.api_call_with_timeout(self.iqoption.get_balance)
        if current_capital is None:
            current_capital = self.initial_capital
        
        # Calcular 2.5% del capital actual
        position_size = round(current_capital * self.position_size_percent, 2)
        
        # Solo aplicar límite mínimo (no hay límite máximo)
        position_size = max(self.min_position_size, position_size)
        
        self.logger.debug(f"💰 Capital: ${current_capital:,.2f} → Posición: ${position_size:,.2f} ({self.position_size_percent*100}%)")
        
        return position_size
    
    def get_rsi(self, asset):
        """Obtener RSI para un activo específico usando velas de 5 minutos"""
        try:
            # Asegurarnos de usar timeframe de 5 minutos (300 segundos)
            candles = self.api_call_with_timeout(
                self.iqoption.get_candles,
                self.iqoption_assets[asset],
                300,  # 5 minutos
                100,
                time.time()
            )
            
            if candles and len(candles) >= self.rsi_period:
                rsi = calculate_rsi(candles, self.rsi_period)
                if rsi is not None:
                    self.logger.debug(f"📊 {asset} - RSI(5min): {rsi:.2f}")
                return rsi
            
            self.logger.warning(f"⚠️ No se pudo calcular RSI para {asset}")
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo RSI para {asset}: {str(e)}")
            return None
    
    def place_option(self, asset, direction, amount):
        """Colocar una opción binaria con reintentos automáticos"""
        max_retries = 2
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                asset_name = self.iqoption_assets[asset]
                option_type = self.asset_option_types[asset]
                
                self.logger.info(f"📈 Colocando {direction} en {asset} ({asset_name}), cantidad: {format_currency(amount)}")
                
                status, order_id = self.api_call_with_timeout(
                    self.iqoption.buy,
                    int(amount),
                    asset_name,
                    direction.lower(),
                    self.expiry_minutes
                )
                
                if status:
                    self.logger.info(f"✅ Orden colocada exitosamente. ID: {order_id}")
                    return order_id
                else:
                    # Manejar el error
                    error_msg = str(order_id) if order_id else "Error desconocido"
                    
                    # Si es un error de disponibilidad y tenemos reintentos
                    if retry_count < max_retries - 1 and ("not available" in error_msg or "suspended" in error_msg):
                        if self.handle_trading_error(asset, error_msg):
                            retry_count += 1
                            self.logger.info(f"🔄 Reintentando con activo alternativo... (intento {retry_count + 1}/{max_retries})")
                            time.sleep(1)  # Pequeña pausa antes de reintentar
                            continue
                    
                    self.logger.error(f"❌ Error colocando orden: {error_msg}")
                    return None
                    
            except Exception as e:
                self.logger.error(f"❌ Excepción colocando orden: {str(e)}")
                
                # Si es un error de conexión/timeout y tenemos reintentos
                if retry_count < max_retries - 1:
                    retry_count += 1
                    self.logger.info(f"🔄 Reintentando... (intento {retry_count + 1}/{max_retries})")
                    time.sleep(2)
                    continue
                
                return None
        
        return None
    
    def process_asset(self, asset):
        """Procesar señales para un activo"""
        # Verificar si estamos en período de calentamiento
        if time.time() < self.warmup_end_time:
            remaining_minutes = (self.warmup_end_time - time.time()) / 60
            if remaining_minutes > 0:
                self.logger.debug(f"⏳ En calentamiento - faltan {remaining_minutes:.1f} minutos")
                return
        
        # Verificar si hay órdenes activas
        if len(self.active_options.get(asset, [])) > 0:
            return
        
        # Verificar tiempo desde última señal (ahora 1 hora)
        time_since_last = (datetime.now() - self.last_signal_time.get(asset, datetime.min)).total_seconds() / 60
        if time_since_last < self.min_time_between_signals:
            return
        
        # Obtener RSI
        current_rsi = self.get_rsi(asset)
        if current_rsi is None:
            return
        
        # Generar señal - LÓGICA INVERTIDA
        signal = None
        if current_rsi <= self.oversold_level:
            signal = "PUT"  # INVERTIDO: Sobreventa genera PUT
            self.logger.info(f"🔴 {asset} - Señal PUT (RSI: {current_rsi:.2f})")
        elif current_rsi >= self.overbought_level:
            signal = "CALL"  # INVERTIDO: Sobrecompra genera CALL
            self.logger.info(f"🟢 {asset} - Señal CALL (RSI: {current_rsi:.2f})")
        
        if signal:
            self.create_binary_option(asset, signal, current_rsi)
            self.last_signal_time[asset] = datetime.now()
    
    def create_binary_option(self, asset, direction, rsi_value):
        """Crear una opción binaria"""
        # Calcular tamaño de posición
        bet_size = self.calculate_position_size()
        
        # Verificar capital disponible
        current_balance = self.api_call_with_timeout(self.iqoption.get_balance)
        if current_balance is None or current_balance < bet_size:
            self.logger.warning(f"⚠️ Capital insuficiente para {asset}")
            return
        
        # Colocar orden
        order_id = self.place_option(asset, direction, bet_size)
        
        if order_id:
            # Registrar orden activa
            order_info = {
                "id": order_id,
                "type": direction,
                "asset": asset,
                "size": bet_size,
                "entry_time": datetime.now(),
                "expiry_time": datetime.now() + timedelta(minutes=self.expiry_minutes),
                "rsi": rsi_value,
                "balance_before": current_balance  # NUEVO: Guardar balance antes
            }
            self.active_options[asset].append(order_info)
            self.logger.info(f"📝 Orden registrada para {asset}")
    
    def check_active_orders(self):
        """Verificar el estado de las órdenes activas"""
        current_time = datetime.now()
        
        for asset in list(self.active_options.keys()):
            remaining_orders = []
            
            for order in self.active_options[asset]:
                # Calcular tiempo desde expiración
                time_since_expiry = (current_time - order["expiry_time"]).total_seconds()
                
                # Si la orden expiró hace más de 15 segundos, procesarla
                if time_since_expiry > 15:
                    self.process_expired_order(asset, order)
                # Si expiró pero es muy reciente, esperar un poco más
                elif order["expiry_time"] <= current_time:
                    self.logger.debug(f"⏳ Orden {order['id']} expiró hace {time_since_expiry:.0f}s, esperando...")
                    remaining_orders.append(order)
                else:
                    remaining_orders.append(order)
            
            if remaining_orders:
                self.active_options[asset] = remaining_orders
            else:
                del self.active_options[asset]
    
    def process_expired_order(self, asset, order):
        """Procesar una orden expirada - VERSIÓN FINAL CON TODOS LOS MÉTODOS"""
        try:
            self.logger.info(f"🔄 Verificando orden {order['id']}...")
            
            # Verificar tiempo desde expiración
            time_since_expiry = (datetime.now() - order["expiry_time"]).total_seconds()
            
            # Si es muy reciente, esperar
            if time_since_expiry < 10:
                self.logger.info(f"⏳ Orden muy reciente ({time_since_expiry:.0f}s), esperando...")
                return
            
            # Variables para resultado
            result_found = False
            win_status = None
            win_amount = 0
            
            # MÉTODO 1: Verificar en api.order_binary (MÁS CONFIABLE)
            if hasattr(self.iqoption.api, 'order_binary') and order['id'] in self.iqoption.api.order_binary:
                order_data = self.iqoption.api.order_binary[order['id']]
                self.logger.info(f"📋 Orden encontrada en order_binary")
                
                # Leer el resultado directamente
                if 'result' in order_data:
                    result = order_data['result'].lower()
                    if result == 'win':
                        win_status = 'win'
                        # Calcular ganancia
                        profit_percent = order_data.get('profit_percent', 85)
                        win_amount = order["size"] * (1 + profit_percent / 100)
                        result_found = True
                        self.logger.info(f"   Result: WIN (profit: {profit_percent}%)")
                    elif result == 'loose':
                        win_status = 'loose'
                        win_amount = 0
                        result_found = True
                        self.logger.info(f"   Result: LOOSE")
                    elif result == 'equal':
                        win_status = 'equal'
                        win_amount = order["size"]
                        result_found = True
                        self.logger.info(f"   Result: EQUAL")
            
            # MÉTODO 2: Verificar en api.listinfodata
            if not result_found and hasattr(self.iqoption.api, 'listinfodata') and isinstance(self.iqoption.api.listinfodata, dict):
                self.logger.debug("📋 Buscando en listinfodata...")
                for key, value in self.iqoption.api.listinfodata.items():
                    if isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict) and str(item.get('id')) == str(order['id']):
                                result_found = True
                                win_status = str(item.get('win', '')).lower()
                                win_amount = float(item.get('win_amount', 0))
                                
                                self.logger.info(f"📋 Orden encontrada en listinfodata:")
                                self.logger.info(f"   Win: {win_status}")
                                self.logger.info(f"   Win Amount: {win_amount}")
                                break
                    if result_found:
                        break
            
            # MÉTODO 3: Verificar por balance (para cuentas REAL)
            if not result_found and 'balance_before' in order:
                current_balance = self.api_call_with_timeout(self.iqoption.get_balance)
                if current_balance is not None:
                    balance_diff = current_balance - order['balance_before']
                    
                    self.logger.info(f"📊 Verificación por balance:")
                    self.logger.info(f"   Balance antes: ${order['balance_before']:,.2f}")
                    self.logger.info(f"   Balance ahora: ${current_balance:,.2f}")
                    self.logger.info(f"   Diferencia: ${balance_diff:+,.2f}")
                    
                    # Solo usar balance si hay cambio significativo
                    if abs(balance_diff) > 0.1:
                        if balance_diff > 0:
                            win_status = 'win'
                            win_amount = order["size"] + balance_diff
                            result_found = True
                        else:
                            win_status = 'loose'
                            win_amount = 0
                            result_found = True
            
            # MÉTODO 4: Intentar get_async_order como último recurso
            if not result_found and time_since_expiry > 20:
                self.logger.info("📋 Intentando get_async_order...")
                order_result = self.api_call_with_timeout(
                    self.iqoption.get_async_order,
                    order["id"],
                    timeout=3
                )
                
                if order_result and isinstance(order_result, dict):
                    # Procesar con la lógica original
                    self._process_order_result(asset, order, order_result)
                    return
            
            # Procesar resultado si se encontró
            if result_found and win_status:
                bet_size = order["size"]
                
                if win_status == 'win':
                    self.logger.info(f"✅ Victoria detectada")
                    self.process_win(asset, order, win_amount)
                elif win_status == 'equal':
                    self.logger.info(f"🟡 Empate detectado")
                    self.process_tie(asset, order)
                elif win_status == 'loose':
                    self.logger.info(f"❌ Pérdida detectada")
                    self.process_loss(asset, order)
                else:
                    # Si no podemos determinar, verificar por monto
                    if win_amount > bet_size:
                        self.process_win(asset, order, win_amount)
                    elif win_amount == bet_size:
                        self.process_tie(asset, order)
                    else:
                        self.process_loss(asset, order)
                return
            
            # Si han pasado más de 2 minutos y no hay resultado, asumir pérdida
            if time_since_expiry > 120:
                self.logger.error(f"❌ No se pudo verificar orden después de {time_since_expiry:.0f}s")
                self.logger.error(f"❌ Asumiendo pérdida por timeout")
                self.process_loss(asset, order)
                
        except Exception as e:
            self.logger.error(f"❌ Error procesando orden expirada: {str(e)}")
            self.logger.error(f"Detalles: {traceback.format_exc()}")
            # En caso de error, registrar como pérdida para ser conservadores
            self.process_loss(asset, order)
    
    def _process_order_result(self, asset, order, order_result):
        """Procesar resultado de orden desde get_async_order"""
        bet_size = order["size"]
        is_win = False
        is_tie = False
        win_amount = 0
        
        # Log detallado
        for key, value in order_result.items():
            self.logger.info(f"   {key}: {value}")
        
        # Método 1: Campo 'win' directo
        if "win" in order_result:
            win_status = str(order_result["win"]).lower()
            self.logger.info(f"   Campo 'win' encontrado: {win_status}")
            
            if win_status == "win":
                is_win = True
                # Buscar el monto ganado
                if "win_amount" in order_result:
                    win_amount = float(order_result["win_amount"])
                elif "profit_amount" in order_result:
                    profit = float(order_result["profit_amount"])
                    win_amount = bet_size + profit
                else:
                    # Asumir 80% payout
                    win_amount = bet_size * 1.80
                    
            elif win_status == "equal":
                is_tie = True
                win_amount = bet_size
            else:
                is_win = False
                win_amount = 0
        
        # Método 2: Otros campos
        elif "win_amount" in order_result:
            win_amount = float(order_result.get("win_amount", 0))
            if win_amount > bet_size:
                is_win = True
            elif win_amount == bet_size:
                is_tie = True
            else:
                is_win = False
        
        # Procesar según resultado
        if is_win:
            self.process_win(asset, order, win_amount)
        elif is_tie:
            self.process_tie(asset, order)
        else:
            self.process_loss(asset, order)
    
    def process_win(self, asset, order, win_amount):
        """Procesar una operación ganadora"""
        profit = win_amount - order["size"]
        self.logger.info(f"✅ {asset} - {order['type']} GANADA! Beneficio: {format_currency(profit)}")
        
        self.wins[asset] += 1
        self.total_profit += profit
        self.daily_profit += profit
        self.consecutive_losses[asset] = 0
        
        # Resetear pérdidas consecutivas diarias
        if self.daily_consecutive_losses > 0:
            self.logger.info(f"✅ Pérdidas consecutivas diarias reseteadas: {self.daily_consecutive_losses} → 0")
            self.daily_consecutive_losses = 0
    
    def process_tie(self, asset, order):
        """Procesar una operación empatada (On The Money)"""
        self.logger.info(f"🟡 {asset} - {order['type']} EMPATE (On The Money). Sin ganancia ni pérdida")
        
        # En un empate no se cuentan pérdidas consecutivas
        # pero tampoco se resetean
        self.ties[asset] += 1
        # No afecta el profit total ni las pérdidas consecutivas
        # Los empates NO resetean ni incrementan las pérdidas consecutivas diarias
    
    def process_loss(self, asset, order):
        """Procesar una operación perdedora"""
        loss = order["size"]
        self.logger.info(f"❌ {asset} - {order['type']} PERDIDA. Pérdida: {format_currency(loss)}")
        
        self.losses[asset] += 1
        self.total_profit -= loss
        self.daily_profit -= loss
        self.consecutive_losses[asset] += 1
        
        # Incrementar pérdidas consecutivas diarias
        self.daily_consecutive_losses += 1
        
        self.logger.info(f"📊 {asset} - Pérdidas consecutivas: {self.consecutive_losses[asset]}")
        self.logger.info(f"📊 Pérdidas consecutivas del día: {self.daily_consecutive_losses}/{self.max_daily_consecutive_losses}")
        
        # Verificar si alcanzamos el límite diario
        if self.daily_consecutive_losses >= self.max_daily_consecutive_losses and not self.daily_loss_lock:
            self.activate_daily_loss_lock()
        
        # Guardar estado después de cada pérdida
        self.save_state()
    
    def activate_daily_loss_lock(self):
        """Activar el bloqueo diario por pérdidas consecutivas"""
        self.daily_loss_lock = True
        self.daily_loss_lock_time = datetime.now()
        
        # Obtener balance actual para mostrar
        current_balance = self.api_call_with_timeout(self.iqoption.get_balance)
        
        self.logger.info("=" * 60)
        self.logger.info("❌ LÍMITE DE PÉRDIDAS CONSECUTIVAS ALCANZADO")
        self.logger.info("=" * 60)
        self.logger.info(f"📊 Pérdidas consecutivas: {self.daily_consecutive_losses}")
        self.logger.info(f"💰 Profit del día: {format_currency(self.daily_profit)}")
        self.logger.info(f"📊 Balance actual: {format_currency(current_balance)}")
        self.logger.info(f"🕐 Hora: {self.daily_loss_lock_time.strftime('%H:%M:%S')}")
        self.logger.info("🛑 Trading pausado por el resto del día")
        self.logger.info("🔄 El trading se reanudará mañana")
        self.logger.info("=" * 60)
    
    def check_stop_loss(self):
        """Verificar condiciones de stop loss"""
        current_capital = self.api_call_with_timeout(self.iqoption.get_balance)
        if current_capital is None:
            return True
        
        # Actualizar capital mínimo
        if current_capital < self.min_capital:
            self.min_capital = current_capital
            loss_percent = ((self.initial_capital - self.min_capital) / self.initial_capital) * 100
            self.logger.info(f"📉 Nuevo mínimo: {format_currency(self.min_capital)} ({loss_percent:.2f}% pérdida)")
        
        # Stop loss absoluto
        if current_capital <= self.absolute_stop_loss_threshold and not self.absolute_stop_loss_activated:
            self.absolute_stop_loss_activated = True
            self.logger.critical("🚨 STOP LOSS ABSOLUTO ACTIVADO!")
            self.logger.critical(f"Capital: {format_currency(current_capital)} (75% de pérdida)")
            return False
        
        if self.absolute_stop_loss_activated:
            return False
        
        # Stop loss mensual
        current_month = f"{datetime.now().year}-{datetime.now().month:02d}"
        
        if self.current_month != current_month:
            self.on_new_month(current_month, current_capital)
        
        if self.monthly_stop_loss and self.stop_loss_triggered_month == current_month:
            return False
        
        monthly_start = self.monthly_starting_capital.get(current_month, self.initial_capital)
        monthly_threshold = monthly_start * (1 - MONTHLY_STOP_LOSS_PERCENT)
        
        if current_capital <= monthly_threshold and not self.monthly_stop_loss:
            self.monthly_stop_loss = True
            self.stop_loss_triggered_month = current_month
            self.logger.critical("🚨 STOP LOSS MENSUAL ACTIVADO!")
            self.logger.critical(f"Pérdida del mes: 40%")
            return False
        
        return True
    
    def check_daily_profit_lock(self):
        """Verificar si debemos parar de operar por profit diario"""
        # Si ya está activado el lock, solo mostrar mensaje periódicamente
        if self.daily_profit_lock:
            if time.time() % 600 < 15:  # Cada 10 minutos aproximadamente
                self.logger.info(f"🔒 Trading pausado - Profit diario alcanzado: {format_currency(self.daily_profit_lock_amount)}")
            time.sleep(15)  # Dormir un poco más cuando está en lock
            return True
        
        # Solo verificar si no hay posiciones abiertas
        if len(self.active_options) > 0:
            return False
        
        # Verificar si el día es rentable
        if self.daily_profit > 0:
            self.daily_profit_lock = True
            self.daily_profit_lock_amount = self.daily_profit
            self.daily_profit_lock_time = datetime.now()
            
            # Obtener balance actual para mostrar
            current_balance = self.api_call_with_timeout(self.iqoption.get_balance)
            
            self.logger.info("=" * 60)
            self.logger.info("🎯 OBJETIVO DIARIO ALCANZADO - TRADING PAUSADO")
            self.logger.info("=" * 60)
            self.logger.info(f"💰 Profit del día: {format_currency(self.daily_profit)}")
            self.logger.info(f"📊 Balance actual: {format_currency(current_balance)}")
            self.logger.info(f"🕐 Hora: {self.daily_profit_lock_time.strftime('%H:%M:%S')}")
            self.logger.info("✅ No se realizarán más operaciones hoy")
            self.logger.info("🔄 El trading se reanudará mañana")
            self.logger.info("=" * 60)
            
            return True
        
        return False
    
    def check_daily_loss_lock(self):
        """Verificar si el trading está bloqueado por pérdidas consecutivas"""
        if self.daily_loss_lock:
            if time.time() % 600 < 15:  # Cada 10 minutos aproximadamente
                self.logger.info(f"🔒 Trading pausado - {self.daily_consecutive_losses} pérdidas consecutivas alcanzadas")
            time.sleep(15)
            return True
        return False
    
    def on_new_day(self):
        """Resetear variables diarias"""
        self.logger.info("🌅 Reseteando variables para nuevo día de trading")
        
        # Resetear daily profit lock
        if self.daily_profit_lock:
            self.logger.info(f"🔓 Desbloqueando trading - Profit del día anterior: {format_currency(self.daily_profit_lock_amount)}")
            self.daily_profit_lock = False
            self.daily_profit_lock_amount = 0.0
            self.daily_profit_lock_time = None
        
        # Resetear daily loss lock
        if self.daily_loss_lock:
            self.logger.info(f"🔓 Desbloqueando trading - {self.daily_consecutive_losses} pérdidas consecutivas del día anterior")
            self.daily_loss_lock = False
            self.daily_loss_lock_time = None
        
        # Resetear contador de pérdidas consecutivas diarias
        if self.daily_consecutive_losses > 0:
            self.logger.info(f"✅ Reseteando pérdidas consecutivas diarias: {self.daily_consecutive_losses} → 0")
            self.daily_consecutive_losses = 0
        
        # Resetear pérdidas consecutivas por activo (esto sí lo mantenemos para estadísticas)
        for asset in list(self.consecutive_losses.keys()):
            if self.consecutive_losses[asset] > 0:
                self.logger.info(f"✅ Reseteando pérdidas consecutivas de {asset}: {self.consecutive_losses[asset]} → 0")
            self.consecutive_losses[asset] = 0
        
        # Actualizar beneficios mensuales
        if self.last_date:
            month_key = f"{self.last_date.year}-{self.last_date.month:02d}"
            self.monthly_profits[month_key] += self.daily_profit
        
        self.daily_profit = 0
        self.last_date = datetime.now().date()
        self.logger.info("✅ Variables diarias reseteadas")
    
    def on_new_month(self, new_month, current_capital):
        """Manejar cambio de mes"""
        self.logger.info(f"📅 NUEVO MES: {new_month}")
        self.monthly_starting_capital[new_month] = current_capital
        self.current_month = new_month
        
        # Resetear stop loss mensual si aplica
        if self.monthly_stop_loss:
            self.monthly_stop_loss = False
            self.stop_loss_triggered_month = None
            self.logger.info("✅ Stop loss mensual reseteado")
    
    def save_state(self):
        """Guardar estado actual de la estrategia"""
        try:
            state = {
                "timestamp": datetime.now().isoformat(),
                "strategy_mode": STRATEGY_MODE,
                "active_options": {
                    asset: [
                        {
                            **order,
                            "entry_time": order["entry_time"].isoformat(),
                            "expiry_time": order["expiry_time"].isoformat()
                        }
                        for order in orders
                    ]
                    for asset, orders in self.active_options.items()
                },
                "last_signal_time": {
                    asset: time.isoformat() if time != datetime.min else "datetime.min"
                    for asset, time in self.last_signal_time.items()
                },
                "consecutive_losses": dict(self.consecutive_losses),
                "daily_lockouts": dict(self.daily_lockouts),
                "wins": dict(self.wins),
                "losses": dict(self.losses),
                "ties": dict(self.ties),  # Guardar empates
                "total_profit": self.total_profit,
                "daily_profit": self.daily_profit,
                "monthly_profits": dict(self.monthly_profits),
                "monthly_starting_capital": self.monthly_starting_capital,
                "monthly_stop_loss": self.monthly_stop_loss,
                "stop_loss_triggered_month": self.stop_loss_triggered_month,
                "absolute_stop_loss_activated": self.absolute_stop_loss_activated,
                "min_capital": self.min_capital,
                "last_date": self.last_date.isoformat() if self.last_date else None,
                "current_month": self.current_month,
                "daily_profit_lock": self.daily_profit_lock,
                "daily_profit_lock_amount": self.daily_profit_lock_amount,
                "daily_profit_lock_time": self.daily_profit_lock_time.isoformat() if self.daily_profit_lock_time else None,
                "daily_consecutive_losses": self.daily_consecutive_losses,
                "daily_loss_lock": self.daily_loss_lock,
                "daily_loss_lock_time": self.daily_loss_lock_time.isoformat() if self.daily_loss_lock_time else None,
                "max_daily_consecutive_losses": self.max_daily_consecutive_losses
            }
            
            with open(STATE_FILE, "w") as f:
                json.dump(state, f, indent=4)
            
            self.logger.debug("💾 Estado guardado correctamente")
            
        except Exception as e:
            self.logger.error(f"❌ Error guardando estado: {str(e)}")
    
    def load_state(self):
        """Cargar estado previo si existe"""
        try:
            if not os.path.exists(STATE_FILE):
                self.logger.info("📂 No hay archivo de estado previo")
                self.last_date = datetime.now().date()
                self.current_month = f"{datetime.now().year}-{datetime.now().month:02d}"
                self.monthly_starting_capital[self.current_month] = self.initial_capital
                return
            
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
            
            # Cargar órdenes activas
            self.active_options = defaultdict(list)
            for asset, orders in state.get("active_options", {}).items():
                for order in orders:
                    order["entry_time"] = datetime.fromisoformat(order["entry_time"])
                    order["expiry_time"] = datetime.fromisoformat(order["expiry_time"])
                    # Compatibilidad: cambiar 'pair' a 'asset' si existe
                    if 'pair' in order and 'asset' not in order:
                        order['asset'] = order.pop('pair')
                    self.active_options[asset].append(order)
            
            # Cargar tiempos de última señal
            self.last_signal_time = defaultdict(lambda: datetime.min)
            for asset, time_str in state.get("last_signal_time", {}).items():
                if time_str == "datetime.min":
                    self.last_signal_time[asset] = datetime.min
                else:
                    self.last_signal_time[asset] = datetime.fromisoformat(time_str)
            
            # Cargar estadísticas
            self.consecutive_losses = defaultdict(int, state.get("consecutive_losses", {}))
            self.daily_lockouts = defaultdict(bool, state.get("daily_lockouts", {}))
            self.wins = defaultdict(int, state.get("wins", {}))
            self.losses = defaultdict(int, state.get("losses", {}))
            self.ties = defaultdict(int, state.get("ties", {}))  # Cargar empates
            self.total_profit = state.get("total_profit", 0)
            self.daily_profit = state.get("daily_profit", 0)
            self.monthly_profits = defaultdict(float, state.get("monthly_profits", {}))
            self.monthly_starting_capital = state.get("monthly_starting_capital", {})
            self.monthly_stop_loss = state.get("monthly_stop_loss", False)
            self.stop_loss_triggered_month = state.get("stop_loss_triggered_month", None)
            self.absolute_stop_loss_activated = state.get("absolute_stop_loss_activated", False)
            self.min_capital = state.get("min_capital", self.initial_capital)
            
            # Cargar daily profit lock
            self.daily_profit_lock = state.get("daily_profit_lock", False)
            self.daily_profit_lock_amount = state.get("daily_profit_lock_amount", 0.0)
            lock_time = state.get("daily_profit_lock_time")
            if lock_time:
                self.daily_profit_lock_time = datetime.fromisoformat(lock_time)
            else:
                self.daily_profit_lock_time = None
            
            # Cargar daily loss lock
            self.daily_consecutive_losses = state.get("daily_consecutive_losses", 0)
            self.daily_loss_lock = state.get("daily_loss_lock", False)
            loss_lock_time = state.get("daily_loss_lock_time")
            if loss_lock_time:
                self.daily_loss_lock_time = datetime.fromisoformat(loss_lock_time)
            else:
                self.daily_loss_lock_time = None
            self.max_daily_consecutive_losses = state.get("max_daily_consecutive_losses", 3)
            
            # Cargar fechas
            last_date_str = state.get("last_date")
            if last_date_str:
                self.last_date = datetime.fromisoformat(last_date_str).date()
            else:
                self.last_date = datetime.now().date()
            
            self.current_month = state.get("current_month", f"{datetime.now().year}-{datetime.now().month:02d}")
            
            self.logger.info(f"✅ Estado cargado desde {state.get('timestamp', 'N/A')}")
            
        except Exception as e:
            self.logger.error(f"❌ Error cargando estado: {str(e)}")
            self.last_date = datetime.now().date()
            self.current_month = f"{datetime.now().year}-{datetime.now().month:02d}"
            self.monthly_starting_capital[self.current_month] = self.initial_capital
    
    def print_summary(self):
        """Imprimir resumen de la estrategia"""
        current_capital = self.api_call_with_timeout(self.iqoption.get_balance)
        if current_capital is None:
            current_capital = self.initial_capital
        
        self.logger.info("=" * 60)
        self.logger.info("📊 RESUMEN DE LA ESTRATEGIA RSI MULTI-ACTIVOS (LÓGICA INVERTIDA)")
        self.logger.info("=" * 60)
        self.logger.info("⚡ Estrategia: PUT en sobreventa (RSI≤35), CALL en sobrecompra (RSI≥65)")
        self.logger.info(f"💰 Capital Inicial: {format_currency(self.initial_capital)}")
        self.logger.info(f"💰 Balance Final: {format_currency(current_capital)}")
        
        total_return = ((current_capital - self.initial_capital) / self.initial_capital) * 100
        self.logger.info(f"📈 Rendimiento Total: {total_return:.2f}%")
        
        # Estadísticas por operaciones
        total_wins = sum(self.wins.values())
        total_losses = sum(self.losses.values())
        total_ties = sum(self.ties.values())
        total_trades = total_wins + total_losses + total_ties
        
        self.logger.info(f"🎯 Total Operaciones: {total_trades}")
        if total_trades > 0:
            win_rate = calculate_win_rate(total_wins, total_losses)
            self.logger.info(f"✅ Victorias: {total_wins} ({total_wins/total_trades*100:.1f}%)")
            self.logger.info(f"❌ Derrotas: {total_losses} ({total_losses/total_trades*100:.1f}%)")
            self.logger.info(f"🟡 Empates: {total_ties} ({total_ties/total_trades*100:.1f}%)")
            self.logger.info(f"📊 Tasa de Éxito (sin empates): {win_rate:.2f}%")
        
        self.logger.info(f"💵 Beneficio Neto: {format_currency(self.total_profit)}")
        self.logger.info(f"📉 Capital Mínimo: {format_currency(self.min_capital)}")
        
        # Stop losses activados
        if self.absolute_stop_loss_activated:
            self.logger.info("🚨 Stop Loss Absoluto: ACTIVADO")
        if self.monthly_stop_loss:
            self.logger.info(f"🚨 Stop Loss Mensual: ACTIVADO en {self.stop_loss_triggered_month}")
        
        # Daily profit lock
        if self.daily_profit_lock:
            self.logger.info(f"🔒 Daily Profit Lock: ACTIVO desde {self.daily_profit_lock_time.strftime('%H:%M')}")
        
        # Daily loss lock
        if self.daily_loss_lock:
            self.logger.info(f"🔒 Daily Loss Lock: ACTIVO desde {self.daily_loss_lock_time.strftime('%H:%M')} ({self.daily_consecutive_losses} pérdidas)")
        
        # Estadísticas por activo
        self.logger.info("\n📊 Estadísticas por Activo:")
        for asset in self.trading_assets:
            if asset in self.wins or asset in self.losses or asset in self.ties:
                asset_wins = self.wins.get(asset, 0)
                asset_losses = self.losses.get(asset, 0)
                asset_ties = self.ties.get(asset, 0)
                asset_total = asset_wins + asset_losses + asset_ties
                if asset_total > 0:
                    asset_wr = (asset_wins / (asset_wins + asset_losses) * 100) if (asset_wins + asset_losses) > 0 else 0
                    cons_losses = self.consecutive_losses.get(asset, 0)
                    self.logger.info(f"{asset}: {asset_total} trades | {asset_wins}W/{asset_losses}L/{asset_ties}T | {asset_wr:.1f}% éxito | Pérdidas consecutivas: {cons_losses}")
        
        # Rendimiento mensual
        self.logger.info("\n📅 Rendimiento Mensual:")
        for month in sorted(self.monthly_profits.keys()):
            monthly_profit = self.monthly_profits[month]
            tag = " (STOP LOSS)" if month == self.stop_loss_triggered_month else ""
            self.logger.info(f"{month}: {format_currency(monthly_profit)}{tag}")
        
        self.logger.info("=" * 60)
    
    def run(self):
        """Ejecutar la estrategia principal"""
        self.logger.info("🚀 Iniciando estrategia RSI Multi-Activos (LÓGICA INVERTIDA)")
        self.logger.info(f"📊 Configuración: {len(self.valid_assets)} activos disponibles")
        self.logger.info("⚡ IMPORTANTE: PUT en RSI≤35 (sobreventa), CALL en RSI≥65 (sobrecompra)")
        self.logger.info(f"⏰ Tiempo entre señales: {self.min_time_between_signals} minutos (1 hora)")
        self.logger.info("🔄 Sin bloqueo por pérdidas consecutivas")
        self.logger.info(f"💰 Tamaño de posición: {self.position_size_percent*100}% del capital (sin límite máximo)")
        
        cycle_count = 0
        
        try:
            while True:
                cycle_start = time.time()
                cycle_count += 1
                
                # Log periódico
                if cycle_count % 10 == 0:
                    self.logger.info(f"🔄 Ciclo #{cycle_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # Mostrar estado de calentamiento si aplica
                    if time.time() < self.warmup_end_time:
                        remaining = (self.warmup_end_time - time.time()) / 60
                        self.logger.info(f"⏳ Período de calentamiento: {remaining:.1f} minutos restantes")
                    elif cycle_count == 10:  # Primera vez después del calentamiento
                        self.logger.info("✅ Período de calentamiento completado - Operaciones habilitadas")
                
                # Verificar conexión
                if not self.iqoption.check_connect():
                    self.logger.warning("🔌 Reconectando...")
                    self._connect_to_iq_option(IQ_EMAIL, IQ_PASSWORD, ACCOUNT_TYPE)
                    time.sleep(5)
                    continue
                
                # Verificar stop loss
                if not self.check_stop_loss():
                    self.logger.info("🛑 Stop loss activo. Esperando...")
                    time.sleep(300)  # Esperar 5 minutos
                    continue
                
                # Verificar daily profit lock
                if self.check_daily_profit_lock():
                    continue
                
                # Verificar daily loss lock
                if self.check_daily_loss_lock():
                    continue
                
                # Verificar órdenes activas
                self.check_active_orders()
                
                # Verificar nuevo día
                current_date = datetime.now().date()
                if self.last_date != current_date:
                    self.on_new_day()
                
                # Procesar cada activo disponible
                for asset in self.valid_assets:
                    try:
                        self.process_asset(asset)
                    except Exception as e:
                        self.logger.error(f"❌ Error procesando {asset}: {str(e)}")
                
                # Guardar estado periódicamente
                if cycle_count % SAVE_STATE_INTERVAL == 0:
                    self.save_state()
                
                # Re-verificar activos periódicamente
                if cycle_count % 100 == 0:
                    self.logger.info("🔄 Re-verificando activos disponibles...")
                    self.check_valid_assets()
                
                # Control de tiempo del ciclo
                cycle_duration = time.time() - cycle_start
                sleep_time = max(5.0, 15.0 - cycle_duration)  # Mínimo 5 segundos entre ciclos
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            self.logger.info("⏹️ Estrategia detenida por el usuario")
        except Exception as e:
            self.logger.critical(f"🚨 Error crítico: {str(e)}")
            self.logger.critical(traceback.format_exc())
        finally:
            self.logger.info("🏁 Finalizando estrategia...")
            self.save_state()
            self.print_summary()
            
            # Cerrar executor
            if hasattr(self, 'executor'):
                self.executor.shutdown(wait=True)
            
            self.logger.info("👋 Estrategia finalizada")
    
    def __del__(self):
        """Limpieza al destruir el objeto"""
        try:
            if hasattr(self, 'executor'):
                self.executor.shutdown(wait=False)
        except:
            pass


# Alias para compatibilidad con main.py
MultiCurrencyRSIBinaryOptionsStrategy = MultiAssetRSIBinaryOptionsStrategy