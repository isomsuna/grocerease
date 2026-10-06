from rest_framework.authentication import SessionAuthentication


class SessionAuthenticationWith401(SessionAuthentication):
    def authenticate_header(self, request):
        return 'Session'
