# coding: utf-8
import time

from game.balance import constants as c

from game.prototypes import TimePrototype, GameTime

from game.heroes.conf import heroes_settings


class MessagesContainer(object):

    def __init__(self):
        self.messages = []
        self.updated = False

    @staticmethod
    def _prepair_message(msg, turn_delta=0):
        return (TimePrototype.get_current_turn_number()+turn_delta, time.time()+turn_delta*c.TURN_DELTA, msg)

    def push_message(self, msg):
        self.updated = True

        self.messages.append(msg)

        if len(self.messages) > 1 and (self.messages[-1][0] < self.messages[-2][0] or self.messages[-1][1] < self.messages[-2][1]):
            self.messages.sort(lambda a, b: cmp(a, b)) # compare tuples

        if len(self.messages) > heroes_settings.MESSAGES_LOG_LENGTH:
            self.messages.pop(0)


    def ui_info(self, with_date=False):
        current_turn = TimePrototype.get_current_turn_number()

        messages = []

        for turn_number, timestamp, msg in self.messages:
            if turn_number > current_turn:
                break
            game_time = GameTime.create_from_turn(turn_number)

            if with_date:
                messages.append((timestamp, game_time.verbose_time, msg, game_time.verbose_date))
            else:
                messages.append((timestamp, game_time.verbose_time, msg))

        return messages

    def serialize(self):
        return {'messages': self.messages}

    @classmethod
    def deserialize(cls, data):
        obj = cls()
        obj.messages = data['messages']
        return obj

    def __eq__(self, other):
        if len(self.messages) != len(other.messages):
            return False

        for a,b in zip(self.messages, other.messages):
            if a[0] != b[0] or a[2] != b[2] or abs(a[1] - b[1]) > 0.0001:
                return False

        return True
