import hashlib
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import ApiKey

class ApiKeyAuthentication(BaseAuthentication):
    """
    Custom authentication backend for API Key authentication.
    Clients should authenticate by passing the API key in the 'X-API-Key' header.
    Example: X-API-Key: your_actual_api_key_string
    """
    keyword = 'X-API-Key'

    def authenticate(self, request):
        auth_header_value = f'HTTP_{self.keyword.upper().replace("-", "_")}'
        key_from_header = request.META.get(auth_header_value)

        if not key_from_header:
            return None # No API key provided, other authentication methods can be attempted.

        try:
            # Ensure ApiKey model has a field named 'key' storing the actual secret key string.
            # Ensure ApiKey model has a ForeignKey to User named 'user'.
            # Ensure ApiKey model has a boolean field 'is_active'.
            api_key_instance = ApiKey.objects.get(key=key_from_header)
        except ApiKey.DoesNotExist:
            raise AuthenticationFailed('Invalid API Key provided.')
        except Exception:
            # Catch any other potential exceptions during DB query for robustness.
            raise AuthenticationFailed('Error validating API Key.')

        if not api_key_instance.is_active:
            raise AuthenticationFailed('API Key is not active.')

        if not api_key_instance.user:
             raise AuthenticationFailed('API Key is not associated with an active user.')

        if not api_key_instance.user.is_active:
            raise AuthenticationFailed('The user associated with this API Key is not active.')
        
        # Optional: Update last_used timestamp. 
        # Be mindful of write operations on every authenticated request if performance is critical.
        # from django.utils import timezone
        # api_key_instance.last_used = timezone.now()
        # api_key_instance.save(update_fields=['last_used'])

        # On successful authentication, return a two-tuple of (user, auth)
        # request.user will be set to api_key_instance.user
        # request.auth will be set to api_key_instance (the ApiKey object itself)
        return (api_key_instance.user, api_key_instance)

    def authenticate_header(self, request):
        """
        If authentication fails, this is included in the WWW-Authenticate header.
        Indicates to the client how to authenticate.
        """
        return f'{self.keyword} realm="api"'

class APIKeyAuthentication(BaseAuthentication):
    """
    Custom authentication backend for API Keys.
    Clients should authenticate by passing the API key in the "Authorization" HTTP header,
    prefixed with the string "ApiKey ". For example:
        Authorization: ApiKey ssk_abcdef12_thisistherealkeypartthatislong
    """
    keyword = 'ApiKey'

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')

        if not auth_header or not auth_header.startswith(self.keyword + ' '):
            return None # No Authorization header with ApiKey keyword

        try:
            # Example: "ApiKey ssk_abc123_verylongkeypart"
            # full_key will be "ssk_abc123_verylongkeypart"
            full_key = auth_header.split()[1]
        except IndexError:
            # Malformed header, keyword present but no key
            raise AuthenticationFailed(_('Invalid API Key header. No key provided.'))

        # Split the full_key into prefix and the actual key_part
        # Assuming prefix is always 8 chars: ssk_ + 6 random chars = 8 chars
        # And the key is prefix + '_' + key_part
        # e.g. ssk_rand1_keypart
        # prefix_len = 8 # Based on ssk_ + 6 random chars
        # A more robust way if prefix length can vary (but ours is fixed from model):
        try:
            prefix, key_part = full_key.split('_', 1)
            # Our model prefix is ssk_xxxxxx (8 chars), full_key includes that plus another underscore and key_part.
            # So, the prefix in the full_key is just the first part.
            # The prefix in the model is the `ssk_xxxxxx` part.
            # We need to be careful here. The model stores prefix as e.g. "ssk_rand1".
            # The key given to user is "ssk_rand1_actualkey".
            # So, `prefix` here is the model's `prefix` field.

        except ValueError:
            # Key does not contain '_' to separate prefix and key_part
            raise AuthenticationFailed(_('Invalid API Key format. Expected prefix_key.'))

        api_key_instance = self.get_api_key(prefix)
        if not api_key_instance:
            raise AuthenticationFailed(_('Invalid API Key prefix or key not found.'))

        if not self.is_key_valid(api_key_instance, key_part):
            raise AuthenticationFailed(_('Invalid API Key.'))

        if not api_key_instance.user.is_active:
            raise AuthenticationFailed(_('User account is disabled.'))

        # Update last_used_at
        api_key_instance.last_used_at = timezone.now()
        api_key_instance.save(update_fields=['last_used_at'])

        return (api_key_instance.user, api_key_instance)

    def get_api_key(self, prefix):
        try:
            return ApiKey.objects.get(prefix=prefix, is_active=True)
        except ApiKey.DoesNotExist:
            return None

    def is_key_valid(self, api_key_instance, provided_key_part):
        if api_key_instance.expires_at and api_key_instance.expires_at < timezone.now():
            return False # Key has expired
        
        # Hash the provided key part and compare with the stored hash
        hashed_provided_key = hashlib.sha256(provided_key_part.encode()).hexdigest()
        return hashed_provided_key == api_key_instance.hashed_key

    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a 401 Unauthenticated response, or `None` if the
        authentication scheme should not be used for the request.
        """
        return self.keyword 