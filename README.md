# AlaCrunch - Sistema de Punto de Venta (POS)

**AlaCrunch** (parte de la suite GastroSoft-POS) es una solución avanzada de Punto de Venta (POS) de escritorio, diseñada para optimizar la eficiencia operativa en negocios de comida rápida, con un enfoque especializado en establecimientos de alitas y pollerías.

## 📝 Descripción General

**AlaCrunch** representa la evolución tecnológica en la gestión de puntos de venta para el sector gastronómico de comida rápida. Desarrollado bajo los estándares de la suite **GastroSoft**, este software de escritorio ha sido diseñado meticulosamente para resolver los desafíos críticos que enfrentan los restaurantes modernos, como las pollerías y establecimientos especializados en alitas. Su objetivo primordial es transformar la complejidad operativa en un flujo de trabajo fluido, permitiendo que el personal se enfoque en la calidad del servicio mientras el sistema garantiza la integridad de cada transacción y proceso administrativo.

La arquitectura de AlaCrunch se sustenta en tres pilares fundamentales: **agilidad transaccional, control financiero riguroso y portabilidad absoluta**. En el día a día, el módulo de ventas brilla por su capacidad de respuesta; mediante una interfaz visual intuitiva, los cajeros pueden gestionar pedidos complejos, aplicar cargos por delivery y procesar diversos métodos de pago (efectivo, tarjetas y billeteras digitales como Yape o Plin) en cuestión de segundos. Esta rapidez se complementa con atajos de teclado estratégicos que minimizan los tiempos de espera del cliente, optimizando la rotación de mesas y pedidos.

En el ámbito financiero, AlaCrunch actúa como un auditor incansable. El sistema implementa un protocolo estricto de control de caja que inicia con la apertura obligatoria mediante un fondo base. Durante la jornada, permite el registro detallado de cada ingreso y egreso extraordinario, asegurando que el flujo de efectivo sea rastreable en todo momento. Al finalizar el turno, el módulo de cierre de caja realiza una conciliación automática, comparando las ventas registradas contra el conteo físico de dinero. Esta funcionalidad es vital para identificar discrepancias de inmediato, eliminando la incertidumbre y previniendo pérdidas económicas por errores humanos.

Técnicamente, el software destaca por su independencia y robustez. Al utilizar **Python 3.12** y una base de datos **SQLite3** embebida, AlaCrunch no requiere de conexión a internet ni de costosos servidores externos para operar, lo que garantiza la continuidad del negocio ante fallos de red. Además, su innovador sistema de gestión de imágenes optimiza los recursos visuales del menú, almacenándolos directamente en la base de datos para facilitar copias de seguridad rápidas. Finalmente, su motor de impresión nativo asegura una compatibilidad perfecta con impresoras térmicas estándar, consolidando a AlaCrunch como la herramienta definitiva para profesionalizar, asegurar y escalar cualquier emprendimiento gastronómico hacia el éxito.

## 🚀 Características Principales

* **Control de Caja y Turnos:** Requiere la apertura de caja con un fondo inicial, registra ingresos/egresos y emite un cuadre de caja detallado al finalizar el turno (calculando efectivo, tarjeta y QR).
* **Punto de Venta Ágil:** Interfaz intuitiva con agrupación por categorías, carrito de compras rápido, atajos de teclado y soporte para cobro de "Delivery".
* **Gestión de Menú (Inventario):** Administración visual de productos. Las imágenes de los platillos se redimensionan, optimizan y guardan automáticamente dentro de la base de datos para facilitar la portabilidad.
* **Impresión de Tickets:** Integración nativa con impresoras térmicas de Windows para imprimir comprobantes de venta directamente sin configuraciones complejas.
* **Seguridad por Roles:** Diferencia entre permisos de `Administrador` (puede anular ventas y modificar configuraciones) y `Cajero` (limitado a ventas y gestión de su caja).

## 🛠️ Tecnologías Utilizadas

* **Lenguaje:** Python 3.12
* **Interfaz Gráfica:** CustomTkinter (Provee una UI moderna con soporte para temas oscuros).
* **Base de Datos:** SQLite3 (Base de datos local `alitas_bbq.db` embebida, sin necesidad de servidor).
* **Procesamiento de Imágenes:** Pillow (PIL).
* **Generación de Tickets:** Motor nativo de creación de PDF (`pdf.py`) construido a medida para alto rendimiento.
* **Empaquetado:** PyInstaller (Genera el archivo `.exe` para distribución).

## 📁 Arquitectura del Código

El proyecto está modularizado de la siguiente manera:

* `main.py`: Punto de entrada de la aplicación. Inicializa la interfaz y asegura la creación de la base de datos.
* `alitasbbq/app.py`: Contiene la clase principal `AlitasBBQApp` que gestiona todas las vistas (Login, Dashboard, POS, Inventario, Reportes, Configuración de Impresora).
* `alitasbbq/db.py`: Capa de persistencia. Maneja todas las consultas SQL, esquemas de tablas, y lógica financiera.
* `alitasbbq/config.py`: Gestor de rutas absolutas y recursos, asegurando que los íconos y la BD se ubiquen correctamente al compilar el proyecto.
* `alitasbbq/pdf.py`: Generador de documentos y tickets.

## 🔑 Credenciales por Defecto

Para iniciar sesión en una base de datos limpia, puedes utilizar los siguientes usuarios:

* **Administrador:**
  * Usuario: `admin`
  * Clave: `1234`
* **Cajero:**
  * Usuario: `caja`
  * Clave: `1234`

## ⚙️ Cómo Ejecutar el Proyecto

**Modo Desarrollo:**
1. Instalar las dependencias requeridas: 
   ```bash
   pip install customtkinter Pillow
   ```
2. Ejecutar la aplicación principal:
   ```bash
   python main.py
   ```

**Compilar a Ejecutable (.exe):**
El proyecto incluye archivos de configuración (`AlaCrunch.spec`) listos para ser procesados con PyInstaller.
