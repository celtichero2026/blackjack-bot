import random

SUITS = ["♠", "♥", "♦", "♣"]

RANKS = {
    "A": 11,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "10": 10,
    "J": 10,
    "Q": 10,
    "K": 10
}


class Deck:
    def __init__(self):
        self.cards = []

        for suit in SUITS:
            for rank in RANKS.keys():
                self.cards.append((rank, suit))

        random.shuffle(self.cards)

    def draw(self):
        return self.cards.pop()


def hand_value(hand):
    total = sum(RANKS[card[0]] for card in hand)

    aces = sum(1 for card in hand if card[0] == "A")

    while total > 21 and aces:
        total -= 10
        aces -= 1

    return total
