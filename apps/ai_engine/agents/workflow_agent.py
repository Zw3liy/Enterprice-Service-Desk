from apps.ai_engine.services.routing_engine import RoutingEngine
from apps.service_desk.services.ai_service import AIService


class WorkflowAgent:
    @classmethod
    def process_new_ticket(cls, ticket):
        AIService.enrich_ticket(ticket)
        RoutingEngine.route(ticket, category_code=ticket.ai_category_suggestion or "")
        return ticket
