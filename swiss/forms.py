from django import forms

from swiss.models import Tournament, Player


class TournamentAddForm(forms.ModelForm):

    ranked_players = forms.ModelMultipleChoiceField(queryset=Player.objects.all())
    # ranked_players = forms.ModelMultipleChoiceField(widget=forms.CheckboxSelectMultiple, queryset=Player.objects.all())

    class Meta:
        model = Tournament
        exclude = ('number_of_rounds', )

    def save(self, commit=True):
        tournament = Tournament.start_tournament(self.cleaned_data['ranked_players'], self.cleaned_data['number_of_winners'])
        return tournament
