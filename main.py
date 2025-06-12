# main.py
# Punto de entrada principal para la estrategia RSI en IQ Option

import sys
import argparse
import logging
from datetime import datetime

from config import IQ_EMAIL, IQ_PASSWORD, ACCOUNT_TYPE, LOG_FILE
from strategy import MultiCurrencyRSIBinaryOptionsStrategy
from utils import setup_logger

def main():
    """Función principal para ejecutar la estrategia"""
    
    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Estrategia RSI Multi-Divisa para IQ Option')
    parser.add_argument('--email', type=str, help='Email de IQ Option (sobrescribe config)')
    parser.add_argument('--password', type=str, help='Contraseña de IQ Option (sobrescribe config)')
    parser.add_argument('--account', type=str, choices=['PRACTICE', 'REAL'], 
                       default=ACCOUNT_TYPE, help='Tipo de cuenta a usar')
    parser.add_argument('--test', action='store_true', help='Ejecutar en modo prueba')
    parser.add_argument('--debug-assets', action='store_true', 
                       help='Mostrar todos los activos forex disponibles y salir')
    parser.add_argument('--check-order', type=str, 
                       help='Verificar el resultado de una orden específica por ID')
    parser.add_argument('--check-recent', action='store_true',
                       help='Verificar resultados de órdenes recientes')
    
    args = parser.parse_args()
    
    # Usar credenciales de argumentos o de config
    email = args.email or IQ_EMAIL
    password = args.password or IQ_PASSWORD
    account_type = args.account
    
    # Verificar credenciales
    if not email or not password or email == "tu_email@example.com":
        print("❌ ERROR: Por favor configura tus credenciales en config.py o pásalas como argumentos")
        print("Uso: python main.py --email tu_email@example.com --password tu_password")
        sys.exit(1)
    
    # Configurar logger principal
    logger = setup_logger('main', LOG_FILE)
    
    # Banner de inicio
    logger.info("=" * 60)
    logger.info("   ESTRATEGIA RSI MULTI-DIVISA PARA IQ OPTION")
    logger.info("   ⚡ LÓGICA INVERTIDA ⚡")
    logger.info("=" * 60)
    logger.info(f"📅 Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"📧 Usuario: {email[:3]}***{email[-10:]}")  # Ocultar parte del email
    logger.info("=" * 60)
    logger.info("⚠️ IMPORTANTE: Esta estrategia usa lógica INVERTIDA")
    logger.info("   - PUT cuando RSI ≤ 35 (sobreventa)")
    logger.info("   - CALL cuando RSI ≥ 65 (sobrecompra)")
    logger.info("=" * 60)
    
    try:
        # Crear e inicializar la estrategia
        logger.info("🚀 Inicializando estrategia...")
        strategy = MultiCurrencyRSIBinaryOptionsStrategy(
            email=email,
            password=password,
            account_type=account_type
        )
        
        # Si es modo debug de activos
        if args.debug_assets:
            logger.info("🔍 MODO DEBUG: Mostrando todos los activos forex disponibles...")
            strategy.debug_show_all_forex_assets()
            logger.info("✅ Debug completado. Revisa los logs para ver todos los activos.")
            return
        
        # Si queremos verificar una orden específica
        if args.check_order:
            logger.info(f"🔍 Verificando orden {args.check_order}...")
            strategy.test_check_order_result(args.check_order)
            logger.info("✅ Verificación completada.")
            return
        
        # Si queremos verificar órdenes recientes
        if args.check_recent:
            logger.info("🔍 Verificando órdenes recientes...")
            strategy.check_recent_orders_results()
            logger.info("✅ Verificación completada.")
            return
        
        if args.test:
            # Modo prueba: verificar conexión y mostrar información
            logger.info("🧪 MODO PRUEBA - Verificando configuración...")
            logger.info(f"✅ Conexión exitosa")
            logger.info(f"💰 Balance: ${strategy.initial_capital:,.2f}")
            logger.info(f"📊 Pares disponibles: {len(strategy.valid_pairs)}")
            if strategy.valid_pairs:
                logger.info("📋 Pares activos:")
                for pair in strategy.valid_pairs[:10]:  # Mostrar hasta 10
                    iq_name = strategy.iqoption_pairs[pair]
                    option_type = strategy.pair_option_types[pair]
                    logger.info(f"   - {pair} → {iq_name} ({option_type})")
            else:
                logger.warning("⚠️ No hay pares disponibles para operar")
                logger.info("💡 Ejecuta con --debug-assets para ver todos los activos disponibles")
            logger.info("✅ Prueba completada exitosamente")
            return
        
        # Ejecutar estrategia
        logger.info("🎯 Iniciando operaciones...")
        logger.info("ℹ️ Presiona Ctrl+C para detener la estrategia")
        strategy.run()
        
    except KeyboardInterrupt:
        logger.info("\n⏹️ Estrategia detenida por el usuario")
    except Exception as e:
        logger.error(f"❌ Error fatal: {str(e)}")
        logger.error("Traceback completo:", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("👋 Programa finalizado")

if __name__ == "__main__":
    main()