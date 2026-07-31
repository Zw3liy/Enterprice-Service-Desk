from apps.service_desk.services.ticket_service import TicketService


def ticket_list_qs(**filters):
    return TicketService.search(**filters)


def get_ticket(ticket_id):
    return TicketService.get_ticket(ticket_id)
