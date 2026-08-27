from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from apps.service_desk.models import Release
from apps.service_desk.security.policies import (
    get_ticket_queryset,
    is_administrator,
    is_manager,
)
from apps.service_desk.services.release_management import (
    execute_deployment,
    rollback_release,
    schedule_release,
)
from apps.service_desk.selectors.release_management import get_releases


def _authorized(user, release):
    return (
        (is_administrator(user) or is_manager(user))
        and release.change_request.ticket in get_ticket_queryset(user)
    )


@login_required
def release_list(request):
    releases = get_releases(request.user)
    return HttpResponse(
        "\n".join(
            f"{release.version_number} - {release.get_status_display()}"
            for release in releases
        )
    )


@login_required
def release_detail(request, pk):
    release = get_object_or_404(
        Release.objects.select_related(
            "change_request",
            "change_request__ticket",
        ),
        pk=pk,
    )

    if not _authorized(request.user, release):
        return HttpResponse("Forbidden", status=403)

    return HttpResponse(
        f"{release.version_number} - {release.get_status_display()}"
    )


@login_required
def release_create(request):
    if not (is_administrator(request.user) or is_manager(request.user)):
        return HttpResponse("Forbidden", status=403)

    return HttpResponse("Release creation endpoint")


@login_required
def release_schedule(request, pk):
    release = get_object_or_404(Release, pk=pk)

    if not _authorized(request.user, release):
        return HttpResponse("Forbidden", status=403)

    schedule_release(release=release, user=request.user)
    return HttpResponse("Release scheduled")


@login_required
def release_execute(request, pk):
    release = get_object_or_404(Release, pk=pk)

    if not _authorized(request.user, release):
        return HttpResponse("Forbidden", status=403)

    execute_deployment(release=release, user=request.user)
    return HttpResponse("Deployment started")


@login_required
def release_rollback(request, pk):
    release = get_object_or_404(Release, pk=pk)

    if not _authorized(request.user, release):
        return HttpResponse("Forbidden", status=403)

    rollback_release(release=release, user=request.user)
    return HttpResponse("Release rolled back")