# F-SALES 🍕 | Sistema POS & Control Gastronómico Inteligente

**F-SALES** es una solución de Punto de Venta (POS) y gestión gastronómica desarrollada en **Python + Django**, especialmente diseñada para operar en entornos comerciales multi-moneda (USD / Bs con sincronización automática con la tasa del **Banco Central de Venezuela - BCV**, financiamientos rápidos como Cashea, cálculos precisos de costeo por recetas e impresión térmica local en Windows).

---

## 🏗️ Módulos del Sistema

El sistema está construido de forma modular para garantizar escalabilidad y separación de responsabilidades en cada operación comercial:

| Módulo | Descripción Principal |
| :--- | :--- |
| 🍽️ **`tables`** *(Mesas & POS)* | Control operativo del salón (mesas internas y externas), comandas digitales en tiempo real, catálogo de productos con tamaños/extras, sincronización automatizada de tasas BCV por scraping e integración directa con impresoras térmicas (comandos ESC/POS y Tickera vía Windows). |
| 📦 **`inventory`** *(Inventario & Recetas)* | Gestión inteligente de stock para insumos simples y compuestos (recetas/sub-reacciones). Deducción de materia prima en tiempo real tras la facturación o cortesías al personal, alertas automáticas por stock mínimo y valoración financiera actual de inventarios. |
| 📋 **`maestros`** *(Catálogo Maestro)* | Administración centralizada del maestro de insumos, manejo de presentaciones o bultos de compra, conversión automática entre peso estándar y unidad del producto con cálculo dinámico de costo unitario por porción. |
| 💵 **`caja`** *(Facturación & Cuadres)* | Módulo contable diario. Control total de cobros, manejo de propinas y cuadres de caja transparentes comparando las ventas teóricas del sistema contra el flujo físico declarado por el cajero (Efectivo USD/Bs, Pago Móvil, Punto de Venta y Cashea). |
| 📊 **`reports`** *(Reportes & Auditoría)* | Centro de inteligencia comercial. Análisis histórico de ventas por categoría y mesero, rentabilidad y márgenes reales por plato, reportes de insumos agotados y registros inmutables de auditorías de cambios y eliminaciones de comandas. |
| 👥 **`staff`** *(Gestión de Personal)* | Registro y asignación de meseros, cajeros y administradores con jerarquías y control granular de acceso al tablero principal. |
| ⚙️ **`core` & `pos_core`** *(Configuración del Sistema)* | Centro de control global del negocio. Personalización de identidad para facturas térmicas (Nombre, RIF, Logo, cuentas de Pago Móvil), políticas impositivas y de tasas automáticas, y parámetros del servidor POS y correos automáticos. |

---

## 💻 Stack Tecnológico & Dependencias

* **Lenguaje Principal:** Python 3.10+
* **Framework Web & ORM:** Django 5.0+
* **Conectividad & Scraping (BCV):** `requests`, `beautifulsoup4`
* **Integración de Hardware:** `pywin32` *(Comunicación local y desatendida con colas de impresión térmica en entornos Windows).*

---

## 🚀 Proceso de Instalación y Puesta en Marcha

Sigue estos sencillos pasos en una terminal de Windows (**PowerShell** o **CMD**) para configurar y ejecutar el sistema en tu equipo local:

### 1. Clonar el Repositorio
Obtén el código fuente y ubícate dentro del directorio del proyecto:
```powershell
git clone <URL_DEL_REPOSITORIO>
cd pos_project
```

### 2. Crear y Activar el Entorno Virtual
Aísla las librerías del proyecto de tu sistema creando un entorno virtual de Python:
```powershell
# Crear entorno virtual
python -m venv venv

# Activar en PowerShell / Windows
.\venv\Scripts\activate
```

### 3. Instalar Dependencias del Proyecto
Con el entorno virtual activado, instala todas las librerías necesarias con un solo comando:
```powershell
pip install -r requirements.txt
```

### 4. Ejecutar Migraciones y Estructurar Base de Datos
Genera el esquema contable, tablas del catálogo y estructura local en tu base de datos SQLite:
```powershell
python manage.py migrate
```

### 5. Crear el Cuenta Administradora (Superusuario)
Para tener acceso total a la interfaz del Punto de Venta, Reportes y Auditoría:
```powershell
python manage.py createsuperuser
```
*(Ingresa tu usuario, correo opcional y la contraseña que prefieras).*

### 6. Iniciar el Servidor de Desarrollo Local
Pon en marcha el servidor Django:
```powershell
python manage.py runserver
```
🌐 **¡Listo para operar!** Abre tu navegador de internet favorito e ingresa a: **`http://127.0.0.1:8000/`** para usar F-SALES.

---

## ⚖️ Copyright & Derechos de Autor

**© 2026 F-SALES. Todos los derechos reservados.**

Este software, junto con su arquitectura, base de datos y código fuente, es propiedad exclusiva del desarrollador y titular del proyecto (**F-SALES**).
* **Uso Restringido y Licencia Privada:** Queda estrictamente prohibida la redistribución, reproducción, modificación, sublicenciamiento, uso comercial no autorizado o ingeniería inversa de todo o parte de este código fuente y sus algoritmos sin el consentimiento previo por escrito de los titulares del copyright.
* **Propiedad Intelectual:** El motor de cálculo computacional para costeo por recetas e insumos compuestos, la automatización de scraping para la tasa oficial del Banco Central de Venezuela (BCV), la gestión contable multi-moneda para cuadres operativos y la interfaz de terminal POS son marcas y creaciones intelectuales protegidas de **F-SALES**.

---
*Desarrollado con estándares profesionales orientados al rendimiento, seguridad y rentabilidad gastronómica.*
