from django.contrib import admin
from .models import Table, Categoria, Producto, TasaBCV

# Registramos los modelos para verlos en /admin
admin.site.register(Table)
admin.site.register(Categoria)
admin.site.register(Producto)
admin.site.register(TasaBCV)