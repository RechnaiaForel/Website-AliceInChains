from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Profile


class RegistrationForm(UserCreationForm):
    email     = forms.EmailField(required=True, label='Email')
    full_name = forms.CharField(required=False, label='ФИО', max_length=150)
    phone     = forms.CharField(required=False, label='Телефон', max_length=20)
    address   = forms.CharField(required=False, label='Адрес доставки', max_length=255)
    city      = forms.CharField(required=False, label='Город доставки', max_length=100)
    # favorite_category убрана — выпадающий список вызывал ошибки валидации

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()

        profile, _ = Profile.objects.get_or_create(user=user)
        profile.full_name = self.cleaned_data.get('full_name', '')
        profile.phone     = self.cleaned_data.get('phone', '')
        profile.address   = self.cleaned_data.get('address', '')
        profile.city      = self.cleaned_data.get('city', '')
        if commit:
            profile.save()
        return user


class ProfileUpdateForm(forms.ModelForm):
    """
    Форма настроек профиля.
    email намеренно НЕ добавляем сюда — шаблон рендерит его вручную,
    чтобы сохранить в User, а не в Profile.
    """
    class Meta:
        model = Profile
        fields = ['full_name', 'phone', 'address', 'city']
        labels = {
            'full_name': 'ФИО',
            'phone':     'Телефон',
            'address':   'Адрес доставки',
            'city':      'Город доставки',
        }
