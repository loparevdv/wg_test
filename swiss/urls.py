from django.conf.urls import patterns, include, url
from django.contrib.auth.decorators import login_required
from django.contrib import admin
admin.autodiscover()

from django.views.generic import CreateView, DetailView, ListView

from swiss.models import Player, Tournament, Round
from swiss.forms import TournamentAddForm
from swiss.views import TournamentDetailView, TournamentCreateView, RoundDetailView, set_result, start_next_round_view, final_calcs

urlpatterns = patterns('',
	url(r'player/(?P<pk>\d+)/', DetailView.as_view(model=Player), name="player"),
	url(r'players/', ListView.as_view(model=Player), name="players"),
    url(r'new_player/', login_required(CreateView.as_view(model=Player)), name="new_player"),

	url(r'final_calcs/(?P<pk>\d+)/$', login_required(final_calcs), name="final_calcs"),

	url(r'start_next_round/(?P<pk>\d+)/$', login_required(start_next_round_view), name="start_next_round"),
	

    url(r'tournament/(?P<pk>\d+)/$', TournamentDetailView.as_view(model=Tournament), name="tournament"),
    url(r'tournaments/', ListView.as_view(model=Tournament), name="tournaments"),
    url(r'new_tournament/', login_required(TournamentCreateView.as_view(model=Tournament, form_class=TournamentAddForm)), name="new_tournament"),

    url(r'matchup/(?P<pk>\d+)/(?P<result>\w+)/', login_required(set_result), name="matchup"),
    url(r'round/(?P<pk>\d+)/', RoundDetailView.as_view(model=Round), name="round"),
)
