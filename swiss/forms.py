import math
from datetime import datetime

from django import forms

from swiss.models import Tournament, Player, Round, Matchup, RoundGroup, TournamentRank, Lot, RoundGroupProxy

def start_tournament(players, number_of_winners):
    check = datetime.now()

    number_of_rounds = round(math.log(len(players), 2)) + round(math.log(number_of_winners, 2))
    tournament = Tournament.objects.create(number_of_winners=number_of_winners, number_of_rounds=number_of_rounds)

    ranks = []
    for rank, player in enumerate(players.order_by('-elo')):
        ranks.append(TournamentRank(
            tournament=tournament,
            player=player,
            rank=rank+1,
            score=0,
            starting_elo=player.elo,
        ))
    TournamentRank.objects.bulk_create(ranks)

    print 'ranks created', datetime.now() - check


    check = datetime.now()

    first_round = tournament.start_next_round()

    print 'round started', datetime.now() - check

    return tournament


class TournamentAddForm(forms.ModelForm):

    # ranked_players = forms.ModelMultipleChoiceField(queryset=Player.objects.all())
    ranked_players = forms.ModelMultipleChoiceField(widget=forms.CheckboxSelectMultiple, queryset=Player.objects.all())

    class Meta:
        model = Tournament
        exclude = ('number_of_rounds', )

    def save(self, commit=True):
        tournament = start_tournament(self.cleaned_data['ranked_players'], self.cleaned_data['number_of_winners'])
        return tournament