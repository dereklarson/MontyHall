import numpy as np
import copy
import pprint
from collections import defaultdict


class Game:
    def __init__(self, rng=None, n_doors=3, n_goats=2, max_doors=None, verbose=0):
        """Configure and initialize the game
        rng: our random number generator, the numpy default is quite good (PCG64)
        n_doors (int): sets the number of doors. set to None and use max_doors
        n_goats (int): sets the number of goats, set to None for random in (0, n_doors)
        max_doors (int): if n_doors is None, it is randomized between min_ and max_doors
        verbose: set to 1 for some informational output, 2 for full output
        """
        # Get settings
        self.rng = rng or np.random.default_rng()
        self.min_doors = 3
        self.max_doors = max_doors or 3
        self.verbose = verbose

        # Initialize meta-state
        self.rerolls = 0

        # First game initialization
        self.initialize_state(n_doors, n_goats)

    def initialize_state(self, n_doors, n_goats):
        """Initializes an individual game, which might happen more than once (reroll)"""
        self.choice = None    # Current player selection
        self.win = False      # Whether the game is a win result for the player
        self.args = (n_doors, n_goats)  # Store for reinitialization
        # Either directly set number of doors/goats or randomize them
        door_spread = self.max_doors - self.min_doors + 1
        self.n_doors = n_doors or self.rng.integers(door_spread) + self.min_doors
        self.n_goats = n_goats or self.rng.integers(self.n_doors + 1)

        # State of the prizes and doors: by default, all have prizes and are not visible
        self.state = {
            'prizes': np.ones(self.n_doors, dtype=bool),
            'visible': np.zeros(self.n_doors, dtype=bool),
        }

        # Then, place goats randomly (N objects, choose k without replacement)
        goatidxs = self.rng.choice(self.n_doors, self.n_goats, replace=False)
        self.state['prizes'][goatidxs] = False

    def pstate(self):
        print(f"{self.n_goats} / {self.n_doors}")
        pprint.pprint(self.state)

    def choose(self, strategy='random'):
        # If a prize is visible somehow, take it!
        if any(prizeviz := np.multiply(self.state['visible'], self.state['prizes'])):
            self.choice = list(prizeviz).index(True)
            if self.verbose:
                print("Taking a revealed prize")
        if strategy == 'stay':
            if self.choice is not None:
                return
            elif self.verbose:
                print(f"Attempting stay with {self.choice}")
            return
        # Now, use passed strategy to choose option from the closed doors
        options = [idx for idx, visible in enumerate(self.state['visible'])
                   if not visible]
        if strategy == 'random':
            self.choice = options[self.rng.integers(len(options))]
        elif strategy == 'update':
            if self.choice is not None:
                try:
                    options.remove(self.choice)
                except Exception:
                    if self.verbose:
                        print(f"Could not remove {self.choice} from {options}")
            self.choice = options[self.rng.integers(len(options))]

    def reveal(self, strategy='goat'):
        """Host reveals a door based on a strategy, default being a random unchosen goat
        If the host can't reveal a door based on the strategy, we return a True value to
        indicate the need to "reroll" the game (otherwise our stats are off)
        """

        if strategy == 'goat':
            options = [idx for idx, prize in enumerate(self.state['prizes'])
                       if not prize]
            if self.choice in options:
                options.remove(self.choice)
            if not len(options):
                if self.verbose:
                    print("No goats left to reveal, rerolling")
                    # Reroll so we get a valid series of game events
                return True
        elif strategy == 'random':
            # Anything except the current player choice
            options = [idx for idx in range(self.n_doors) if idx != self.choice]

        else:
            print(f"Game strategy not supported {strategy}")

        # Reveal a random, allowable door
        self.state['visible'][options[self.rng.integers(len(options))]] = True

    def play(self, player="update", host="goat"):
        """A standard game is:
            1) choose door randomly
            2) A reveal or other update
            3) optionally choose again
            """
        self.choose(strategy='random')

        # A true return for reveal means we reroll the game
        if self.reveal(strategy=host):
            self.rerolls += 1
            if self.rerolls > 10:
                print("Too many rerolls within game...bug alert")
            self.initialize_state(*self.args)
            return self.play(player, host)

        # The player's second choice
        self.choose(strategy=player)
        self.win = self.state['prizes'][self.choice]
        return self.win

class GameSeries:
    def __init__(self, config):
        self.rng = np.random.default_rng()
        self.config = copy.deepcopy(config)
        self.config['rules']['max_doors'] = (self.config['rules']['max_doors']
                                             or self.config['rules']['n_doors'])

        # Data collection
        self.history = []
        self.stats = defaultdict(int)

    def header(self):
        player = self.config['strategies']['player']
        host = self.config['strategies']['host']
        print(f"\n--- Simulating player strategy: {player} vs host strategy: {host} ---")
        goats = self.config['rules']['n_goats'] or "random"
        doors = (self.config['rules']['n_doors'] or
                 f"from 3 to {self.config['rules']['max_doors']}")
        print(f"--- Using {goats} goats and {doors} doors ---")

    def pstats(self):
        print(f"Rerolls: {self.stats['rerolls']}")
        fraction = self.stats['win'] / self.config['games']

        variants = 0
        for ct in range(self.config['rules']['max_doors'] + 1):
            basekey = f"{ct}_goats"
            wins = self.stats[f"{basekey}_wins"]
            total = self.stats[basekey]
            if total:
                variants += 1
                print(f"{basekey.replace('_',' ')}: won {wins} / {total}"
                        "for {100 * wins / total:.1f}%")

        if variants > 1:
            print(f"Aggregate Outcome: won {self.stats['win']} / {self.config['games']}"
                    "for {fraction:.3f}")

    def simulate(self, n=None):
        n = n or self.config['games']
        for game_idx in range(n):
            if self.config.get('verbose', 0) > 1:
                print(f"---Game {game_idx + 1}")
            game = Game(rng=self.rng, **(self.config['rules']))
            game.play(**(self.config['strategies']))
            self.history.append(game)
            for stat in ['win', 'rerolls']:
                self.stats[stat] += getattr(game, stat)

            for ct in range(self.config['rules']['max_doors'] + 1):
                # Count type of game played
                self.stats[f"{ct}_goats"] += (ct == game.n_goats)
                self.stats[f"{ct}_goats_wins"] += (ct == game.n_goats) and game.win
        
    def test(self):
        #Test to see if there are issues
        exceptions = 0
        print("Testing -- ( games | player | host )")
        for games in [1, 10, 100]:
            for player in ['stay', 'random', 'update']: 
                for host in ['goat', 'random']:
                    self.config['games'] = games
                    self.config['strategies']['player'] = player
                    self.config['strategies']['host'] = host
                    if self.config.get('verbose', 0):
                        print(f"{' '*13}{str(games).ljust(8)}"
                               "{player.ljust(9)}{host.ljust(9)}")
                    if exceptions > 5:
                        break
                    try:
                        self.simulate()
                    except Exception as exc:
                        print(exc)
                        exceptions += 1
        print(f"Total exceptions {exceptions}")
