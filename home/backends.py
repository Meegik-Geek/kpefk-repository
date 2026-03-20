from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

class EmailOrUsernameModelBackend(ModelBackend):
    """
    Дозволяє авторизуватись використовуючи або ім'я користувача, або email.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
            
        try:
            # Шукаємо користувача за username АБО email (регістронезалежно)
            user = UserModel.objects.get(
                Q(username__iexact=username) | Q(email__iexact=username)
            )
        except UserModel.DoesNotExist:
            # Для захисту від атак за часом
            UserModel().set_password(password)
            return None
        except UserModel.MultipleObjectsReturned:
            # Якщо є дублікати email, беремо першого знайденого
            user = UserModel.objects.filter(
                Q(username__iexact=username) | Q(email__iexact=username)
            ).order_by('id').first()

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
            
        return None
