from django import forms
from assignments.models import About, SocialLink
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
            'seo_title',
            'meta_description',
            'focus_keyword',
            'image_alt_text',
        )
        widgets = {
            'blog_body': forms.Textarea(attrs={
                'rows': 18,
                'maxlength': '10000',
                'class': 'rich-text-source',
                'aria-describedby': 'blog-editor-help',
            }),
            'seo_title': forms.TextInput(attrs={
                'maxlength': '70',
                'data-character-counter': 'seo-title-count',
            }),
            'meta_description': forms.Textarea(attrs={
                'rows': 3,
                'maxlength': '160',
                'data-character-counter': 'meta-description-count',
            }),
            'focus_keyword': forms.TextInput(attrs={'maxlength': '100'}),
            'image_alt_text': forms.TextInput(attrs={'maxlength': '255'}),
        }
        help_texts = {
            'seo_title': 'Optional. Recommended: about 50–60 characters.',
            'meta_description': 'Optional. Recommended: about 150–160 characters.',
            'focus_keyword': 'Optional editorial guidance; this is not emitted as a meta keywords tag.',
            'image_alt_text': 'Optional. Describe the featured image; the post title is used when blank.',
        }


class AboutForm(forms.ModelForm):
    class Meta:
        model = About
        fields = ('about_heading', 'about_description')
        widgets = {
            'about_description': forms.Textarea(attrs={'rows': 8}),
        }


class SocialLinkForm(forms.ModelForm):
    class Meta:
        model = SocialLink
        fields = ('platform', 'link')


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
