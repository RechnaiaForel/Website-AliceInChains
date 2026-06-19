from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminOrReadOnly(BasePermission):
    """
    Каталог (товары/категории/производители) доступен на чтение всем,
    включая анонимных пользователей. Создание, изменение и удаление —
    только администраторам (`is_staff=True` либо суперпользователь).
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)
