from django import template
from django.template.defaultfilters import filesizeformat

register = template.Library()

@register.filter
def format_file_size(value):
    """Format file size in human readable format"""
    if value is None:
        return "0 B"
    return filesizeformat(value)

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key"""
    return dictionary.get(key)

@register.filter
def divide(value, arg):
    """Divide the value by the argument"""
    try:
        return int(value) / int(arg)
    except (ValueError, ZeroDivisionError):
        return None