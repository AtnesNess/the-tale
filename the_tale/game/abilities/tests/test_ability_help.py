# coding: utf-8
import mock

from the_tale.common.utils import testcase

from the_tale.accounts.prototypes import AccountPrototype
from the_tale.accounts.logic import register_user

from the_tale.game.logic_storage import LogicStorage
from the_tale.game.logic import create_test_map

from the_tale.game.prototypes import TimePrototype
from the_tale.game.actions import prototypes as actions_prototypes

from the_tale.game.heroes.logic import create_mob_for_hero
from the_tale.game.heroes.relations import HABIT_CHANGE_SOURCE

from the_tale.game.abilities.deck.help import Help
from the_tale.game.abilities.relations import HELP_CHOICES

from the_tale.game.pvp.prototypes import Battle1x1Prototype
from the_tale.game.pvp.models import BATTLE_1X1_STATE

from the_tale.game.postponed_tasks import ComplexChangeTask


class HelpAbilityTest(testcase.TestCase):

    def setUp(self):
        super(HelpAbilityTest, self).setUp()
        self.p1, self.p2, self.p3 = create_test_map()


        result, account_id, bundle_id = register_user('test_user_1', 'test_user_1@test.com', '111111')

        self.account = AccountPrototype.get_by_id(account_id)
        self.storage = LogicStorage()
        self.storage.load_account_data(self.account)
        self.hero = self.storage.accounts_to_heroes[self.account.id]
        self.action_idl = self.hero.actions.current_action

        self.ability = Help()

    @property
    def use_attributes(self):
        return {'data': {'hero_id': self.hero.id},
                'step': None,
                'main_task_id': 0,
                'storage': self.storage,
                'pvp_balancer': None}

    def test_none(self):
        with mock.patch('the_tale.game.actions.prototypes.ActionBase.get_help_choice', lambda x: None):
            with self.check_not_changed(lambda: self.hero.statistics.help_count):
                self.assertEqual(self.ability.use(**self.use_attributes), (ComplexChangeTask.RESULT.FAILED, None, ()))

    def test_help_when_battle_waiting(self):
        battle = Battle1x1Prototype.create(self.account)
        self.assertTrue(battle.state.is_WAITING)
        with self.check_delta(lambda: self.hero.statistics.help_count, 1):
            self.assertEqual(self.ability.use(**self.use_attributes), (ComplexChangeTask.RESULT.SUCCESSED, None, ()))

    def test_help_when_battle_not_waiting(self):
        battle = Battle1x1Prototype.create(self.account)
        battle.state = BATTLE_1X1_STATE.PREPAIRING
        battle.save()

        self.assertFalse(battle.state.is_WAITING)
        with self.check_not_changed(lambda: self.hero.statistics.help_count):
            self.assertEqual(self.ability.use(**self.use_attributes), (ComplexChangeTask.RESULT.FAILED, None, ()))

    def test_heal(self):
        self.hero.health = 1
        with mock.patch('the_tale.game.actions.prototypes.ActionBase.get_help_choice', lambda x: HELP_CHOICES.HEAL):
            with self.check_delta(lambda: self.hero.statistics.help_count, 1):
                self.assertEqual(self.ability.use(**self.use_attributes), (ComplexChangeTask.RESULT.SUCCESSED, None, ()))
                self.assertTrue(self.hero.health > 1)

    def test_start_quest(self):
        with mock.patch('the_tale.game.actions.prototypes.ActionBase.get_help_choice', lambda x: HELP_CHOICES.START_QUEST):
            with self.check_delta(lambda: self.hero.statistics.help_count, 1):
                self.assertEqual(self.ability.use(**self.use_attributes), (ComplexChangeTask.RESULT.SUCCESSED, None, ()))
                self.assertTrue(self.action_idl.percents >= 1)

    def test_experience(self):
        old_experience = self.hero.experience
        with mock.patch('the_tale.game.actions.prototypes.ActionBase.get_help_choice', lambda x: HELP_CHOICES.EXPERIENCE):
            with self.check_delta(lambda: self.hero.statistics.help_count, 1):
                self.assertEqual(self.ability.use(**self.use_attributes), (ComplexChangeTask.RESULT.SUCCESSED, None, ()))

        self.assertTrue(old_experience < self.hero.experience)

    def test_stock_up_energy(self):

        with self.check_changed(lambda: self.hero.energy_bonus):
            with mock.patch('the_tale.game.actions.prototypes.ActionBase.get_help_choice', lambda x: HELP_CHOICES.STOCK_UP_ENERGY):
                with self.check_delta(lambda: self.hero.statistics.help_count, 1):
                    self.assertEqual(self.ability.use(**self.use_attributes), (ComplexChangeTask.RESULT.SUCCESSED, None, ()))

    def test_money(self):
        old_hero_money = self.hero.money
        with mock.patch('the_tale.game.actions.prototypes.ActionBase.get_help_choice', lambda x: HELP_CHOICES.MONEY):
            with self.check_delta(lambda: self.hero.statistics.help_count, 1):
                self.assertEqual(self.ability.use(**self.use_attributes), (ComplexChangeTask.RESULT.SUCCESSED, None, ()))
                self.assertTrue(self.hero.money > old_hero_money)

    @mock.patch('the_tale.game.heroes.prototypes.HeroPositionPrototype.is_battle_start_needed', lambda self: False)
    def test_teleport(self):
        move_place = self.p3
        if move_place.id == self.hero.position.place.id:
            move_place = self.p1

        current_time = TimePrototype.get_current_time()

        action_move = actions_prototypes.ActionMoveToPrototype.create(hero=self.hero, destination=move_place)

        current_time.increment_turn()
        self.storage.process_turn()

        old_road_percents = self.hero.position.percents
        old_percents = action_move.percents

        with mock.patch('the_tale.game.actions.prototypes.ActionBase.get_help_choice', lambda x: HELP_CHOICES.TELEPORT):
            with self.check_delta(lambda: self.hero.statistics.help_count, 1):
                self.assertEqual(self.ability.use(**self.use_attributes), (ComplexChangeTask.RESULT.SUCCESSED, None, ()))

        self.assertTrue(old_road_percents < self.hero.position.percents)
        self.assertTrue(old_percents < action_move.percents)
        self.assertEqual(self.hero.actions.current_action.percents, action_move.percents)


    def test_lighting(self):
        current_time = TimePrototype.get_current_time()
        action_battle = actions_prototypes.ActionBattlePvE1x1Prototype.create(hero=self.hero, mob=create_mob_for_hero(self.hero))

        current_time.increment_turn()
        self.storage.process_turn()

        old_mob_health = action_battle.mob.health
        old_percents = action_battle.percents

        self.assertTrue(HELP_CHOICES.LIGHTING in action_battle.help_choices)

        with mock.patch('the_tale.game.actions.prototypes.ActionBase.get_help_choice', lambda x: HELP_CHOICES.LIGHTING):
            with self.check_delta(lambda: self.hero.statistics.help_count, 1):
                self.assertEqual(self.ability.use(**self.use_attributes), (ComplexChangeTask.RESULT.SUCCESSED, None, ()))

        self.assertTrue(old_mob_health > action_battle.mob.health)
        self.assertEqual(self.hero.actions.current_action.percents, action_battle.percents)
        self.assertTrue(old_percents < action_battle.percents)

    def test_lighting_when_mob_killed(self):
        current_time = TimePrototype.get_current_time()
        action_battle = actions_prototypes.ActionBattlePvE1x1Prototype.create(hero=self.hero, mob=create_mob_for_hero(self.hero))

        current_time.increment_turn()
        self.storage.process_turn()

        action_battle.mob.health = 0

        self.assertFalse(HELP_CHOICES.LIGHTING in action_battle.help_choices)

    def test_resurrect(self):
        current_time = TimePrototype.get_current_time()

        self.hero.kill()
        action_resurrect = actions_prototypes.ActionResurrectPrototype.create(hero=self.hero)

        old_percents = action_resurrect.percents

        with mock.patch('the_tale.game.actions.prototypes.ActionBase.get_help_choice', lambda x: HELP_CHOICES.RESURRECT):
            with self.check_delta(lambda: self.hero.statistics.help_count, 1):
                current_time.increment_turn()
                self.assertEqual(self.ability.use(**self.use_attributes), (ComplexChangeTask.RESULT.SUCCESSED, None, ()))
                self.storage.process_turn(second_step_if_needed=False)

        self.assertEqual(self.hero.health, self.hero.max_health)
        self.assertEqual(self.hero.is_alive, True)
        self.assertTrue(old_percents < action_resurrect.percents)
        self.assertEqual(self.hero.actions.current_action.percents, action_resurrect.percents)


    def test_resurrect__two_times(self):
        current_time = TimePrototype.get_current_time()

        self.hero.kill()
        actions_prototypes.ActionResurrectPrototype.create(hero=self.hero)

        with mock.patch('the_tale.game.actions.prototypes.ActionBase.get_help_choice', lambda x: HELP_CHOICES.RESURRECT):
            with self.check_delta(lambda: self.hero.statistics.help_count, 1):
                current_time.increment_turn()
                self.assertEqual(self.ability.use(**self.use_attributes), (ComplexChangeTask.RESULT.SUCCESSED, None, ()))

        with mock.patch('the_tale.game.actions.prototypes.ActionBase.get_help_choice', lambda x: HELP_CHOICES.RESURRECT):
            with self.check_not_changed(lambda: self.hero.statistics.help_count):
                current_time.increment_turn()
                self.assertEqual(self.ability.use(**self.use_attributes), (ComplexChangeTask.RESULT.IGNORE, None, ()))

    @mock.patch('the_tale.game.actions.prototypes.ActionIdlenessPrototype.AGGRESSIVE', False)
    def test_update_habits__aggressive_action(self):

        with mock.patch('the_tale.game.heroes.prototypes.HeroPrototype.update_habits') as update_habits:
            with self.check_delta(lambda: self.hero.statistics.help_count, 1):
                self.assertEqual(self.ability.use(**self.use_attributes), (ComplexChangeTask.RESULT.SUCCESSED, None, ()))

        self.assertEqual(update_habits.call_args_list, [mock.call(HABIT_CHANGE_SOURCE.HELP_UNAGGRESSIVE)])

    @mock.patch('the_tale.game.actions.prototypes.ActionIdlenessPrototype.AGGRESSIVE', True)
    def test_update_habits__unaggressive_action(self):
        with mock.patch('the_tale.game.heroes.prototypes.HeroPrototype.update_habits') as update_habits:
            with self.check_delta(lambda: self.hero.statistics.help_count, 1):
                self.assertEqual(self.ability.use(**self.use_attributes), (ComplexChangeTask.RESULT.SUCCESSED, None, ()))

        self.assertEqual(update_habits.call_args_list, [mock.call(HABIT_CHANGE_SOURCE.HELP_AGGRESSIVE)])