# working_solution.py
# Solución funcional que no depende de get_position_history

import time
from datetime import datetime
from iqoptionapi.stable_api import IQ_Option
from config import *

class OrderTracker:
    """Clase para rastrear órdenes y sus resultados"""
    
    def __init__(self, iq):
        self.iq = iq
        self.orders = {}  # Almacenar órdenes activas
        
    def add_order(self, order_id, amount, asset, direction):
        """Registrar una nueva orden"""
        self.orders[order_id] = {
            'amount': amount,
            'asset': asset,
            'direction': direction,
            'start_time': time.time(),
            'balance_before': self.iq.get_balance(),
            'status': 'active'
        }
        print(f"📝 Orden registrada: {order_id}")
        
    def check_order_result(self, order_id, expiry_minutes=1):
        """Verificar el resultado de una orden"""
        if order_id not in self.orders:
            return None
            
        order = self.orders[order_id]
        
        # Método 1: Verificar por balance
        current_balance = self.iq.get_balance()
        balance_diff = current_balance - order['balance_before']
        
        # Método 2: Buscar en api.listinfodata
        result_from_api = self._find_in_listinfodata(order_id)
        
        # Método 3: Buscar en api.order_binary
        if hasattr(self.iq.api, 'order_binary') and order_id in self.iq.api.order_binary:
            order_data = self.iq.api.order_binary[order_id]
            print(f"📋 Datos de order_binary: {order_data}")
        
        # Determinar resultado
        result = {
            'order_id': order_id,
            'amount': order['amount'],
            'balance_diff': balance_diff,
            'api_result': result_from_api
        }
        
        # Interpretar resultado
        if balance_diff > 0:
            result['status'] = 'win'
            result['profit'] = balance_diff
            print(f"✅ GANANCIA detectada por balance: +${balance_diff:.2f}")
        elif balance_diff < 0:
            result['status'] = 'loss'
            result['profit'] = balance_diff
            print(f"❌ PÉRDIDA detectada por balance: ${balance_diff:.2f}")
        else:
            result['status'] = 'pending'
            print(f"⏳ Sin cambio en balance aún")
            
        # Si encontramos datos en la API, usar esos
        if result_from_api:
            if result_from_api.get('win') == 'win':
                result['status'] = 'win'
                result['win_amount'] = result_from_api.get('win_amount', 0)
            elif result_from_api.get('win') == 'loose':
                result['status'] = 'loss'
                
        return result
        
    def _find_in_listinfodata(self, order_id):
        """Buscar orden en listinfodata"""
        if hasattr(self.iq.api, 'listinfodata') and isinstance(self.iq.api.listinfodata, dict):
            for key, value in self.iq.api.listinfodata.items():
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict) and item.get('id') == order_id:
                            return item
        return None

# PRUEBA
print("🧪 SOLUCIÓN FUNCIONAL - SIN DEPENDENCIA DE get_position_history")
print("="*60)

# Conectar
iq = IQ_Option(IQ_EMAIL, IQ_PASSWORD)
check, reason = iq.connect()

if not check:
    print(f"❌ Error: {reason}")
    exit()

iq.change_balance(ACCOUNT_TYPE)
print(f"✅ Conectado. Balance: ${iq.get_balance():,.2f}")

# Crear tracker
tracker = OrderTracker(iq)

# Hacer operación
print("\n📊 Haciendo operación de prueba...")
amount = 1
asset = "EURUSD-OTC"
direction = "call"

check, order_id = iq.buy(amount, asset, direction, 1)

if check:
    print(f"✅ Orden creada: {order_id}")
    
    # Registrar orden
    tracker.add_order(order_id, amount, asset, direction)
    
    # Verificar inmediatamente (para ver datos iniciales)
    print("\n🔍 Verificación inicial:")
    tracker.check_order_result(order_id)
    
    # Esperar a que expire
    print("\n⏳ Esperando 75 segundos...")
    for i in range(75, 0, -5):
        print(f"   {i}s...", end="\r")
        time.sleep(5)
    
    # Verificar resultado final
    print("\n\n🔍 Verificación final:")
    result = tracker.check_order_result(order_id)
    
    if result:
        print(f"\n📊 RESULTADO FINAL:")
        print(f"   Order ID: {result['order_id']}")
        print(f"   Status: {result['status']}")
        print(f"   Balance Diff: ${result['balance_diff']:+.2f}")
        
        if result['status'] == 'win':
            print(f"\n✅ OPERACIÓN GANADORA!")
            print(f"   Profit: ${result['profit']:.2f}")
        elif result['status'] == 'loss':
            print(f"\n❌ OPERACIÓN PERDEDORA")
            print(f"   Loss: ${abs(result['profit']):.2f}")
else:
    print(f"❌ Error creando orden: {order_id}")

print("\n✅ Prueba completada")
print("="*60)