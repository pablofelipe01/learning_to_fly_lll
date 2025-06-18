# 📈 Algoritmo de Multi-Activos para IQ Option

[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg)](mailto:pablofelipe@me.com)
[![Educational Use Only](https://img.shields.io/badge/Use-Educational%20Only-blue.svg)](mailto:pablofelipe@me.com)
[![Commercial Use: Prohibited](https://img.shields.io/badge/Commercial%20Use-Prohibited-red.svg)](mailto:pablofelipe@me.com)

> **⚠️ AVISO IMPORTANTE**: Este software es de uso EXCLUSIVAMENTE EDUCATIVO. El uso comercial está ESTRICTAMENTE PROHIBIDO sin licencia. Contactar a pablofelipe@me.com para solicitar permisos.

Un algoritmo automatizado de opciones binarias basado en **Algebra Invertida** para múltiples activos en IQ Option.

## ⚡ Características Principales

- **Lógica Algebra Invertida**: 
  - PUT cuando indicador ≤ 35 (sobreventa)
  - CALL cuando indicador ≥ 65 (sobrecompra)
- **Multi-Activos**: Opera hasta 15 activos simultáneamente
- **Gestión de Riesgo**: Stop loss absoluto y mensual
- **Control de Pérdidas**: Límite de 3 pérdidas consecutivas diarias
- **Profit Lock**: Detiene operaciones cuando el día es rentable
- **Período de Calentamiento**: 1 hora sin operaciones al inicio
- **Persistencia de Estado**: Guarda y recupera el estado del algoritmo

## 🚀 Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/iq-option-algebra-algorithm.git
cd iq-option-algebra-algorithm
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Configurar credenciales
Edita el archivo `config.py` y añade tus credenciales:
```python
IQ_EMAIL = "tu_correo@example.com"
IQ_PASSWORD = "tu_contraseña"
ACCOUNT_TYPE = "PRACTICE"  # o "REAL"
```

## 💻 Uso

### Ejecutar el algoritmo
```bash
python main.py
```

### Opciones de línea de comandos
```bash
# Usar credenciales por línea de comandos
python main.py --email tu_email@example.com --password tu_password

# Usar cuenta real
python main.py --account REAL

# Modo prueba (verifica conexión sin operar)
python main.py --test

# Ver todos los activos disponibles
python main.py --debug-assets

# Verificar una orden específica
python main.py --check-order ORDER_ID

# Ver órdenes recientes
python main.py --check-recent
```

## ⚙️ Configuración

### Parámetros Algebra Invertida
- **RSI_PERIOD**: 14 (período interno del cálculo)
- **OVERSOLD_LEVEL**: 35 (nivel para señal PUT en algebra invertida)
- **OVERBOUGHT_LEVEL**: 65 (nivel para señal CALL en algebra invertida)

### Gestión de Capital
- **POSITION_SIZE_PERCENT**: 1% del capital por operación
- **MIN_POSITION_SIZE**: $1.00 mínimo
- **ABSOLUTE_STOP_LOSS_PERCENT**: 75% pérdida máxima del capital inicial
- **MONTHLY_STOP_LOSS_PERCENT**: 40% pérdida máxima mensual

### Control de Operaciones
- **EXPIRY_MINUTES**: 5 minutos de expiración
- **MIN_TIME_BETWEEN_SIGNALS**: 60 minutos entre señales del mismo activo
- **MAX_CONSECUTIVE_LOSSES**: 3 pérdidas consecutivas diarias (activa pausa)

### Activos Disponibles
```python
TRADING_ASSETS = [
    "US500",   # S&P 500
    "EURUSD",  # Euro/Dólar
    "GER30",   # DAX
    "GBPUSD",  # Libra/Dólar
    "XAUUSD",  # Oro
    "USDJPY",  # Dólar/Yen
    "UK100",   # FTSE
    "EURGBP",  # Euro/Libra
    "AUDUSD",  # Dólar Australiano
    "JP225",   # Nikkei
    "EURJPY",  # Euro/Yen
    "GBPJPY",  # Libra/Yen
]
```

## 📊 Características de Seguridad

### 1. Stop Loss
- **Absoluto**: Se activa al perder 75% del capital inicial
- **Mensual**: Se activa al perder 40% en un mes

### 2. Control Diario
- **Profit Lock**: Detiene operaciones cuando el día es rentable
- **Loss Lock**: Detiene operaciones después de 3 pérdidas consecutivas

### 3. Período de Calentamiento
- 1 hora sin operaciones al iniciar para analizar el mercado

### 4. Persistencia
- Guarda estado cada 30 ciclos en `strategy_state.json`
- Recupera operaciones activas al reiniciar

## 📈 Lógica de Trading - Algebra Invertida

### Señales de Entrada
```
Indicador Algebra ≤ 35 → Señal PUT (Lógica Invertida)
Indicador Algebra ≥ 65 → Señal CALL (Lógica Invertida)
```

### Proceso de Trading
1. Calcula indicador Algebra con velas de 5 minutos
2. Genera señal si el indicador está en zona extrema
3. Verifica condiciones (capital, tiempo entre señales, etc.)
4. Coloca orden binaria de 5 minutos
5. Espera expiración + 15 segundos
6. Verifica resultado y actualiza estadísticas

## 📝 Logs y Debugging

### Niveles de Log
- **INFO**: Operaciones normales
- **WARNING**: Situaciones a revisar
- **ERROR**: Errores recuperables
- **CRITICAL**: Errores fatales

### Archivos de Log
- `iqoption_strategy.log`: Log principal
- `strategy_state.json`: Estado guardado

### Comandos de Debug
```bash
# Ver todos los activos disponibles
python main.py --debug-assets

# Verificar orden específica
python main.py --check-order 123456789

# Ver últimas 10 órdenes
python main.py --check-recent
```

## 🔧 Troubleshooting

### Error de conexión
- Verifica credenciales en `config.py`
- Asegúrate de no tener 2FA activado
- Prueba primero con cuenta PRACTICE

### No hay activos disponibles
- Ejecuta `python main.py --debug-assets`
- Verifica que los activos estén abiertos
- Algunos activos solo están disponibles en horario de mercado

### Órdenes no se verifican
- El sistema espera 15 segundos después de expiración
- Si falla, intenta varios métodos de verificación
- Después de 2 minutos asume pérdida por seguridad

## 📊 Estadísticas

El algoritmo muestra:
- Balance inicial vs final
- Rendimiento total (%)
- Total de operaciones
- Victorias/Derrotas/Empates
- Tasa de éxito
- Beneficio neto
- Estadísticas por activo
- Rendimiento mensual

## ⚠️ Advertencias

1. **Riesgo de Capital**: El trading de opciones binarias conlleva alto riesgo
2. **Cuenta Demo**: Siempre prueba primero en cuenta PRACTICE
3. **Sin Garantías**: Los resultados pasados no garantizan resultados futuros
4. **Supervisión**: Requiere supervisión aunque sea automatizado

## 🛠️ Requisitos

- Python 3.7+
- iqoptionapi
- pandas (para cálculos)
- pytz (zonas horarias)

### requirements.txt
```
iqoptionapi
pandas
pytz
```

## 📄 Licencia y Términos de Uso

### ⚖️ Restricciones de Uso

**IMPORTANTE**: Este software está protegido por leyes internacionales de derechos de autor y propiedad intelectual.

- **USO COMERCIAL PROHIBIDO**: El uso comercial de este software está **ESTRICTAMENTE PROHIBIDO** sin autorización expresa por escrito.
- **FINES EDUCATIVOS**: Este software se proporciona exclusivamente con fines educativos y de investigación.
- **LICENCIAS**: Para cualquier uso diferente al educativo personal, debe solicitar una licencia contactando al desarrollador: **pablofelipe@me.com**

### 🛡️ Protección Legal

Este software está protegido bajo:
- **Convenio de Berna** para la Protección de las Obras Literarias y Artísticas
- **Tratado de la OMPI** sobre Derecho de Autor (WCT)
- **Digital Millennium Copyright Act (DMCA)**
- **Directiva 2009/24/CE** de la Unión Europea sobre protección jurídica de programas de ordenador
- Leyes nacionales de propiedad intelectual aplicables en cada jurisdicción

### ❌ Prohibiciones

Queda expresamente prohibido:
1. Usar este software con fines comerciales sin licencia
2. Redistribuir, vender o sublicenciar el código
3. Eliminar o alterar avisos de copyright
4. Realizar ingeniería inversa sin autorización
5. Usar el software para actividades ilegales o no éticas

### ✅ Usos Permitidos

- Estudio personal del código
- Uso en entornos académicos con atribución
- Pruebas en cuentas demo para aprendizaje
- Modificaciones privadas para uso personal no comercial

### 📧 Solicitud de Licencias

Para solicitar una licencia comercial o de uso especial:
- **Email**: pablofelipe@me.com
- **Asunto**: Solicitud de Licencia - IQ Option Algebra Algorithm
- **Incluir**: Descripción del uso propuesto, datos de contacto, organización

### ⚠️ Consecuencias Legales

El uso no autorizado, la distribución ilegal o el plagio de este software puede resultar en:
- Acciones civiles por daños y perjuicios
- Demandas por infracción de copyright
- Responsabilidad penal según las leyes aplicables
- Indemnización por daños hasta 150,000 USD por infracción (según DMCA)

### 📋 Aviso de Copyright

```
Copyright (c) 2024 Pablo Felipe (pablofelipe@me.com)
Todos los derechos reservados.

Este software y su documentación asociada están protegidos por las leyes
de derechos de autor y tratados internacionales. La reproducción o
distribución no autorizada de este programa, o cualquier parte del mismo,
puede resultar en severas sanciones civiles y penales, y será perseguida
con el máximo rigor permitido por la ley.
```

## 🤝 Contribuciones

Las contribuciones con fines educativos son bienvenidas, sujetas a las siguientes condiciones:

1. **Cesión de Derechos**: Al contribuir, aceptas ceder todos los derechos de tu contribución al proyecto.
2. **Fines Educativos**: Las contribuciones deben mantener el carácter educativo del proyecto.
3. **Sin Uso Comercial**: No se aceptan contribuciones destinadas a uso comercial.

### Proceso de Contribución:
1. Fork el proyecto
2. Crea tu feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

**Nota**: Todas las contribuciones están sujetas a revisión y deben respetar los términos de la licencia original.

## 📞 Soporte y Contacto

- **Soporte Técnico**: Abre un issue en el repositorio
- **Licencias Comerciales**: pablofelipe@me.com
- **Consultas Legales**: pablofelipe@me.com

**IMPORTANTE**: Este es un proyecto educativo. No se proporciona soporte para uso en cuentas reales o con fines comerciales sin licencia.

---

## ⚖️ AVISO LEGAL Y DISCLAIMER

**IMPORTANTE - LEER ANTES DE USAR**:

1. **SOFTWARE EDUCATIVO**: Este software se proporciona EXCLUSIVAMENTE con fines educativos y de investigación académica.

2. **PROHIBICIÓN DE USO COMERCIAL**: El uso comercial está ESTRICTAMENTE PROHIBIDO sin licencia expresa del desarrollador.

3. **SIN GARANTÍAS**: Este software se proporciona "tal cual", sin garantías de ningún tipo, expresas o implícitas.

4. **RIESGO FINANCIERO**: El trading de opciones binarias conlleva riesgos significativos y puede resultar en la pérdida total del capital invertido. NO use este software con dinero que no pueda permitirse perder.

5. **RESPONSABILIDAD**: El desarrollador NO se hace responsable de pérdidas financieras, daños directos o indirectos derivados del uso de este software.

6. **CUMPLIMIENTO LEGAL**: Es responsabilidad del usuario asegurarse de que el uso de este software cumple con todas las leyes y regulaciones aplicables en su jurisdicción.

7. **PROPIEDAD INTELECTUAL**: Este código es propiedad intelectual protegida. Su copia, modificación o distribución sin autorización constituye una violación de las leyes de copyright internacionales.

**Para consultas sobre licencias comerciales**: pablofelipe@me.com

© 2024 Pablo Felipe. Todos los derechos reservados.