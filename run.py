import copy

from montyhall import GameSeries

config = {
    'games': 10000,
    'rules': {
        'max_doors': None,
        'n_doors': 3,
        'n_goats': None,
    },
    'strategies': {
        # A player's strategy can be the following:
        #   'stay' -- stick with first choice
        #   'update' -- switch to a new un-revealed door (randomly) after a reveal
        #   'random' -- select a random un-revealed door again (could be original choice)
        'player': 'update',
        # The host's strategy can be the following:
        #   'goat' -- reveals a goat that isn't the player's choice
        #   'random' -- opens a random door that isn't the player's choice
        'host': 'goat',
    },
}

if __name__ == "__main__":
    GameSeries(config).test()

    for player_strategy in ['stay', 'random', 'update']:
        curr_config = copy.deepcopy(config)
        curr_config['strategies']['player'] = player_strategy
        simulator = GameSeries(curr_config)
        simulator.header()
        simulator.simulate()
        simulator.pstats()
