from django import template

register = template.Library()


@register.filter
def remove_normal(value):
    return value.replace("_normal", "")
