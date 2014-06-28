from django.test import TestCase, Client

from swiss.models import Player, Tournament, Round, Matchup, RoundGroup
from fixt import createplayers

class TournamentTestCase(TestCase):

    def setUp(self):
        createplayers()
        self.players = Player.objects.all()
        self.client = Client()

        response = self.client.post('/swiss/new_tournament/',
            {'ranked_players': [player.id for player in self.players]},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        self.tournament = Tournament.objects.latest('id')

    def test_tournament_2nd_round(self):
        self.assertEqual(Tournament.objects.all().count(), 1)
        self.assertEqual(Round.objects.all().count(), 1)
        self.assertEqual(Matchup.objects.all().count(), 5)
        matchups = Matchup.objects.all()
        self.assertEqual(RoundGroup.objects.all().count(), 1)

        self.client.get('/swiss/matchup/{0}/black/'.format(matchups[0].id), follow=True)
        self.client.get('/swiss/matchup/{0}/white/'.format(matchups[1].id), follow=True)
        self.client.get('/swiss/matchup/{0}/white/'.format(matchups[2].id), follow=True)
        self.client.get('/swiss/matchup/{0}/draw/'.format(matchups[3].id), follow=True)
        self.client.get('/swiss/matchup/{0}/draw/'.format(matchups[4].id), follow=True)

        self.client.get('/swiss/start_next_round/{0}/'.format(self.tournament.id), follow=True)

        self.assertEqual(Tournament.objects.all().count(), 1)
        self.assertEqual(Round.objects.all().count(), 2)
        self.assertEqual(Matchup.objects.all().count(), 10)
            
        self.assertEqual(RoundGroup.objects.all().count(), 4)
