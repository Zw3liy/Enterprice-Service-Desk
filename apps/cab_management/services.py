from apps.change_management.models import CABMeeting
from apps.change_management.services import ChangeService

__all__ = ["CABMeeting", "ChangeService"]


class CABManagementService:
    @staticmethod
    def schedule_meeting(company, title, scheduled_at, chair=None, members=None, changes=None):
        meeting = ChangeService.create_cab_meeting(
            company, title, scheduled_at, chair=chair, members=members
        )
        if changes:
            meeting.changes.set(changes)
        return meeting

    @staticmethod
    def close_meeting(meeting: CABMeeting, minutes: str = "") -> CABMeeting:
        meeting.minutes = minutes or meeting.minutes
        meeting.is_closed = True
        meeting.save(update_fields=["minutes", "is_closed", "updated_at"])
        return meeting

    @staticmethod
    def upcoming(company):
        return CABMeeting.objects.filter(company=company, is_closed=False).order_by(
            "scheduled_at"
        )
