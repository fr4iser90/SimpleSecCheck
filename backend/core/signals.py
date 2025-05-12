from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import UserProfile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # Ensure profile exists, might be redundant if create_user_profile always runs first
    # but good for robustness if users could somehow be created without the signal firing initially.
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        # This case should ideally not happen if create_user_profile works correctly
        UserProfile.objects.create(user=instance) 