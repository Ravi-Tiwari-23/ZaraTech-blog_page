from django import forms
from blogs.models import Category, Blog
from django.contrib.auth.models import Group, User
from django.contrib.auth.forms import UserCreationForm


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = '__all__'


class BlogPostForm(forms.ModelForm):
    class Meta:
        model = Blog
        fields = (
            'title',
            'Category',
            'featured_image',
            'short_description',
            'blog_body',
            'status',
            'is_featured',
        )


ROLE_CHOICES = (
    ('Reader', 'Reader'),
    ('Editor', 'Editor'),
    ('Manager', 'Manager'),
)


class AddUserForm(UserCreationForm):
    role = forms.ChoiceField(choices=ROLE_CHOICES)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'username', 'role', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            if self.cleaned_data['role'] == 'Reader':
                user.groups.clear()
            else:
                group, _ = Group.objects.get_or_create(name=self.cleaned_data['role'])
                user.groups.set([group])
        return user


class EditUserForm(forms.ModelForm):
    role = forms.ChoiceField(choices=ROLE_CHOICES)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'username', 'role', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_group = self.instance.groups.filter(name__in=dict(ROLE_CHOICES)).first()
        if current_group:
            self.fields['role'].initial = current_group.name
        else:
            self.fields['role'].initial = 'Reader'

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            if self.cleaned_data['role'] == 'Reader':
                user.groups.clear()
            else:
                group, _ = Group.objects.get_or_create(name=self.cleaned_data['role'])
                user.groups.set([group])
        return user
