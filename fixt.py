from swiss.models import Player, Tournament, Round

first_names = ['ALEXEI', 'PETR', 'IAN', 'NOAH', 'PAK', 'LI']
second_names = ['EGOROV', 'PETROV', 'JOHNSON', 'MCDONALD', 'WATANABE', 'PAULS']

def createplayers(count=11):
    import random
    players = []
    for i in range(count):
        players.append(Player(
            name = '{0} {1}'.format(random.choice(first_names), random.choice(second_names)),
            elo = 2500 + random.randint(1, 100)
        ))
    Player.objects.bulk_create(players)

def play_whole_round(round_id):
    import random
    import urllib2
    from datetime import datetime

    matchup_ids = []
    round_groups = Round.objects.get(id=round_id).roundgroup_set.all()

    for round_group in round_groups:
        for matchup in round_group.matchup_set.all():
            matchup_ids.append(matchup.id)

    starts_at = datetime.now()
    # for i in range(int(from_id), int(to_id)):
    for i in matchup_ids:
        url = 'http://localhost:8080/swiss/matchup/{0}/{1}/'.format(i, random.choice(['black', 'white', 'draw']))
        urllib2.urlopen(url)
    print 'works for'
    print datetime.now() - starts_at

def get_buchholtz_for_tournament(tournament_id):
    import urllib2
    from datetime import datetime
    starts_at = datetime.now()

    tournament = Tournament.objects.get(id=tournament_id)
    ranks = tournament.tournamentrank_set.all()
    
    for player in ranks:
        bhz = player.get_buchholz_factor()
        print player, bhz

    print 'works for'
    print datetime.now() - starts_at