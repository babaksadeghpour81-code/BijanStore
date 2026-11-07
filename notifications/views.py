from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Notification


@login_required
def notification_list(request):
    notifications = request.user.notifications.all()
    unread_count = notifications.filter(is_read=False).count()

    return render(request, 'notifications/list.html', {
        'notifications': notifications,
        'unread_count': unread_count,
    })


@login_required
@require_POST
def mark_read(request, notification_id):
    notification = get_object_or_404(
        Notification, id=notification_id, user=request.user
    )
    notification.is_read = True
    notification.save()

    # اگر لینک داشت، برو به اون
    if notification.link:
        return redirect(notification.link)
    return redirect('notifications:list')


@login_required
@require_POST
def mark_all_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect('notifications:list')


@login_required
def notification_click(request, notification_id):
    """کلیک روی اعلان: خوانده‌شده + رفتن به لینک"""
    notification = get_object_or_404(
        Notification, id=notification_id, user=request.user
    )
    if not notification.is_read:
        notification.is_read = True
        notification.save()

    if notification.link:
        return redirect(notification.link)
    return redirect('notifications:list')

