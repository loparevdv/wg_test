import json
from datetime import datetime

from django.views.generic import CreateView, DetailView
from django.http import HttpResponseRedirect, HttpResponse
from django.template.context import RequestContext

from swiss.models import Matchup, Tournament
from swiss.models import SCORE_FOR_DRAW, SCORE_FOR_WIN

class TournamentCreateView(CreateView):

    def get_success_url(self):
        return self.object.get_current_round().get_absolute_url()


class TournamentDetailView(DetailView):

    model = Tournament


class RoundDetailView(DetailView):
    
    def get_context_data(self, **kwargs):
        context_data = super(RoundDetailView, self).get_context_data(**kwargs)
        round_groups = self.object.roundgroup_set.all()
        context_data['groups'] = round_groups
        context_data['next_round'] = self.object.get_next_round()
        return context_data


def set_result(request, pk, result):
    matchup = Matchup.objects.get(id=pk)

    if result == 'black':
        black = matchup.black
        black.score += SCORE_FOR_WIN
        black.save()
        matchup.black_score = SCORE_FOR_WIN
    elif result == 'white':
        white = matchup.white
        white.score += SCORE_FOR_WIN
        white.save()
        matchup.white_score = SCORE_FOR_WIN
    elif result == 'draw':
        black = matchup.black
        white = matchup.white
        black.score += SCORE_FOR_DRAW
        black.save()
        white.score += SCORE_FOR_DRAW
        white.save()
        matchup.black_score = matchup.white_score = SCORE_FOR_DRAW
    matchup.save()

    tournament_round = matchup.round_group.tournament_round
    can_start_next_round = tournament_round.is_finished() and (tournament_round.number < tournament_round.tournament.number_of_rounds)
    is_all_games_played = tournament_round.is_finished() and (tournament_round.number == tournament_round.tournament.number_of_rounds)

    return HttpResponse(json.dumps(
        {
            'matchup': matchup.id,
            'result': result,
            'can_start_next_round': can_start_next_round,
            'is_all_games_played': is_all_games_played,
        }
    ))

def start_next_round_view(request, pk):
    context = RequestContext(request)
    tournament = Tournament.objects.get(id=pk)

    check = datetime.now()

    tournament_round = tournament.start_next_round()

    print 'round started', datetime.now() - check

    check = datetime.now()

    context['tournament'] = tournament
    context['tournament_round'] = tournament_round
    context['groups'] = tournament_round.roundgroup_set.all()

    print 'context completed', datetime.now() - check

    return HttpResponseRedirect(tournament_round.get_absolute_url())

def final_calcs(request, pk):
    tournament = Tournament.objects.get(id=pk)
    final_results = tournament.finish_tournament()
    return HttpResponse(json.dumps(final_results))
