@echo off
:: 1. Ve a la ruta donde está tu proyecto
cd C:\Ruta\A\Tu\Proyecto

:: 2. Activa tu entorno virtual (modifica "venv" por el nombre de tu entorno si es distinto)
call venv\Scripts\activate

:: 3. Abre el navegador predeterminado en la dirección local
start http://127.0.0.1:8000

:: 4. Inicia el servidor de Django
python manage.py runserver