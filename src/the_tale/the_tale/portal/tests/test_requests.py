# coding: utf-8
from unittest import mock

from django.conf import settings as project_settings

from dext.common.utils.urls import url

from the_tale.common.utils import testcase

from the_tale.game.abilities.relations import ABILITY_TYPE

from the_tale.game.logic import create_test_map
from the_tale.game.balance import constants as c

from the_tale.forum.tests.helpers import ForumFixture


class TestRequests(testcase.TestCase):

    def setUp(self):
        super(TestRequests, self).setUp()
        create_test_map()

    def test_search(self):
        self.check_html_ok(self.request_html(url('portal:search')))

    def test_chat(self):
        self.check_html_ok(self.request_html(url('portal:chat')))

    def test_landing(self):
        self.check_html_ok(self.request_html(url('portal:landing')))

    def test_preview(self):
        text = 'simple test text'
        self.check_html_ok(self.client.post(url('portal:preview'), {'text': text}), texts=[text])

    def test_hot_themes__show_all(self):
        forum = ForumFixture(self.accounts_factory)
        self.check_html_ok(self.request_html(url('portal:')), texts=[forum.thread_1.caption, forum.thread_2.caption, forum.thread_3.caption])

    def test_hot_themes__hide_restricted_themes(self):
        forum = ForumFixture(self.accounts_factory)
        forum.subcat_3._model.restricted = True
        forum.subcat_3.save()
        self.check_html_ok(self.request_html(url('portal:')), texts=[forum.thread_1.caption, forum.thread_2.caption, (forum.thread_3.caption, 0)])

    def test_info(self):
        self.check_ajax_ok(self.request_json(url('portal:api-info', api_version='1.0', api_client=project_settings.API_CLIENT)),
                           data={'static_content': project_settings.STATIC_URL,
                                 'game_version': project_settings.META_CONFIG.version,
                                 'turn_delta': c.TURN_DELTA,
                                 'account_id': None,
                                 'account_name': None,
                                 'abilities_cost': {ability_type.value: ability_type.cost for ability_type in ABILITY_TYPE.records}})

    def test_info__logined(self):
        account = self.accounts_factory.create_account()
        self.request_login(account.email)

        self.check_ajax_ok(self.request_json(url('portal:api-info', api_version='1.0', api_client=project_settings.API_CLIENT)),
                           data={'static_content': project_settings.STATIC_URL,
                                 'game_version': project_settings.META_CONFIG.version,
                                 'turn_delta': c.TURN_DELTA,
                                 'account_id': account.id,
                                 'account_name': account.nick,
                                 'abilities_cost': {ability_type.value: ability_type.cost for ability_type in ABILITY_TYPE.records}})



class IndexRequestTests(testcase.TestCase):

    def setUp(self):
        super(IndexRequestTests, self).setUp()
        create_test_map()


    def test_success(self):
        response = self.client.get(url('portal:'))
        self.assertEqual(response.status_code, 200)


    @mock.patch('the_tale.portal.conf.portal_settings.FIRST_TIME_LANDING_URLS', ['/x', '/x'])
    def test_first_time_redirect(self):
        with mock.patch('the_tale.portal.conf.portal_settings.ENABLE_FIRST_TIME_REDIRECT', True):
            with mock.patch('the_tale.accounts.logic.is_first_time_visit', lambda request: True):
                self.check_redirect('/', '/x')
            with mock.patch('the_tale.accounts.logic.is_first_time_visit', lambda request: False):
                self.check_html_ok(self.request_html('/'))

        with mock.patch('the_tale.portal.conf.portal_settings.ENABLE_FIRST_TIME_REDIRECT', False):
            with mock.patch('the_tale.accounts.logic.is_first_time_visit', lambda request: True):
                self.check_html_ok(self.request_html('/'))
            with mock.patch('the_tale.accounts.logic.is_first_time_visit', lambda request: False):
                self.check_html_ok(self.request_html('/'))
