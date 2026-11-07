# vendors/templatetags/__init__.py  (خالی)

# vendors/templatetags/vendor_tags.py
from django import template

register = template.Library()


@register.filter
def get_vendor_name(user):
    try:
        return user.vendor.name
    except Exception:
        return "پنل فروشنده"