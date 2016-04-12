from models import User

class EmailAuth(object):
    def authenticate(self, email=None, password=None):
        """
        Get an instance of User using the supplied email and password
        """
        try:
            user = User.objects.get(email=email)
            if user.check_password(password):
                return user

        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        """
        used by django authentication system to get an instance of User
        """
        try:
            user = User.objects.get(pk=user_id)
            if user.is_active:
                return user
            return None
        except User.DoesNotExist:
            return None

