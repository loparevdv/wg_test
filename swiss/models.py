from datetime import datetime

from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User


SCORES_FOR_WIN = 1.0
SCORES_FOR_DRAW = 0.5
SCORES_FOR_NONPLAY = 0.5


class Player(models.Model):
    name = models.CharField(max_length=100)
    elo = models.FloatField()

    @property
    def get_elo(self):
        return self.elo

    def __unicode__(self):
        return '{0} - {1}'.format(self.name, self.get_elo)

    def get_absolute_url(self):
        return '/swiss/player/{0}/'.format(self.pk)

    def get_tournament_rank(self, tournament):
        return TournamentRank.objects.get(player=self, tournament=tournament)


class Matchup(models.Model):

    round_group = models.ForeignKey('RoundGroup')

    black = models.ForeignKey('TournamentRank', related_name=u'black_rank')
    white = models.ForeignKey('TournamentRank', related_name=u'white_rank')

    black_score = models.FloatField(default=0.0)
    white_score = models.FloatField(default=0.0)

    def __unicode__(self):
        return '{0} v {1} ({2})'.format(self.white, self.black, self.get_winner())

    def get_winner(self):
        if self.black_score == SCORES_FOR_WIN:
            return 'Black'
        elif self.white_score == SCORES_FOR_WIN:
            return 'White'
        elif self.black_score == self.white_score == SCORES_FOR_DRAW:
            return 'Draw'
        else:
            return 'Not played yet'

    def is_not_played(self):
        return self.black_score == self.white_score == 0

    def get_black_rank(self):
        return self.black

    def get_white_rank(self):
        return self.white


class Round(models.Model):

    number = models.PositiveIntegerField()
    tournament = models.ForeignKey('Tournament')

    nonplayer = models.ForeignKey(Player, null=True, blank=True)

    def __unicode__(self):
        return 'Round #{0}'.format(self.number)

    def get_absolute_url(self):
        return '/swiss/round/{0}/'.format(self.pk)

    def is_finished(self):
        for round_group in self.roundgroup_set.all():
            for matchup in round_group.matchup_set.all():
                if matchup.get_winner() == 'Not played yet':
                    return False
        return True

    def get_next_round(self):
        try:
            return Round.objects.get(tournament=self.tournament, number=self.number+1)
        except Round.DoesNotExist:
            return None

    def is_latest(self):
        return self.number == self.tournament.number_of_rounds

    def set_nonplayer(self, loted_players):
        round_groups = RoundGroup.objects.filter(tournament_round=self)

        tournament_ranks = TournamentRank.objects.filter(tournament=self.tournament)
        all_players = [rank.player for rank in tournament_ranks]
        
        nonplayer_as_list = list(set(all_players) - set(loted_players))

        if nonplayer_as_list:
            nonplayer = nonplayer_as_list[0]
            nonplayer_rank = TournamentRank.objects.get(player=nonplayer, tournament=self.tournament)
            nonplayer_rank.score += SCORES_FOR_NONPLAY
            nonplayer_rank.save()
            self.nonplayer = nonplayer
            self.save()
            return nonplayer_rank
        else:
            return None


class RoundGroup(models.Model):
    tournament_round = models.ForeignKey(Round)
    score_value = models.FloatField()

    class Meta:
        unique_together = (
            ('tournament_round', 'score_value'),
        )

    def __unicode__(self):
        return '{0} - {1} score'.format(self.tournament_round, self.score_value)

    def generate_matchups(self):
        matchups = []
        group_lots = self.lot_set.all().select_related('player')

        played_lots = []

        for number in range(len(group_lots) / 2):
            black = group_lots[number]
            white = group_lots[len(group_lots)/2+number]
            
            matchups.append(
                Matchup(
                    black=black.player.get_tournament_rank(self.tournament_round.tournament),
                    white=white.player.get_tournament_rank(self.tournament_round.tournament),
                    round_group=self,
                )
            )
            played_lots.append(black)
            played_lots.append(white)

        return matchups, played_lots

    def get_lots(self):
        return Lot.objects.filter(round_group=self).select_related('player')

    def get_matchups(self):
        return Matchup.objects.filter(round_group=self).select_related('black', 'white')


class TournamentRank(models.Model):
    player = models.ForeignKey(Player)
    rank = models.PositiveIntegerField()
    score = models.FloatField(default=0.0)
    tournament = models.ForeignKey('Tournament', null=True, blank=True)

    starting_elo = models.FloatField(default=0.0)
    final_elo = models.FloatField(default=0.0)

    buchholz_factor = models.FloatField(default=0)

    class Meta:
        unique_together = (
            ('tournament', 'player'),
        )

    def __unicode__(self):
        return '{0} - {1} - {2}'.format(self.rank, self.player.name, self.player.get_elo)

    def get_buchholz_factor(self):
        from django.db.models import Sum
        matchups_qs = Matchup.objects.filter(Q(black=self)|Q(white=self)).select_related('black', 'white')

        opponents = []

        for matchup in matchups_qs:
            if self == matchup.black:
                opponents.append(matchup.white)
            elif self == matchup.white:
                opponents.append(matchup.black)

        buchholz_factor = sum([opponent.score for opponent in opponents])
        return buchholz_factor

    def set_buchholtz_factor(self):
        self.buchholz_factor = self.get_buchholz_factor()
        self.save()

    def get_k_factor(self):
        if self.score < 2100:
            return 32
        elif self.score < 2400:
            return 24
        else:
            return 16


class Lot(models.Model):
    player = models.ForeignKey(Player)
    round_group = models.ForeignKey(RoundGroup)

    is_shifted = models.BooleanField(default=False)

    class Meta:
        unique_together = (
            ('round_group', 'player'),
        )


    def __unicode__(self):
        return 'Lot: {0} for {1}'.format(self.player, self.round_group)

    def get_player_rank(self):
        print 'IM SO FAT AND EXPENSIVE'
        return TournamentRank.objects.get(
            tournament=self.round_group.tournament_round.tournament,
            player=self.player,
        )

class Tournament(models.Model):
    number_of_winners = models.PositiveIntegerField(default=1)
    number_of_rounds = models.PositiveIntegerField(default=0)

    is_finished = models.BooleanField(default=False)

    def __unicode__(self):
        return 'Tournament #{0}'.format(self.pk)

    def get_absolute_url(self):
        return '/swiss/tournament/{0}/'.format(self.pk)

    def can_update_players_elos(self):
        current_round = self.get_current_round()
        if current_round:
            is_last_round = current_round.number == self.number_of_rounds
        return is_last_round and current_round.is_finished() and not self.is_finished

    def get_ranked_players(self):
        ranked_players = TournamentRank.objects.filter(tournament=self).order_by('-score', '-buchholz_factor')
        return ranked_players

    def get_current_round(self):
        try:
            return Round.objects.filter(tournament=self).latest('number')
        except Round.DoesNotExist:
            return None

    def start_next_round(self):
        check = datetime.now()
        current_round = self.get_current_round()

        if current_round:
            new_round_number = current_round.number + 1
        else:
            new_round_number = 1

        tournament_round = Round.objects.create(
            tournament=self,
            number=new_round_number,
        )

        print 'lots and rounds created in', datetime.now() - check

        check = datetime.now()

        proxy_groups = RoundGroupProxyList(RoundGroupProxy.get_round_groups(tournament_round))
        groups = proxy_groups.save_round_groups()

        print 'groups created in', datetime.now() - check

        check = datetime.now()

        loted_players = []
        matchups_to_bulk = []
        for group in groups:
            matchups, played_lots = group.generate_matchups()
            matchups_to_bulk.extend(matchups)
            loted_players.extend([lot.player for lot in played_lots])

        Matchup.objects.bulk_create(matchups_to_bulk)

        print 'matchups created', datetime.now() - check

        check = datetime.now()

        tournament_round.set_nonplayer(loted_players)

        print 'nonplayer modified in', datetime.now() - check

        return tournament_round

    def finish_tournament(self):

        def get_ev(player1, player2):
            '''
            calculates expectation value for player1 in game with player2
            NB: funciton is non commutative: get_ev(p1, p2) != get_ev(p2, p1)
            '''
            ra = player1.player.elo
            rb = player2.player.elo
            degree = (rb - ra) / 400.
            res = 1. / (1 + 10**degree)
            return res

        check = datetime.now()
        tournament_ranks = TournamentRank.objects.filter(tournament=self)

        final_results = {}

        for ranked_player in tournament_ranks:
            matchups = Matchup.objects.filter(Q(black=ranked_player)|Q(white=ranked_player)).select_related('black', 'white')
            expected_values = []
            opponents_scores = []
            for matchup in matchups:
                if ranked_player == matchup.black:
                    expected_value = get_ev(ranked_player, matchup.white)
                    opponents_scores.append(matchup.white.score)
                elif ranked_player == matchup.white:
                    expected_value = get_ev(ranked_player, matchup.black)
                    opponents_scores.append(matchup.black.score)
                
                expected_values.append(expected_value)

            k_factor = ranked_player.get_k_factor()
            final_elo = round(ranked_player.player.elo + 16*(ranked_player.score - sum(expected_values)), 2)
            buchholz_factor = sum(opponents_scores)
            ranked_player.final_elo = final_elo
            ranked_player.buchholz_factor = buchholz_factor
            ranked_player.save()

            final_results[ranked_player.id] = (final_elo, buchholz_factor)
        

        self.is_finished = True
        self.save()

        print 'new Elo ratings and Buchholz factors has been calculated in', datetime.now() - check

        return final_results


class RoundGroupProxy(object):

    def __init__(self, tournament_round, score_value):
        self.score_value = score_value
        self.tournament_round = tournament_round

        players = []
        for player in tournament_round.tournament.tournamentrank_set.filter(score=score_value):
            players.append([player, None])

        if [player[0].score for player in players] == [0]*len(players):
            self.players = sorted(players, key=lambda player: player[0].player.elo)
        else:
            self.players = sorted(players, key=lambda player: player[0].score)

        self.round_group = self.save_round_group()

    @classmethod
    def get_round_groups(cls, tournament_round):
        player_ranks = tournament_round.tournament.tournamentrank_set.all()

        def evenify_groups(groups):
            player = None
            for group in groups:
                if player:
                    group.add_player(player)
                if len(group.players) % 2 != 0:
                    player = group.pop_player()
                else:
                    player = None
            return groups

        unique_score_values = [player_rank['score'] for player_rank in player_ranks.values('score').distinct()]
        groups = [cls(tournament_round, score_value) for score_value in unique_score_values]
        sorted_groups = sorted(groups, key=lambda group: group.score_value)

        return evenify_groups(sorted_groups)

    def __repr__(self):
        return '{0} score group'.format(self.score_value)

    def add_player(self, player):
        if player or self.players:
            self.players.append(player)
            sorted(self.players, key=lambda player: player[0].score)        

    def pop_player(self):
        player = self.players[0]
        player[1] = 'shifted'
        self.players.remove(player)
        return player

    def save_round_group(self):
        round_group = RoundGroup.objects.create(
            score_value=self.score_value,
            tournament_round=self.tournament_round
        )
        return round_group


class RoundGroupProxyList(list):

    def save_round_groups(self):
        round_groups = []
        round_group_lots = []

        for group in self:
            round_groups.append(group.round_group)
            for player in group.players:
                round_group_lots.append(
                    Lot(
                        player=player[0].player,
                        round_group=group.round_group,
                        is_shifted=(player[1]=='shifted'),
                    )
                )

        Lot.objects.bulk_create(round_group_lots)

        return round_groups
