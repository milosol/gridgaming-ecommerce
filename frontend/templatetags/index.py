from django import template

register = template.Library()


@register.filter
def index(indexable, i):
    try:
        return indexable[i]
    except:
        return indexable[0]
