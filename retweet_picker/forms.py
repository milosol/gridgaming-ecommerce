from django import forms

from .models import TwitterGiveaway


class GiveawayForm(forms.ModelForm):
    class Meta:
        model = TwitterGiveaway
        fields = ['tweet_url', 'winner_count', 'contest_name']

class RetweetChooserForm(forms.Form):
    id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    tweet_url = forms.URLField()
    #winner_count = forms.IntegerField(max_value=100)
    #members_to_follow = forms.CharField()
    contest_name = forms.CharField()

    def clean_tweet_url(self, *args, **kwargs):
        tweet_url = self.cleaned_data.get("tweet_url")
        if "twitter" in tweet_url:
            return tweet_url
        else:
            raise forms.ValidationError("Invalid Twitter URL")
