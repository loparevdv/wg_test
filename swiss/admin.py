# -*- coding: utf-8 -*-
from django.contrib import admin
from django.db import models
from django.forms import widgets
from swiss.models import Matchup, Player, Round, TournamentRank, Tournament, RoundGroup, Lot


class MatchupAdmin(admin.ModelAdmin):
    pass


class PlayerAdmin(admin.ModelAdmin):
    pass


class RoundAdmin(admin.ModelAdmin):
    pass


class RoundGroupAdmin(admin.ModelAdmin):
    pass


class TournamentRankAdmin(admin.ModelAdmin):
    pass


class TournamentAdmin(admin.ModelAdmin):
    pass


class LotAdmin(admin.ModelAdmin):
    pass



admin.site.register(Matchup, MatchupAdmin)
admin.site.register(Player, PlayerAdmin)
admin.site.register(Round, RoundAdmin)
admin.site.register(RoundGroup, RoundGroupAdmin)
admin.site.register(TournamentRank, TournamentRankAdmin)
admin.site.register(Tournament, TournamentAdmin)
admin.site.register(Lot, LotAdmin)