import math
from datetime import datetime

from django.db import models
from django.db.models import Q

SCORE_FOR_WIN = 1.0
SCORE_FOR_DRAW = 0.5
SCORE_FOR_NONPLAY = 0.5


class Player(models.Model):
    name = models.CharField(max_length=100)
    elo = models.FloatField()

    def __unicode__(self):
        return '{0} - {1}'.format(self.name, self.elo)

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
        if self.black_score == SCORE_FOR_WIN:
            return 'Black'
        elif self.white_score == SCORE_FOR_WIN:
            return 'White'
        elif self.black_score == self.white_score == SCORE_FOR_DRAW:
            return 'Draw'
        else:
            return 'Not played yet'

    def is_not_played(self):
        return self.black_score == self.white_score == 0


class Round(models.Model):

    number = models.PositiveIntegerField()
    tournament = models.ForeignKey('Tournament')

    nonplayer = models.ForeignKey(Player, null=True, blank=True)

    def __unicode__(self):
        return 'Round #{0}'.format(self.number)

    def get_absolute_url(self):
        return '/swiss/round/{0}/'.format(self.pk)

    def is_finished(self):
        round_groups = self.roundgroup_set.all()
        matchups = Matchup.objects.filter(round_group__in=round_groups, black_score=0, white_score=0)
        return not matchups.exists()

    def get_next_round(self):
        try:
            return Round.objects.get(tournament=self.tournament, number=self.number+1)
        except Round.DoesNotExist:
            return None

    def is_latest(self):
        return self.number == self.tournament.number_of_rounds

    def set_nonplayer(self, loted_players):
        tournament_ranks = TournamentRank.objects.filter(tournament=self.tournament)
        nonplayer_as_list = list(set(tournament_ranks) - set(loted_players))

        if nonplayer_as_list:
            nonplayer = nonplayer_as_list[0]
            nonplayer.score += SCORE_FOR_NONPLAY
            nonplayer.save()
            self.nonplayer = nonplayer.player
            self.save()
            return nonplayer
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
        group_lots = self.lot_set.all().select_related('player').order_by('-player__score', '-player__starting_elo')
        played_lots = []
        matchups = []

        for number in range(len(group_lots) / 2):

            black = group_lots[number]
            white = group_lots[len(group_lots)/2+number]
            
            matchups.append(
                Matchup(
                    black=black.player,
                    white=white.player,
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
        return '{0} - {1} - {2}'.format(self.rank, self.player.name, self.player.elo)

    def get_buchholz_factor(self):
        from django.db.models import Sum
        white_score = Matchup.objects.filter(black=self).aggregate(Sum('white__score'))
        black_score = Matchup.objects.filter(white=self).aggregate(Sum('black__score'))
        return (black_score['black__score__sum'] or 0) + (white_score['white__score__sum'] or 0)

    def set_buchholtz_factor(self):
        self.buchholz_factor = self.get_buchholz_factor()
        self.save()

    def get_k_factor(self):

        BOTTOM_LINE = 2100
        MIDDLE_LINE = 2400

        if self.score < BOTTOM_LINE:
            return 32
        elif self.score < MIDDLE_LINE:
            return 24
        else:
            return 16


class Lot(models.Model):
    player = models.ForeignKey(TournamentRank)
    round_group = models.ForeignKey(RoundGroup)

    is_shifted = models.BooleanField(default=False)

    class Meta:
        unique_together = (
            ('round_group', 'player'),
        )


    def __unicode__(self):
        return 'Lot: {0} for {1}'.format(self.player.player, self.round_group)


class Tournament(models.Model):
    number_of_winners = models.PositiveIntegerField(default=1)
    number_of_rounds = models.PositiveIntegerField(default=0)

    is_finished = models.BooleanField(default=False)

    def __unicode__(self):
        return 'Tournament #{0}'.format(self.pk)

    def get_absolute_url(self):
        return '/swiss/tournament/{0}/'.format(self.pk)

    @classmethod
    def start_tournament(cls, players, number_of_winners):
        check = datetime.now()

        number_of_rounds = round(math.log(len(players), 2)) + round(math.log(number_of_winners, 2))
        tournament = cls.objects.create(number_of_winners=number_of_winners, number_of_rounds=number_of_rounds)

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

        tournament.start_next_round()

        print 'round started', datetime.now() - check

        return tournament

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

        tournament_round = Round.objects.create(tournament=self, number=new_round_number)

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

        def get_ev(tournament_rank1, tournament_rank2):
            '''
            calculates expectation value for player1 in game with player2
            NB: funciton is non commutative: get_ev(p1, p2) != get_ev(p2, p1)
            '''
            r_a = tournament_rank1.player.elo
            r_b = tournament_rank2.player.elo
            degree = (r_b - r_a) / 400.
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
            final_elo = round(ranked_player.player.elo + k_factor*(ranked_player.score - sum(expected_values)), 2)
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

        ranks = []
        for rank in tournament_round.tournament.tournamentrank_set.filter(score=score_value):
            ranks.append([rank, None])

        if [rank[0].score for rank in ranks] == [0]*len(ranks):
            self.ranks = sorted(ranks, key=lambda rank: rank[0].player.elo)
        else:
            self.ranks = sorted(ranks, key=lambda rank: rank[0].score)

        self.round_group = self.save_round_group()

    @classmethod
    def get_round_groups(cls, tournament_round):
        ranks = tournament_round.tournament.tournamentrank_set.all()

        def evenify_groups(groups):
            rank = None
            for group in groups:
                if rank:
                    group.add_rank(rank)
                if len(group.ranks) % 2 != 0:
                    rank = group.pop_rank()
                else:
                    rank = None
            return groups

        unique_score_values = [player_rank['score'] for player_rank in ranks.values('score').distinct()]
        groups = [cls(tournament_round, score_value) for score_value in unique_score_values]
        sorted_groups = sorted(groups, key=lambda group: group.score_value)

        return evenify_groups(sorted_groups)

    def __repr__(self):
        return '{0} score group'.format(self.score_value)

    def add_rank(self, rank):
        if rank or self.ranks:
            self.ranks.append(rank)
            self.ranks = sorted(self.ranks, key=lambda rank: rank[0].score)        

    def pop_rank(self):
        rank = self.ranks[0]
        rank[1] = 'shifted'
        self.ranks.remove(rank)
        return rank

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
            for rank in group.ranks:
                round_group_lots.append(
                    Lot(
                        player=rank[0],
                        round_group=group.round_group,
                        is_shifted=(rank[1] == 'shifted'),
                    )
                )

        Lot.objects.bulk_create(round_group_lots)

        return round_groups
