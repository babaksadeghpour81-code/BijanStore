def vendor_status(request):
    if request.user.is_authenticated:
        try:
            vendor = request.user.vendor
            return {'current_vendor': vendor}
        except Exception:
            return {'current_vendor': None}
    return {'current_vendor': None}