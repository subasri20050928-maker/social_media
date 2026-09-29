from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Profile, Post, Comment


class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter strong password',
            'autocomplete': 'new-password'
        }),
        min_length=6,
        help_text='At least 6 characters'
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password',
            'autocomplete': 'new-password'
        }),
        label="Confirm Password"
    )

    class Meta:
        model = User
        fields = ('username', 'email')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username (e.g. alex)',
                'autocomplete': 'username'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'name@example.com (optional)',
                'autocomplete': 'email'
            }),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("A user with that username already exists.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class UserLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your username',
            'autocomplete': 'username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your password',
            'autocomplete': 'current-password'
        })
    )


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('content',)
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'post-input',
                'placeholder': "What's happening? Share with your network...",
                'rows': 3,
                'maxlength': '2000'
            })
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('content',)
        widgets = {
            'content': forms.TextInput(attrs={
                'class': 'comment-input',
                'placeholder': 'Write a comment...',
                'maxlength': '1000'
            })
        }


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('bio', 'avatar')
        widgets = {
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Tell everyone about yourself...',
                'rows': 4,
                'maxlength': '500'
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'form-control-file',
                'accept': 'image/*'
            }),
        }
