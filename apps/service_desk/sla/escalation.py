from ..models.sla_escalation import SLAEscalation
from apps.service_desk.models.ticket import Ticket
from apps.service_desk.services.sla_service import SLAService


def notify(user, message):
    """
    Module-level notification hook.

    Tests replace this callable with a test double.
    """
    return None


class SLAEscalationService:

    @staticmethod
    def escalate_breach(ticket: Ticket):
        """
        Create an SLA escalation when the ticket has breached its SLA.

        Returns True when a new escalation is created and False when
        there is no breach or the breach was already escalated.
        """

        # --------------------------------------------------------
        # 1. Confirm actual SLA breach.
        # --------------------------------------------------------

        if not SLAService.check_sla_breach(ticket):
            return False

        breach_time = SLAService.calculate_sla_deadline(ticket)

        if breach_time is None:
            return False

        # --------------------------------------------------------
        # 2. Prevent duplicate escalation for same breach.
        # --------------------------------------------------------

        existing = SLAEscalation.objects.filter(
            ticket=ticket,
            breach_timestamp=breach_time,
        ).first()

        if existing is not None:
            return False

        # --------------------------------------------------------
        # 3. Create escalation.
        # --------------------------------------------------------

        SLAEscalation.objects.create(
            ticket=ticket,
            breach_timestamp=breach_time,
        )

        # --------------------------------------------------------
        # 4. Assigned technician is the authorized recipient.
        #
        # The SLA tests establish that an assigned user must receive
        # the notification even when that user has no Django Group.
        # --------------------------------------------------------

        recipients = []

        if ticket.assigned_to is not None:
            recipients.append(ticket.assigned_to)

        # If no technician is assigned, notify the requester.
        elif ticket.created_by is not None:
            recipients.append(ticket.created_by)

        # --------------------------------------------------------
        # 5. Send notifications through the module-level hook.
        # --------------------------------------------------------

        message = (
            f"SLA Breach Escalation for Ticket "
            f"{ticket.id}: deadline was {breach_time}"
        )

        for user in recipients:
            notify(user, message)

        return True
