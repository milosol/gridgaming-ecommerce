from django import forms
from users.models import UserRoles


# class UserAccountForm(forms.ModelForm):
#
#     account_type = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.RadioSelect())
#
#     class Meta:
#         model = UserRoles
#         fields = ('role_name', )
#
#
#     # def __init__(self, *args, **kwargs):
#     #     super(UserAccountForm, self).__init__(*args, **kwargs)
#     #     self.fields['role_name'].widget = forms.RadioSelect()
#

class UserAccountForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super(UserAccountForm, self).__init__(*args, **kwargs)

        choices = [(role, role.role_description)
                   for role in UserRoles.objects.all()]

        self.fields['user_roles'] = forms.ChoiceField(widget=forms.RadioSelect(),
                                                      choices=choices, label='')
