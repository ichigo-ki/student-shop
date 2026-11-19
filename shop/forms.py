from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Product


class StudentRegistrationForm(UserCreationForm):
  email = forms.EmailField(required=True, help_text='University or personal email')
  first_name = forms.CharField(max_length=100, required=False)
  last_name = forms.CharField(max_length=100, required=False)

  class Meta:
    model = User
    fields = ('username', 'email', 'first_name', 'last_name')

  def save(self, commit=True):
    user = super().save(commit=False)
    user.email = self.cleaned_data['email']
    user.first_name = self.cleaned_data['first_name']
    user.last_name = self.cleaned_data['last_name']
    user.is_staff = False  # Regular students are never staff by default
    if commit:
      user.save()
    return user


class ProductManageForm(forms.ModelForm):
  class Meta:
    model = Product
    fields = ('category', 'title', 'description', 'price', 'image')