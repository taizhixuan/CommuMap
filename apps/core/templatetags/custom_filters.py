from django import template

register = template.Library()


@register.filter
def replace(value, arg):
    """
    Replace parts of a string.
    Usage: {{ value|replace:"old,new" }}
    """
    if arg and ',' in arg:
        old, new = arg.split(',', 1)
        return value.replace(old, new)
    return value


@register.filter
def underscore_to_space(value):
    """
    Replace underscores with spaces and title case the result.
    Usage: {{ value|underscore_to_space }}
    """
    return value.replace('_', ' ').title() 