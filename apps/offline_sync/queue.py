from apps.offline_sync.models import OfflineMutation

def pending_for(user, device_id):
    return OfflineMutation.objects.filter(user=user, device_id=device_id, state=OfflineMutation.State.PENDING)
