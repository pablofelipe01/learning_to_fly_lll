#!/usr/bin/env python3
"""
Script para reiniciar la estrategia de trading
Borra todas las estadísticas acumuladas y permite empezar de cero
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path

# Configuración
STATE_FILE = "strategy_state.json"
LOG_FILE = "iqoption_strategy.log"
BACKUP_DIR = "backups"

def load_current_state():
    """Cargar el estado actual si existe"""
    if not os.path.exists(STATE_FILE):
        return None
    
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error leyendo estado: {e}")
        return None

def show_current_statistics(state):
    """Mostrar las estadísticas actuales"""
    if not state:
        print("📊 No hay estadísticas previas")
        return
    
    print("\n📊 ESTADÍSTICAS ACTUALES:")
    print("=" * 50)
    
    # Wins/Losses/Ties
    wins = state.get('wins', {})
    losses = state.get('losses', {})
    ties = state.get('ties', {})
    
    total_wins = sum(wins.values()) if isinstance(wins, dict) else 0
    total_losses = sum(losses.values()) if isinstance(losses, dict) else 0
    total_ties = sum(ties.values()) if isinstance(ties, dict) else 0
    total_trades = total_wins + total_losses + total_ties
    
    print(f"🎯 Total de operaciones: {total_trades}")
    if total_trades > 0:
        print(f"✅ Victorias: {total_wins} ({total_wins/total_trades*100:.1f}%)")
        print(f"❌ Pérdidas: {total_losses} ({total_losses/total_trades*100:.1f}%)")
        print(f"🟡 Empates: {total_ties} ({total_ties/total_trades*100:.1f}%)")
    
    # Profit
    total_profit = state.get('total_profit', 0)
    print(f"\n💰 Beneficio total: ${total_profit:,.2f}")
    
    # Pérdidas consecutivas
    consecutive_losses = state.get('consecutive_losses', {})
    if consecutive_losses:
        print("\n📉 Pérdidas consecutivas por activo:")
        for asset, count in consecutive_losses.items():
            if count > 0:
                print(f"   {asset}: {count}")
    
    # Stop losses
    if state.get('absolute_stop_loss_activated'):
        print("\n🚨 Stop Loss Absoluto: ACTIVADO")
    if state.get('monthly_stop_loss'):
        print(f"🚨 Stop Loss Mensual: ACTIVADO en {state.get('stop_loss_triggered_month')}")
    
    # Fecha de última actividad
    timestamp = state.get('timestamp', 'N/A')
    print(f"\n📅 Última actualización: {timestamp}")
    print("=" * 50)

def create_backup(state):
    """Crear backup del estado actual"""
    if not state:
        return None
    
    # Crear directorio de backups si no existe
    Path(BACKUP_DIR).mkdir(exist_ok=True)
    
    # Nombre del archivo de backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{BACKUP_DIR}/strategy_state_backup_{timestamp}.json"
    
    # Guardar backup
    try:
        with open(backup_file, 'w') as f:
            json.dump(state, f, indent=4)
        print(f"\n💾 Backup creado: {backup_file}")
        return backup_file
    except Exception as e:
        print(f"❌ Error creando backup: {e}")
        return None

def reset_strategy():
    """Reiniciar la estrategia"""
    print("\n🔄 REINICIANDO ESTRATEGIA...")
    
    # Eliminar archivo de estado
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
        print(f"✅ Archivo {STATE_FILE} eliminado")
    
    # Opcional: Limpiar log
    response = input("\n¿Deseas también limpiar el archivo de log? (s/N): ").lower()
    if response == 's':
        if os.path.exists(LOG_FILE):
            # Hacer backup del log
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_backup = f"{BACKUP_DIR}/iqoption_strategy_log_{timestamp}.log"
            Path(BACKUP_DIR).mkdir(exist_ok=True)
            shutil.move(LOG_FILE, log_backup)
            print(f"✅ Log movido a: {log_backup}")
        else:
            print("📄 No se encontró archivo de log")
    
    print("\n✨ ¡Estrategia reiniciada exitosamente!")
    print("📌 La próxima vez que ejecutes el bot:")
    print("   - Comenzará con estadísticas en cero")
    print("   - Mantendrá tu configuración actual")
    print("   - Usará tu balance actual como capital inicial")

def main():
    """Función principal"""
    print("🔄 SCRIPT DE REINICIO DE ESTRATEGIA")
    print("=" * 50)
    print("Este script borrará todas las estadísticas acumuladas:")
    print("- Wins/Losses/Ties")
    print("- Pérdidas consecutivas")
    print("- Beneficios acumulados")
    print("- Estados de stop loss")
    print("- Historial de operaciones")
    print("=" * 50)
    
    # Cargar estado actual
    current_state = load_current_state()
    
    # Mostrar estadísticas actuales
    show_current_statistics(current_state)
    
    # Confirmar acción
    print("\n⚠️  ADVERTENCIA: Esta acción no se puede deshacer")
    response = input("¿Estás seguro de que quieres reiniciar la estrategia? (s/N): ").lower()
    
    if response != 's':
        print("\n❌ Operación cancelada")
        return
    
    # Crear backup si hay estado
    if current_state:
        backup_file = create_backup(current_state)
        if backup_file:
            print(f"💡 Puedes restaurar el estado anterior copiando:")
            print(f"   cp {backup_file} {STATE_FILE}")
    
    # Reiniciar estrategia
    reset_strategy()
    
    print("\n✅ Proceso completado")
    print("🚀 Puedes ejecutar 'python main.py' para empezar de nuevo")

if __name__ == "__main__":
    main()