from django import template

register = template.Library()

@register.filter
def split(value, delimiter=','):
    """
    Returns the string split by delimiter.
    Usage: {{ "a,b,c"|split:"," }} returns ['a', 'b', 'c']
    """
    if value:
        return value.split(delimiter)
    return []