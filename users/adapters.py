from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .utils import build_unique_username, normalize_email


def build_username(email, first_name='', last_name=''):
    return build_unique_username(email=email, first_name=first_name, last_name=last_name)


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        print(f"DEBUG: Pre-social login for {sociallogin.user.email}")
        return super().pre_social_login(request, sociallogin)

    def authentication_error(self, request, provider_id, error=None, exception=None, extra_context=None):
        print(f"DEBUG: Auth error for {provider_id}: {error}, {exception}")
        return super().authentication_error(request, provider_id, error, exception, extra_context)

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        email = data.get('email', '')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        if not user.username:
            user.username = build_username(email=email, first_name=first_name, last_name=last_name)
        if not user.email:
            user.email = normalize_email(email)
        if not user.first_name:
            user.first_name = first_name
        if not user.last_name:
            user.last_name = last_name
        return user
