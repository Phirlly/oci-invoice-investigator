from django import forms


class ApprovalForm(forms.Form):
    digest = forms.RegexField(regex=r"^[0-9a-f]{64}$", widget=forms.HiddenInput)
    confirm = forms.BooleanField(
        label="I reviewed this exact request and approve creating the internal demo task."
    )
