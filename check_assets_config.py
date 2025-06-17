#!/usr/bin/env python3
"""
Script para verificar disponibilidad de activos específicos en IQ Option
Versión que usa las credenciales de config.py
"""

import time
import sys
from datetime import datetime
from iqoptionapi.stable_api import IQ_Option

# Importar configuración
try:
    from config import IQ_EMAIL, IQ_PASSWORD, ACCOUNT_TYPE
except ImportError:
    print("❌ Error: No se pudo importar config.py")
    print("Asegúrate de que config.py esté en el mismo directorio")
    sys.exit(1)

# Lista de activos a verificar con descripciones
TARGET_ASSETS = {
    "US500": "S&P 500 - El más confiable",
    "EURUSD": "Rey del Forex",
    "GER30": "DAX - Muy técnico", 
    "GBPUSD": "Cable - Líquido y predecible",
    "XAUUSD": "Oro - Respeta niveles",
    "USDJPY": "Yen - Movimientos claros",
    "UK100": "FTSE - Buen comportamiento",
    "EURGBP": "Euro/Libra - Menos volátil",
    "AUDUSD": "Aussie - Commodity currency",
    "JP225": "Nikkei - Técnicamente limpio",
    "EURJPY": "Euro/Yen - Buenos rebotes",
    "APPLE": "La más técnica de las acciones",
    "XAGUSD": "Plata - Sigue al oro",
    "MSFT": "Microsoft - Tendencias claras",
    "GBPJPY": "Libra/Yen - Para más volatilidad"
}

# Variantes a buscar para cada activo
SUFFIXES = ["", "-OTC", "-op", "_otc", "_OTC"]

# Mapeo conocido de nombres alternativos
KNOWN_MAPPINGS = {
    "US500": ["US500", "USA500", "SP500", "SPX500"],
    "GER30": ["GER30", "GER40", "DAX30", "DAX", "GERMANY30"],
    "UK100": ["UK100", "FTSE100", "FTSE"],
    "JP225": ["JP225", "JPN225", "NIKKEI225", "NIKKEI"],
    "APPLE": ["APPLE", "AAPL", "#AAPL", "APPLE#", "AAPL#"],
    "MSFT": ["MSFT", "MICROSOFT", "#MSFT", "MSFT#"],
    "XAUUSD": ["XAUUSD", "GOLD", "Gold"],
    "XAGUSD": ["XAGUSD", "SILVER", "Silver"]
}

def check_assets():
    """Verificar disponibilidad de activos específicos"""
    
    print("="*80)
    print("🔍 VERIFICADOR DE ACTIVOS PARA IQ OPTION")
    print("="*80)
    print(f"📅 Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📧 Usuario: {IQ_EMAIL[:3]}***{IQ_EMAIL[-10:]}")
    print(f"💼 Cuenta: {ACCOUNT_TYPE}")
    print("="*80)
    
    # Verificar credenciales
    if not IQ_EMAIL or IQ_EMAIL == "tu_email@example.com":
        print("❌ ERROR: Por favor configura tus credenciales en config.py")
        return
    
    # Conectar a IQ Option
    print("\n🔗 Conectando a IQ Option...")
    iq = IQ_Option(IQ_EMAIL, IQ_PASSWORD)
    check, reason = iq.connect()
    
    if not check:
        print(f"❌ Error al conectar: {reason}")
        if "2FA" in str(reason).upper():
            print("🔑 Se requiere autenticación de dos factores (2FA)")
        return
    
    print("✅ Conexión exitosa")
    
    # Cambiar tipo de cuenta
    iq.change_balance(ACCOUNT_TYPE)
    balance = iq.get_balance()
    print(f"💰 Balance: ${balance:,.2f}")
    
    # Actualizar lista de activos
    print("\n📊 Obteniendo lista de activos...")
    iq.update_ACTIVES_OPCODE()
    time.sleep(1)
    
    # Obtener todos los activos disponibles
    all_assets = iq.get_all_open_time()
    
    if not all_assets:
        print("❌ No se pudieron obtener los activos")
        return
    
    # Resultados
    results = {}
    
    print("\n🔍 BUSCANDO ACTIVOS OBJETIVO:")
    print("-" * 80)
    
    # Buscar cada activo objetivo
    for asset, description in TARGET_ASSETS.items():
        results[asset] = {
            'found': False,
            'variants': [],
            'description': description
        }
        
        print(f"\n📌 {asset} - {description}:")
        
        # Obtener posibles nombres del mapeo conocido
        possible_names = KNOWN_MAPPINGS.get(asset, [asset])
        
        # Agregar variantes con sufijos
        names_to_check = []
        for base_name in possible_names:
            names_to_check.append(base_name)
            for suffix in SUFFIXES:
                names_to_check.append(f"{base_name}{suffix}")
        
        # Buscar en cada tipo de opción
        for option_type in ["binary", "turbo", "digital"]:
            if option_type not in all_assets:
                continue
            
            # Buscar cada posible nombre
            for name in names_to_check:
                # Probar también en mayúsculas y minúsculas
                for test_name in [name, name.upper(), name.lower()]:
                    if test_name in all_assets[option_type]:
                        is_open = all_assets[option_type][test_name].get("open", False)
                        status = "✅ ABIERTO" if is_open else "❌ CERRADO"
                        
                        # Verificar si ya tenemos esta variante
                        already_found = any(
                            v['name'] == test_name and v['type'] == option_type 
                            for v in results[asset]['variants']
                        )
                        
                        if not already_found:
                            variant_info = {
                                'name': test_name,
                                'type': option_type,
                                'open': is_open
                            }
                            
                            results[asset]['variants'].append(variant_info)
                            results[asset]['found'] = True
                            
                            print(f"   ✓ Encontrado como '{test_name}' en {option_type}: {status}")
    
    # Resumen por tipo de activo
    print("\n" + "="*80)
    print("📊 RESUMEN POR CATEGORÍA:")
    print("="*80)
    
    # Categorizar activos
    forex_pairs = ["EURUSD", "GBPUSD", "USDJPY", "EURGBP", "AUDUSD", "EURJPY", "GBPJPY"]
    indices = ["US500", "GER30", "UK100", "JP225"]
    commodities = ["XAUUSD", "XAGUSD"]
    stocks = ["APPLE", "MSFT"]
    
    # Mostrar por categoría
    print("\n💱 FOREX:")
    for asset in forex_pairs:
        show_asset_status(asset, results)
    
    print("\n📈 ÍNDICES:")
    for asset in indices:
        show_asset_status(asset, results)
    
    print("\n🏗️ COMMODITIES:")
    for asset in commodities:
        show_asset_status(asset, results)
    
    print("\n🏢 ACCIONES:")
    for asset in stocks:
        show_asset_status(asset, results)
    
    # Resumen final
    print("\n" + "="*80)
    print("📊 RESUMEN FINAL:")
    print("="*80)
    
    available_count = 0
    tradeable_assets = []
    
    for asset in TARGET_ASSETS:
        if results[asset]['found']:
            # Buscar la mejor variante disponible
            open_variants = [v for v in results[asset]['variants'] if v['open']]
            
            if open_variants:
                available_count += 1
                # Preferir binary sobre turbo
                best = next((v for v in open_variants if v['type'] == 'binary'), open_variants[0])
                tradeable_assets.append({
                    'original': asset,
                    'iq_name': best['name'],
                    'type': best['type']
                })
    
    print(f"\n✅ Activos disponibles para operar: {available_count}/{len(TARGET_ASSETS)}")
    
    if tradeable_assets:
        print("\n📋 CONFIGURACIÓN SUGERIDA PARA STRATEGY:")
        print("-" * 50)
        print("TRADING_ASSETS = [")
        for asset in tradeable_assets:
            print(f'    "{asset["original"]}",  # IQ: {asset["iq_name"]} ({asset["type"]})')
        print("]")
        
        print("\n# Mapeo para IQ Option:")
        print("ASSET_MAPPING = {")
        for asset in tradeable_assets:
            print(f'    "{asset["original"]}": "{asset["iq_name"]}",')
        print("}")
    
    print("\n✅ Verificación completada")

def show_asset_status(asset, results):
    """Mostrar estado de un activo específico"""
    if results[asset]['found']:
        open_variants = [v for v in results[asset]['variants'] if v['open']]
        if open_variants:
            best = open_variants[0]
            print(f"   ✅ {asset}: '{best['name']}' ({best['type']})")
        else:
            print(f"   ⚠️  {asset}: Encontrado pero cerrado")
    else:
        print(f"   ❌ {asset}: No encontrado")

def main():
    """Función principal"""
    try:
        check_assets()
    except KeyboardInterrupt:
        print("\n\n⏹️ Verificación cancelada por el usuario")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()