import random
import matplotlib.pyplot as plt
from collections import defaultdict, deque

N_TEAMS = 3

NUM_TICKS = 50

STRIKES = [50, 60, 70, 80, 90]
OPTION_TYPES = ['C', 'P']

ALL_OPTION_SYMBOLS = [(strike, opt_type) for strike in STRIKES for opt_type in OPTION_TYPES]
deck = []
for rank in range(1, 14):
    for _ in range(4):
        deck.append(rank)

random.shuffle(deck)

team_cards = {}
for team_id in range(N_TEAMS):
    team_cards[team_id] = deck.pop()

def create_empty_orderbook():
    return {
        "bids": deque(),
        "asks": deque()
    }

order_books = {symbol: create_empty_orderbook() for symbol in ALL_OPTION_SYMBOLS}

open_orders = {}
team_cash = {team_id: 0.0 for team_id in range(N_TEAMS)}
team_positions = {
    team_id: {(strike, opt_type): 0 for strike, opt_type in ALL_OPTION_SYMBOLS}
    for team_id in range(N_TEAMS)
}
team_pnl_history = {team_id: [] for team_id in range(N_TEAMS)}

def get_final_sum_of_cards():
    return sum(team_cards.values())

def option_payoff(strike, opt_type, final_underlying):
    if opt_type == 'C':
        return max(0, final_underlying - strike)
    else:  # 'P'
        return max(0, strike - final_underlying)

def mark_to_market(team_id, current_underlying):
    """
    Mark-to-market PnL for a team at a given underlying level.
    We'll do a naive approach: fair value of the option is the *intrinsic value*,
    ignoring time value. Modify as needed (e.g., use a model).
    """
    mtm = team_cash[team_id]
    return mtm

#############################
#ORDER MATCHING ENGINE
#############################
ORDER_ID_COUNTER = 0

def place_order(team_id, symbol, side, price, size = 1):
    """
    Place an order in the LOB. side in {"BUY","SELL"}.
    """

    global ORDER_ID_COUNTER
    ORDER_ID_COUNTER += 1
    order_id = ORDER_ID_COUNTER

    if size <= 0:
        return

    book = order_books[symbol]

    if side == "BUY":
        bids = book["bids"]
        inserted = False
        for i in range(len(bids)):
            if price > bids[i][0]:
                bids.insert(i, (price, size, team_id, order_id))
                inserted = True
                break
        if not inserted:
            bids.append((price, size, team_id, order_id))
        open_orders[(team_id, order_id)] = (symbol, side, price, size)
    else:
        asks = book["asks"]
        inserted = False
        for i in range(len(asks)):
            if price < asks[i][0]:
                asks.insert(i, (price, size, team_id, order_id))
                inserted = True
                break
        if not inserted:
            asks.append((price, size, team_id, order_id))
        open_orders[(team_id, order_id)] = (symbol, side, price, size)

def match_orders():
    """
    After all teams have placed orders this tick, cross the LOB. 
    If the best bid >= best ask, we have a trade at the mid (or choose ask or bid).
    Here, for simplicity, let's trade at the midpoint or at the ask price.
    We'll do a naive “match-one-lot-at-a-time” approach.
    """
    for symbol in ALL_OPTION_SYMBOLS:
        book = order_books[symbol]
        bids = book["bids"]
        asks = book["asks"]

        # Keep crossing while best bid >= best ask
        while bids and asks and (bids[0][0] >= asks[0][0]):
            best_bid_price, bid_size, bid_team, bid_order_id = bids[0]
            best_ask_price, ask_size, ask_team, ask_order_id = asks[0]

            trade_price = best_ask_price

            traded_size = min(bid_size, ask_size)

            team_cash[bid_team] -= trade_price * traded_size
            team_cash[ask_team] += trade_price * traded_size

            team_positions[bid_team][symbol] += traded_size
            team_positions[ask_team][symbol] -= traded_size

            new_bid_size = bid_size - traded_size
            new_ask_size = ask_size - traded_size

            if new_bid_size <= 0:
                bids.popleft()
                if (bid_team, bid_order_id) in open_orders:
                    del open_orders[(bid_team, bid_order_id)]
            else:
                bids[0] = (best_bid_price, new_bid_size, bid_team, bid_order_id)
                open_orders[(bid_team, bid_order_id)] = (symbol, "BUY", best_bid_price, new_bid_size)

            if new_ask_size <= 0:
                asks.popleft()
                if (ask_team, ask_order_id) in open_orders:
                    del open_orders[(ask_team, ask_order_id)]
            else:
                asks[0] = (best_ask_price, new_ask_size, ask_team, ask_order_id)
                open_orders[(ask_team, ask_order_id)] = (symbol, "SELL", best_ask_price, new_ask_size)

#############################
#TEAM STRATEGY FUNCTIONS
#############################
def random_strategy(last_tick_orders, team_id, current_tick):
    """
    Places random bids and asks for demonstration. 
    Real strategies will be provided by the teams.
    """
    orders = []
    n_orders = random.randint(0, 2)
    for _ in range(n_orders):
        symbol = random.choice(ALL_OPTION_SYMBOLS)
        side = random.choice(["BUY", "SELL"])
        price = random.uniform(0.0, 5.0) 
        size = random.randint(1, 3)
        orders.append((symbol, side, price, size))
    return orders

team_strategies = {
    0: random_strategy,
    1: random_strategy,
    2: random_strategy
}

#############################
#MAIN SIMULATION LOOP
#############################
def run_simulation():
    current_underlying = sum(team_cards.values())
    for t_id in range(N_TEAMS):
        team_pnl_history[t_id].append(mark_to_market(t_id, current_underlying))

    last_tick_orders = []

    for tick in range(1, NUM_TICKS + 1):
        this_tick_orders = []
        for t_id in range(N_TEAMS):
            strategy_fn = team_strategies[t_id]
            new_orders = strategy_fn(last_tick_orders, t_id, tick)
            for (symbol, side, price, size) in new_orders:
                place_order(t_id, symbol, side, price, size)
            this_tick_orders.append((t_id, new_orders))

        match_orders()
        current_underlying = sum(team_cards.values())
        for t_id in range(N_TEAMS):
            mtm_val = mark_to_market(t_id, current_underlying)
            team_pnl_history[t_id].append(mtm_val)

        last_tick_orders = this_tick_orders

    final_sum = get_final_sum_of_cards()
    final_pnls = {}
    for t_id in range(N_TEAMS):
        payoff = 0
        for symbol, qty in team_positions[t_id].items():
            strike, opt_type = symbol
            payoff += qty * option_payoff(strike, opt_type, final_sum)

        final_pnls[t_id] = team_cash[t_id] + payoff
        team_pnl_history[t_id].append(final_pnls[t_id]) 

    print("\n--- FINAL RESULTS ---")
    print(f"Final sum of all cards = {final_sum}")
    for t_id in range(N_TEAMS):
        print(f"Team {t_id}: Final PnL = {final_pnls[t_id]:.2f}")

    plt.figure(figsize=(10,6))
    for t_id in range(N_TEAMS):
        plt.plot(team_pnl_history[t_id], label=f"Team {t_id}")
    plt.title("Team PnL Through Time (Mark-to-Market)")
    plt.xlabel("Tick")
    plt.ylabel("PnL")
    plt.legend()
    plt.show()


if __name__ == "__main__":
    run_simulation()