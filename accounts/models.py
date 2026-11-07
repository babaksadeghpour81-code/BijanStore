import uuid
from django.db import models
from django.contrib.auth.models import User


class EmailConfirmation(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='email_confirmation')
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} — {'تأیید شده' if self.confirmed_at else 'در انتظار'}"

    @property
    def is_confirmed(self):
        return self.confirmed_at is not None