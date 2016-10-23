# coding: utf-8

from the_tale.amqp_environment import environment

from the_tale.common.utils.workers import BaseWorker

from the_tale.game.conf import game_settings
from the_tale.game.prototypes import GameState


class TurnsLoopException(Exception): pass

class Worker(BaseWorker):
    NO_CMD_TIMEOUT = game_settings.TURN_DELAY

    def process_no_cmd(self):
        if GameState.is_working():
            self.logger.info('send next turn command')
            environment.workers.supervisor.cmd_next_turn()
        else:
            self.logger.info('skip next turn command, since game is stopped')


    def initialize(self):
        if self.initialized:
            self.logger.warn('WARNING: turn loop already initialized, do reinitialization')

        self.initialized = True

        self.logger.info('TURN LOOP INITIALIZED')