# tables/templatetags/tables_extras.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Permite hacer {{ diccionario|get_item:clave }} en el HTML"""
    return dictionary.get(key)