from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Profile


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, label='Email')
    full_name = forms.CharField(required=False, label='ФИО', max_length=150)
    phone = forms.CharField(required=False, label='Телефон', max_length=20)
    address = forms.CharField(required=False, label='Адрес доставки', max_length=255)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()

        # Profile уже создан сигналом post_save на User, здесь его дозаполняем.
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.full_name = self.cleaned_data.get('full_name', '')
        profile.phone = self.cleaned_data.get('phone', '')
        profile.address = self.cleaned_data.get('address', '')
        if commit:
            profile.save()
        return user
