from django import template

register = template.Library()

@register.filter(name='trim')
def trim(value):
    if isinstance(value, str):
        return value.strip()
    return value
