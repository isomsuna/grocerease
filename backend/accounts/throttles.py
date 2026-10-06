from rest_framework.throttling import ScopedRateThrottle


class UserScopedRateThrottle(ScopedRateThrottle):
    """Apply a scoped rate limit to an authenticated user across all their IPs."""

    def get_cache_key(self, request, view):
        user = getattr(request, 'user', None)
        if user is None or not user.is_authenticated:
            return None

        ident = str(user.pk)
        self.key = self.cache_format % {'scope': self.scope, 'ident': ident}
        return self.key


class IPScopedRateThrottle(ScopedRateThrottle):
    """Keep public auth endpoint limits tied to the client IP after sign-in."""

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        self.key = self.cache_format % {'scope': self.scope, 'ident': ident}
        return self.key
