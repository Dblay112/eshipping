from django import template
from apps.tally.models import Terminal

register = template.Library()


@register.simple_tag
def get_terminals():
    return Terminal.objects.all().order_by('name')
