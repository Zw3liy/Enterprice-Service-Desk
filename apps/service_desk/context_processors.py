"""
Template context processors.

Only one, and it is deliberately cheap: the navigation bar needs the
signed-in user's unread notification count on every page, and pushing
that through every individual view's get_context_data would be both
repetitive and easy to forget.
"""

from apps.service_desk.selectors.notification_selector import (
    NotificationSelector,
)


def notifications(request):
    """
    Expose the current user's unread notification count.

    Returns an empty dict for anonymous requests so no query is run
    on the login page or any other unauthenticated view.
    """

    user = getattr(request, "user", None)

    if user is None or not user.is_authenticated:
        return {}

    return {
        "nav_unread_notifications": NotificationSelector.unread_count(user),
    }
