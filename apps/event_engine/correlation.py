from apps.event_engine.models import DomainEvent

def by_correlation(correlation_id: str):
    return DomainEvent.objects.filter(correlation_id=correlation_id)
