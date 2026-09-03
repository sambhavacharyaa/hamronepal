from . import services


def notifications(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {}
    return {"nav_unread_notification_count": services.get_unread_notification_count(request.user)}
