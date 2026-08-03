from apps.ai_engine.services.priority_predictor import PriorityPredictor


class PriorityEngine:
    @staticmethod
    def apply(ticket) -> None:
        if ticket.priority_id or not ticket.company_id:
            return
        text = f"{ticket.title}\n{ticket.description}"
        priority = PriorityPredictor.predict(ticket.company, text)
        if priority:
            ticket.priority = priority
            ticket.save(update_fields=["priority", "updated_at"])
