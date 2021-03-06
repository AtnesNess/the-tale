# coding: utf-8

from unittest import mock

from dext.common.utils.urls import url

from the_tale.common.utils.testcase import TestCase

from the_tale.accounts.logic import login_page_url
from the_tale.accounts.personal_messages.prototypes import MessagePrototype

from the_tale.game.logic import create_test_map

from ..prototypes import ClanPrototype, MembershipPrototype, MembershipRequestPrototype
from ..relations import ORDER_BY, MEMBER_ROLE, MEMBERSHIP_REQUEST_TYPE
from ..conf import clans_settings
from .. import meta_relations

from .helpers import ClansTestsMixin

from the_tale.forum.prototypes import CategoryPrototype


class BaseTestRequests(TestCase, ClansTestsMixin):

    def setUp(self):
        super(BaseTestRequests, self).setUp()
        create_test_map()

        CategoryPrototype.create(caption='category-1', slug=clans_settings.FORUM_CATEGORY_SLUG, order=0)

        self.account = self.accounts_factory.create_account()


class TestAccountClanRequests(BaseTestRequests):

    def setUp(self):
        super(TestAccountClanRequests, self).setUp()
        self.account_clan_url = url('accounts:clans:account-clan', account=self.account.id)

    def test_wrong_account_id(self):
        self.check_html_ok(self.request_html(url('accounts:clans:account-clan', account=666)), texts=['clans.account_clan.account.not_found'], status_code=404)
        self.check_html_ok(self.request_html(url('accounts:clans:account-clan', account='bla-bla')), texts=['clans.account_clan.account.wrong_format'])

    def test_no_clan(self):
        self.check_html_ok(self.request_html(url('accounts:clans:account-clan', account=self.account.id)), texts=['clans.account_clan.no_clan'])

    # change tests order to fix sqlite segmentation fault
    def test_1_success(self):
        clan = self.create_clan(self.account, 0)
        self.check_redirect(self.account_clan_url, url('accounts:clans:show', clan.id))


class TestIndexRequests(BaseTestRequests):

    def setUp(self):
        super(TestIndexRequests, self).setUp()

    def test_no_clans(self):
        self.check_html_ok(self.request_html(url('accounts:clans:')),
                           texts=[('pgf-no-clans-message', 1)])

    def test_create_button(self):
        with mock.patch('the_tale.accounts.clans.logic.ClanInfo.can_create_clan', False):
            self.check_html_ok(self.request_html(url('accounts:clans:')),
                               texts=[('pgf-create-clan-button', 0),
                                      ('pgf-create-clan-disabled-button', 1)])

        with mock.patch('the_tale.accounts.clans.logic.ClanInfo.can_create_clan', True):
            self.check_html_ok(self.request_html(url('accounts:clans:')),
                               texts=[('pgf-create-clan-button', 1),
                                      ('pgf-create-clan-disabled-button', 0)])

    @mock.patch('the_tale.accounts.clans.conf.clans_settings.CLANS_ON_PAGE', 4)
    def test_clans_2_pages(self):
        for i in range(6):
            self.create_clan(self.accounts_factory.create_account(), i)

        self.check_html_ok(self.request_html(url('accounts:clans:')),
                           texts=[('a-%d' % i, 1) for i in range(4)] + [('pgf-no-clans-message', 0)])

        self.check_html_ok(self.request_html(url('accounts:clans:', page=2)),
                           texts=[('a-%d' % i, 1) for i in range(4, 6)] + [('pgf-no-clans-message', 0)])

        self.check_redirect(url('accounts:clans:', page=3), url('accounts:clans:', page=2, order_by=ORDER_BY.NAME.value))


class TestNewRequests(BaseTestRequests):

    def setUp(self):
        super(TestNewRequests, self).setUp()
        self.new_url = url('accounts:clans:new')

    def test_login_required(self):
        self.check_redirect(self.new_url, login_page_url(self.new_url))

    def test_fast_account(self):
        self.request_login(self.account.email)
        self.account.is_fast = True
        self.account.save()
        self.check_html_ok(self.request_html(self.new_url), texts=['common.fast_account'])

    @mock.patch('the_tale.accounts.clans.logic.ClanInfo.can_create_clan', False)
    def test_creation_rights(self):
        self.request_login(self.account.email)
        self.check_html_ok(self.request_html(self.new_url), texts=['clans.can_not_create_clan'])

    def test_banned(self):
        self.request_login(self.account.email)
        self.account.ban_forum(1)
        self.check_html_ok(self.request_html(self.new_url), texts=['common.ban_any'])


    @mock.patch('the_tale.accounts.clans.logic.ClanInfo.can_create_clan', True)
    def test_ok(self):
        self.request_login(self.account.email)
        self.check_html_ok(self.request_html(self.new_url), texts=[('clans.can_not_create_clan', 0)])


class TestCreateRequests(BaseTestRequests):

    def setUp(self):
        super(TestCreateRequests, self).setUp()
        self.create_url = url('accounts:clans:create')
        self.request_login(self.account.email)

    def create_data(self, name=None, abbr=None):
        return {'name': 'clan-1' if name is None else name,
                'abbr': 'CLN-1' if abbr is None else abbr,
                'motto': 'Clan!',
                'description': 'ARGH!'}

    def test_login_required(self):
        self.request_logout()
        self.check_ajax_error(self.post_ajax_json(self.create_url, self.create_data()), 'common.login_required')
        self.assertEqual(ClanPrototype._db_count(), 0)

    def test_fast_account(self):
        self.account.is_fast = True
        self.account.save()
        self.check_ajax_error(self.post_ajax_json(self.create_url, self.create_data()), 'common.fast_account')
        self.assertEqual(ClanPrototype._db_count(), 0)

    @mock.patch('the_tale.accounts.clans.logic.ClanInfo.can_create_clan', False)
    def test_creation_rights(self):
        self.check_ajax_error(self.post_ajax_json(self.create_url, self.create_data()), 'clans.can_not_create_clan')
        self.assertEqual(ClanPrototype._db_count(), 0)

    @mock.patch('the_tale.accounts.clans.logic.ClanInfo.can_create_clan', True)
    def test_form_errors(self):
        self.check_ajax_error(self.post_ajax_json(self.create_url, {}), 'clans.create.form_errors')
        self.assertEqual(ClanPrototype._db_count(), 0)

    @mock.patch('the_tale.accounts.clans.logic.ClanInfo.can_create_clan', True)
    def test_name_exists(self):
        account = self.accounts_factory.create_account()

        clan = self.create_clan(account, 0)
        self.check_ajax_error(self.post_ajax_json(self.create_url, self.create_data(name=clan.name)), 'clans.create.name_exists')
        self.assertEqual(ClanPrototype._db_count(), 1)

    @mock.patch('the_tale.accounts.clans.logic.ClanInfo.can_create_clan', True)
    def test_abbr_exists(self):
        account = self.accounts_factory.create_account()

        clan = self.create_clan(account, 0)
        self.check_ajax_error(self.post_ajax_json(self.create_url, self.create_data(abbr=clan.abbr)), 'clans.create.abbr_exists')
        self.assertEqual(ClanPrototype._db_count(), 1)

    @mock.patch('the_tale.accounts.clans.logic.ClanInfo.can_create_clan', True)
    def test_ok(self):
        self.assertEqual(ClanPrototype._db_count(), 0)
        response = self.post_ajax_json(self.create_url, self.create_data())
        self.assertEqual(ClanPrototype._db_count(), 1)
        self.check_ajax_ok(response, data={'next_url': url('accounts:clans:show', ClanPrototype._db_get_object(0).id)})

    @mock.patch('the_tale.accounts.clans.logic.ClanInfo.can_create_clan', True)
    def test_banned(self):
        self.request_login(self.account.email)
        self.account.ban_forum(1)
        self.check_ajax_error(self.post_ajax_json(self.create_url, self.create_data()), 'common.ban_any')


class TestShowRequests(BaseTestRequests):

    def setUp(self):
        super(TestShowRequests, self).setUp()
        self.clan = self.create_clan(self.account, 0)
        self.show_url = url('accounts:clans:show', self.clan.id)

    def test_ok(self):
        self.check_html_ok(self.request_html(self.show_url), texts=['pgf-no-folclor',
                                                                    self.clan.abbr,
                                                                    self.clan.name,
                                                                    self.clan.motto,
                                                                    self.clan.description_html,
                                                                    (self.clan.description, 0)])

    def test_folclor(self):
        from the_tale.blogs.tests import helpers as blogs_helpers

        blogs_helpers.prepair_forum()

        blogs_helpers.create_post_for_meta_object(self.accounts_factory.create_account(), 'folclor-1-caption', 'folclor-1-text',
                                                  meta_relations.Clan.create_from_object(self.clan), vote_by=self.account)
        blogs_helpers.create_post_for_meta_object(self.accounts_factory.create_account(), 'folclor-2-caption', 'folclor-2-text',
                                                  meta_relations.Clan.create_from_object(self.clan), vote_by=self.account)
        blogs_helpers.create_post_for_meta_object(self.accounts_factory.create_account(), 'folclor-3-caption', 'folclor-3-text',
                                                   meta_relations.Clan.create_from_object(self.clan))

        self.check_html_ok(self.request_html(self.show_url), texts=[('pgf-no-folclor', 0), 'folclor-1-caption', 'folclor-2-caption', ('folclor-3-caption', 0)])


class TestEditRequests(BaseTestRequests):

    def setUp(self):
        super(TestEditRequests, self).setUp()
        self.clan = self.create_clan(self.account, 0)
        self.edit_url = url('accounts:clans:edit', self.clan.id)
        self.request_login(self.account.email)

    def test_login_required(self):
        self.request_logout()
        self.check_redirect(self.edit_url, login_page_url(self.edit_url))

    def test_ownership(self):
        account = self.accounts_factory.create_account()
        clan = self.create_clan(account, 1)

        self.check_html_ok(self.request_html(url('accounts:clans:edit', clan.id)), texts=['clans.not_owner'])

    def test_ok(self):
        self.check_html_ok(self.request_html(self.edit_url), texts=[self.clan.abbr, self.clan.name, self.clan.motto, self.clan.description, (self.clan.description_html, 0)])

    def test_banned(self):
        self.request_login(self.account.email)
        self.account.ban_forum(1)
        self.check_html_ok(self.request_html(self.edit_url), texts=['common.ban_any'])


class TestUpdateRequests(BaseTestRequests):

    def setUp(self):
        super(TestUpdateRequests, self).setUp()
        self.clan = self.create_clan(self.account, 0)
        self.update_url = url('accounts:clans:update', self.clan.id)
        self.request_login(self.account.email)

    def update_data(self, name=None, abbr=None):
        return {'name': 'clan-1' if name is None else name,
                'abbr': 'CLN-1' if abbr is None else abbr,
                'motto': 'Clan!',
                'description': 'ARGH!'}

    def check_clan_old_data(self):
        self.clan.reload()

        self.assertEqual('a-0', self.clan.abbr)
        self.assertEqual('name-0', self.clan.name)
        self.assertEqual('motto-0', self.clan.motto)
        self.assertEqual('[b]description-0[/b]', self.clan.description)

    def check_clan_new_data(self):
        self.clan.reload()

        self.assertEqual('CLN-1', self.clan.abbr)
        self.assertEqual('clan-1', self.clan.name)
        self.assertEqual('Clan!', self.clan.motto)
        self.assertEqual('ARGH!', self.clan.description)

    def test_login_required(self):
        self.request_logout()
        self.check_ajax_error(self.post_ajax_json(self.update_url, self.update_data()), 'common.login_required')
        self.check_clan_old_data()

    def test_ownership(self):
        account = self.accounts_factory.create_account()
        clan = self.create_clan(account, 1)

        self.check_ajax_error(self.post_ajax_json(url('accounts:clans:update', clan.id)), 'clans.not_owner')
        self.check_clan_old_data()


    def test_form_errors(self):
        self.check_ajax_error(self.post_ajax_json(self.update_url, {}), 'clans.update.form_errors')
        self.check_clan_old_data()

    def test_name_exists(self):
        account = self.accounts_factory.create_account()

        clan = self.create_clan(account, 1)
        self.check_ajax_error(self.post_ajax_json(self.update_url, self.update_data(name=clan.name)), 'clans.update.name_exists')

        self.check_clan_old_data()

    def test_abbr_exists(self):
        account = self.accounts_factory.create_account()

        clan = self.create_clan(account, 1)
        self.check_ajax_error(self.post_ajax_json(self.update_url, self.update_data(abbr=clan.abbr)), 'clans.update.abbr_exists')

        self.check_clan_old_data()

    def test_ok(self):
        self.check_ajax_ok(self.post_ajax_json(self.update_url, self.update_data()))
        self.check_clan_new_data()

    def test_banned(self):
        self.request_login(self.account.email)
        self.account.ban_forum(1)
        self.check_ajax_error(self.post_ajax_json(self.update_url, self.update_data()), 'common.ban_any')

    def test_name_and_abbr_not_changed(self):
        self.check_ajax_ok(self.post_ajax_json(self.update_url, self.update_data(abbr=self.clan.abbr, name=self.clan.name)))


class TestRemoveRequests(BaseTestRequests):

    def setUp(self):
        super(TestRemoveRequests, self).setUp()
        self.clan = self.create_clan(self.account, 0)
        self.remove_url = url('accounts:clans:remove', self.clan.id)
        self.request_login(self.account.email)

    def test_login_required(self):
        self.request_logout()
        self.check_ajax_error(self.post_ajax_json(self.remove_url), 'common.login_required')
        self.assertEqual(ClanPrototype._db_count(), 1)

    def test_ownership(self):
        account = self.accounts_factory.create_account()
        clan = self.create_clan(account, 1)

        self.check_ajax_error(self.post_ajax_json(url('accounts:clans:remove', clan.id)), 'clans.not_owner')
        self.assertEqual(ClanPrototype._db_count(), 2)

    def test_not_empty(self):
        self.clan.add_member(self.accounts_factory.create_account())

        self.check_ajax_error(self.post_ajax_json(url('accounts:clans:remove', self.clan.id)), 'clans.remove.not_empty_clan')
        self.assertEqual(ClanPrototype._db_count(), 1)

        self.clan.reload()
        self.assertEqual(self.clan.members_number, 2)


    def test_ok(self):
        self.check_ajax_ok(self.post_ajax_json(self.remove_url, ))
        self.assertEqual(ClanPrototype._db_count(), 0)



class BaseMembershipRequestsTests(BaseTestRequests):

    def setUp(self):
        super(BaseMembershipRequestsTests, self).setUp()


class MembershipForClanRequestsTests(BaseMembershipRequestsTests):

    def setUp(self):
        super(MembershipForClanRequestsTests, self).setUp()
        self.for_clan_url = url('accounts:clans:membership:for-clan')
        self.clan = self.create_clan(self.account, 0)
        self.request_login(self.account.email)

    def test_login_required(self):
        self.request_logout()
        self.check_redirect(self.for_clan_url, login_page_url(self.for_clan_url))

    def test_has_invite_rights(self):
        MembershipPrototype._model_class.objects.all().update(role=MEMBER_ROLE.MEMBER)
        self.check_html_ok(self.request_html(self.for_clan_url), texts=['clans.membership.no_invite_rights'])

    def test_no_requests(self):
        self.check_html_ok(self.request_html(self.for_clan_url), texts=[('clans.membership.no_invite_rights', 0),
                                                                        ('pgf-no-requests-message', 1)])

    def test_success(self):
        account_2 = self.accounts_factory.create_account()
        account_3 = self.accounts_factory.create_account()
        account_4 = self.accounts_factory.create_account()
        account_5 = self.accounts_factory.create_account()
        account_6 = self.accounts_factory.create_account()

        clan_2 = self.create_clan(account_4, 1)

        MembershipRequestPrototype.create(initiator=self.account,
                                          account=account_2,
                                          clan=self.clan,
                                          text='invite-1',
                                          type=MEMBERSHIP_REQUEST_TYPE.FROM_CLAN)

        MembershipRequestPrototype.create(initiator=account_3,
                                          account=account_3,
                                          clan=self.clan,
                                          text='invite-2',
                                          type=MEMBERSHIP_REQUEST_TYPE.FROM_ACCOUNT)

        MembershipRequestPrototype.create(initiator=account_5,
                                          account=account_5,
                                          clan=clan_2,
                                          text='invite-3',
                                          type=MEMBERSHIP_REQUEST_TYPE.FROM_ACCOUNT)

        MembershipRequestPrototype.create(initiator=account_4,
                                          account=account_6,
                                          clan=clan_2,
                                          text='invite-4',
                                          type=MEMBERSHIP_REQUEST_TYPE.FROM_CLAN)


        self.check_html_ok(self.request_html(self.for_clan_url), texts=[('clans.membership.no_invite_rights', 0),
                                                                        ('pgf-no-requests-message', 0),
                                                                        ('invite-1', 0),
                                                                        ('invite-2', 1),
                                                                        ('invite-3', 0),
                                                                        ('invite-4', 0)])


class MembershipForAccountRequestsTests(BaseMembershipRequestsTests):

    def setUp(self):
        super(MembershipForAccountRequestsTests, self).setUp()
        self.for_account_url = url('accounts:clans:membership:for-account')
        self.request_login(self.account.email)

    def test_login_required(self):
        self.request_logout()
        self.check_redirect(self.for_account_url, login_page_url(self.for_account_url))

    def test_no_requests(self):
        self.check_html_ok(self.request_html(self.for_account_url), texts=[('pgf-no-requests-message', 1)])

    # change tests order to fix sqlite segmentation fault
    def test_1_success(self):
        account_2 = self.accounts_factory.create_account()
        account_3 = self.accounts_factory.create_account()
        account_4 = self.accounts_factory.create_account()
        account_5 = self.accounts_factory.create_account()
        account_6 = self.accounts_factory.create_account()

        clan_1 = self.create_clan(account_2, 0)
        clan_2 = self.create_clan(account_4, 1)
        clan_3 = self.create_clan(account_6, 2)

        MembershipRequestPrototype.create(initiator=account_2,
                                          account=self.account,
                                          clan=clan_1,
                                          text='invite-1',
                                          type=MEMBERSHIP_REQUEST_TYPE.FROM_CLAN)

        MembershipRequestPrototype.create(initiator=self.account,
                                          account=self.account,
                                          clan=clan_3,
                                          text='invite-2',
                                          type=MEMBERSHIP_REQUEST_TYPE.FROM_ACCOUNT)

        MembershipRequestPrototype.create(initiator=account_3,
                                          account=account_3,
                                          clan=clan_2,
                                          text='invite-3',
                                          type=MEMBERSHIP_REQUEST_TYPE.FROM_ACCOUNT)

        MembershipRequestPrototype.create(initiator=account_4,
                                          account=account_5,
                                          clan=clan_2,
                                          text='invite-4',
                                          type=MEMBERSHIP_REQUEST_TYPE.FROM_CLAN)


        self.check_html_ok(self.request_html(self.for_account_url), texts=[('pgf-no-requests-message', 0),
                                                                           ('invite-1', 1),
                                                                           ('invite-2', 0),
                                                                           ('invite-3', 0),
                                                                           ('invite-4', 0) ])



class MembershipInviteDialogRequestsTests(BaseMembershipRequestsTests):

    def setUp(self):
        super(MembershipInviteDialogRequestsTests, self).setUp()
        self.clan = self.create_clan(self.account, 0)
        self.account_2 = self.accounts_factory.create_account()
        self.invite_url = url('accounts:clans:membership:invite', account=self.account_2.id)
        self.request_login(self.account.email)


    def test_login_required(self):
        self.request_logout()
        self.check_redirect(self.invite_url, login_page_url(self.invite_url))

    def test_invite_rights(self):
        self.clan.remove()
        self.check_html_ok(self.request_ajax_html(self.invite_url), texts=['clans.membership.no_invite_rights'])

    def test_in_clan(self):
        self.create_clan(self.account_2, 1)
        self.check_html_ok(self.request_ajax_html(self.invite_url), texts=['clans.membership.other_already_in_clan'])

    def test_wrong_account(self):
        self.check_html_ok(self.request_ajax_html(url('accounts:clans:membership:invite', account=666)), texts=['clans.membership.invite.account.not_found'], status_code=404)
        self.check_html_ok(self.request_ajax_html(url('accounts:clans:membership:invite', account='bla-bla')), texts=['clans.membership.invite.account.wrong_format'])

    def test_invite_exist__from_clan(self):
        MembershipRequestPrototype.create(initiator=self.account,
                                          account=self.account_2,
                                          clan=self.clan,
                                          text='invite',
                                          type=MEMBERSHIP_REQUEST_TYPE.FROM_CLAN)
        self.check_html_ok(self.request_ajax_html(self.invite_url), texts=['clans.membership.account_has_invite'])

    def test_invite_exist__from_account(self):
        MembershipRequestPrototype.create(initiator=self.account_2,
                                          account=self.account_2,
                                          clan=self.clan,
                                          text='invite',
                                          type=MEMBERSHIP_REQUEST_TYPE.FROM_ACCOUNT)
        self.check_html_ok(self.request_ajax_html(self.invite_url), texts=['clans.membership.account_has_invite'])

    def test_success(self):
        account_3 = self.accounts_factory.create_account()
        clan_3 = self.create_clan(account_3, 1)
        account_4 = self.accounts_factory.create_account()
        clan_4 = self.create_clan(account_4, 2)

        MembershipRequestPrototype.create(initiator=account_3,
                                          account=self.account_2,
                                          clan=clan_3,
                                          text='invite',
                                          type=MEMBERSHIP_REQUEST_TYPE.FROM_CLAN)
        MembershipRequestPrototype.create(initiator=self.account_2,
                                          account=self.account_2,
                                          clan=clan_4,
                                          text='invite',
                                          type=MEMBERSHIP_REQUEST_TYPE.FROM_ACCOUNT)

        self.check_html_ok(self.request_ajax_html(self.invite_url), texts=['pgf-invite-dialog'])


class MembershipRequestDialogRequestsTests(BaseMembershipRequestsTests):

    def setUp(self):
        super(MembershipRequestDialogRequestsTests, self).setUp()
        self.clan = self.create_clan(self.account, 0)
        self.account_2 = self.accounts_factory.create_account()
        self.request_url = url('accounts:clans:membership:request', clan=self.clan.id)
        self.request_login(self.account_2.email)

    def test_login_required(self):
        self.request_logout()
        self.check_redirect(self.request_url, login_page_url(self.request_url))

    def test_in_clan(self):
        self.create_clan(self.account_2, 1)
        self.check_html_ok(self.request_ajax_html(self.request_url), texts=['clans.membership.already_in_clan'])

    def test_wrong_clan(self):
        self.check_html_ok(self.request_ajax_html(url('accounts:clans:membership:request', clan=666)), texts=['clans.membership.request.clan.not_found'], status_code=404)
        self.check_html_ok(self.request_ajax_html(url('accounts:clans:membership:request', clan='bla-bla')), texts=['clans.membership.request.clan.wrong_format'])

    def test_request_exist__from_clan(self):
        MembershipRequestPrototype.create(initiator=self.account,
                                          account=self.account_2,
                                          clan=self.clan,
                                          text='request',
                                          type=MEMBERSHIP_REQUEST_TYPE.FROM_CLAN)
        self.check_html_ok(self.request_ajax_html(self.request_url), texts=['clans.membership.clan_has_request'])

    def test_request_exist__from_account(self):
        MembershipRequestPrototype.create(initiator=self.account_2,
                                          account=self.account_2,
                                          clan=self.clan,
                                          text='request',
                                          type=MEMBERSHIP_REQUEST_TYPE.FROM_ACCOUNT)
        self.check_html_ok(self.request_ajax_html(self.request_url), texts=['clans.membership.clan_has_request'])

    def test_success(self):
        account_3 = self.accounts_factory.create_account()
        clan_3 = self.create_clan(account_3, 1)
        account_4 = self.accounts_factory.create_account()
        clan_4 = self.create_clan(account_4, 2)

        MembershipRequestPrototype.create(initiator=account_3,
                                          account=self.account,
                                          clan=clan_3,
                                          text='invite',
                                          type=MEMBERSHIP_REQUEST_TYPE.FROM_CLAN)

        MembershipRequestPrototype.create(initiator=self.account,
                                          account=self.account,
                                          clan=clan_4,
                                          text='invite',
                                          type=MEMBERSHIP_REQUEST_TYPE.FROM_ACCOUNT)

        self.check_html_ok(self.request_ajax_html(self.request_url), texts=['pgf-request-dialog'])



class MembershipInviteRequestsTests(BaseMembershipRequestsTests):

    def setUp(self):
        super(MembershipInviteRequestsTests, self).setUp()
        self.clan = self.create_clan(self.account, 0)
        self.account_2 = self.accounts_factory.create_account()
        self.invite_url = url('accounts:clans:membership:invite', account=self.account_2.id)
        self.request_login(self.account.email)

    def post_data(self): return {'text': 'invite-text'}

    def test_login_required(self):
        self.request_logout()
        self.check_ajax_error(self.post_ajax_json(self.invite_url, self.post_data()), 'common.login_required')
        self.assertEqual(MembershipRequestPrototype._db_count(), 0)

    def test_invite_rights(self):
        self.clan.remove()
        self.check_ajax_error(self.post_ajax_json(self.invite_url, self.post_data()), 'clans.membership.no_invite_rights')
        self.assertEqual(MembershipRequestPrototype._db_count(), 0)

    def test_in_clan(self):
        self.create_clan(self.account_2, 1)
        self.check_ajax_error(self.post_ajax_json(self.invite_url, self.post_data()), 'clans.membership.other_already_in_clan')
        self.assertEqual(MembershipRequestPrototype._db_count(), 0)

    def test_wrong_account(self):
        self.check_ajax_error(self.post_ajax_json(url('accounts:clans:membership:invite', account=666), self.post_data()), 'clans.membership.invite.account.not_found')
        self.check_ajax_error(self.post_ajax_json(url('accounts:clans:membership:invite', account='bla-bla'), self.post_data()), 'clans.membership.invite.account.wrong_format')
        self.assertEqual(MembershipRequestPrototype._db_count(), 0)

    def test_invite_exist__from_clan(self):
        MembershipRequestPrototype.create(initiator=self.account,
                                          account=self.account_2,
                                          clan=self.clan,
                                          text='invite',
                                          type=MEMBERSHIP_REQUEST_TYPE.FROM_CLAN)
        self.check_ajax_error(self.post_ajax_json(self.invite_url, self.post_data()), 'clans.membership.account_has_invite')
        self.assertEqual(MembershipRequestPrototype._db_count(), 1)

    def test_invite_exist__from_account(self):
        MembershipRequestPrototype.create(initiator=self.account_2,
                                          account=self.account_2,
                                          clan=self.clan,
                                          text='invite',
                                          type=MEMBERSHIP_REQUEST_TYPE.FROM_ACCOUNT)
        self.check_ajax_error(self.post_ajax_json(self.invite_url, self.post_data()), 'clans.membership.account_has_invite')
        self.assertEqual(MembershipRequestPrototype._db_count(), 1)

    def test_form_errors(self):
        self.check_ajax_error(self.post_ajax_json(self.invite_url, {}), 'clans.membership.invite.form_errors')
        self.assertEqual(MembershipRequestPrototype._db_count(), 0)


    def test_success(self):
        account_3 = self.accounts_factory.create_account()
        clan_3 = self.create_clan(account_3, 1)
        account_4 = self.accounts_factory.create_account()
        clan_4 = self.create_clan(account_4, 2)

        MembershipRequestPrototype.create(initiator=account_3,
                                          account=self.account_2,
                                          clan=clan_3,
                                          text='invite',
                                          type=MEMBERSHIP_REQUEST_TYPE.FROM_CLAN)
        MembershipRequestPrototype.create(initiator=self.account_2,
                                          account=self.account_2,
                                          clan=clan_4,
                                          text='invite',
                                          type=MEMBERSHIP_REQUEST_TYPE.FROM_ACCOUNT)

        self.assertEqual(MessagePrototype._db_count(), 0)

        self.check_ajax_ok(self.post_ajax_json(self.invite_url, self.post_data()))
        self.assertEqual(MembershipRequestPrototype._db_count(), 3)

        invite = MembershipRequestPrototype._db_get_object(2)
        self.assertEqual(invite.text, 'invite-text')
        self.assertTrue(invite.type.is_FROM_CLAN)

        self.assertEqual(MessagePrototype._db_count(), 1)

        message = MessagePrototype._db_get_object(0)
        self.assertEqual(message.sender.id, self.account.id)
        self.assertEqual(message.recipient.id, self.account_2.id)


class MembershipRequestRequestsTests(BaseMembershipRequestsTests):

    def setUp(self):
        super(MembershipRequestRequestsTests, self).setUp()
        self.clan = self.create_clan(self.account, 0)
        self.account_2 = self.accounts_factory.create_account()
        self.request_url = url('accounts:clans:membership:request', clan=self.clan.id)
        self.request_login(self.account_2.email)

    def post_data(self): return {'text': 'request-text'}

    def test_login_required(self):
        self.request_logout()
        self.check_ajax_error(self.post_ajax_json(self.request_url, self.post_data()), 'common.login_required')
        self.assertEqual(MembershipRequestPrototype._db_count(), 0)

    def test_in_clan(self):
        self.create_clan(self.account_2, 1)
        self.check_ajax_error(self.post_ajax_json(self.request_url, self.post_data()), 'clans.membership.already_in_clan')
        self.assertEqual(MembershipRequestPrototype._db_count(), 0)

    def test_wrong_clan(self):
        self.check_ajax_error(self.post_ajax_json(url('accounts:clans:membership:request', clan=666), self.post_data()), 'clans.membership.request.clan.not_found')
        self.check_ajax_error(self.post_ajax_json(url('accounts:clans:membership:request', clan='bla-bla'), self.post_data()), 'clans.membership.request.clan.wrong_format')
        self.assertEqual(MembershipRequestPrototype._db_count(), 0)

    def test_request_exist__from_clan(self):
        MembershipRequestPrototype.create(initiator=self.account,
                                          account=self.account_2,
                                          clan=self.clan,
                                          text='request',
                                          type=MEMBERSHIP_REQUEST_TYPE.FROM_CLAN)
        self.check_ajax_error(self.post_ajax_json(self.request_url, self.post_data()), 'clans.membership.clan_has_request')
        self.assertEqual(MembershipRequestPrototype._db_count(), 1)

    def test_request_exist__from_account(self):
        MembershipRequestPrototype.create(initiator=self.account_2,
                                          account=self.account_2,
                                          clan=self.clan,
                                          text='request',
                                          type=MEMBERSHIP_REQUEST_TYPE.FROM_ACCOUNT)
        self.check_ajax_error(self.post_ajax_json(self.request_url, self.post_data()), 'clans.membership.clan_has_request')
        self.assertEqual(MembershipRequestPrototype._db_count(), 1)

    def test_form_errors(self):
        self.check_ajax_error(self.post_ajax_json(self.request_url, {}), 'clans.membership.request.form_errors')
        self.assertEqual(MembershipRequestPrototype._db_count(), 0)

    def test_success(self):
        account_3 = self.accounts_factory.create_account()
        clan_3 = self.create_clan(account_3, 1)
        account_4 = self.accounts_factory.create_account()
        clan_4 = self.create_clan(account_4, 2)

        MembershipRequestPrototype.create(initiator=account_3,
                                          account=self.account,
                                          clan=clan_3,
                                          text='request',
                                          type=MEMBERSHIP_REQUEST_TYPE.FROM_CLAN)

        MembershipRequestPrototype.create(initiator=self.account,
                                          account=self.account,
                                          clan=clan_4,
                                          text='request',
                                          type=MEMBERSHIP_REQUEST_TYPE.FROM_ACCOUNT)

        self.assertEqual(MessagePrototype._db_count(), 0)

        self.check_ajax_ok(self.post_ajax_json(self.request_url, self.post_data()))
        self.assertEqual(MembershipRequestPrototype._db_count(), 3)
        request = MembershipRequestPrototype._db_get_object(2)
        self.assertEqual(request.text, 'request-text')
        self.assertTrue(request.type.is_FROM_ACCOUNT)

        self.assertEqual(MessagePrototype._db_count(), 1)

        message = MessagePrototype._db_get_object(0)
        self.assertEqual(message.recipient.id, self.account.id)
        self.assertEqual(message.sender.id, self.account_2.id)


class MembershipAcceptRequestRequestsTests(BaseMembershipRequestsTests):

    def setUp(self):
        super(MembershipAcceptRequestRequestsTests, self).setUp()
        self.clan = self.create_clan(self.account, 0)
        self.account_2 = self.accounts_factory.create_account()
        self.request = MembershipRequestPrototype.create(initiator=self.account_2,
                                                         account=self.account_2,
                                                         clan=self.clan,
                                                         text='request',
                                                         type=MEMBERSHIP_REQUEST_TYPE.FROM_ACCOUNT)

        self.accept_url = url('accounts:clans:membership:accept-request', request=self.request.id)
        self.request_login(self.account.email)

    def test_login_required(self):
        self.request_logout()
        self.check_ajax_error(self.post_ajax_json(self.accept_url), 'common.login_required')
        self.assertEqual(MembershipRequestPrototype._db_count(), 1)
        self.assertEqual(MembershipPrototype._db_count(), 1)

    def test_no_invite_rights(self):
        MembershipPrototype._model_class.objects.all().update(role=MEMBER_ROLE.MEMBER)
        self.check_ajax_error(self.post_ajax_json(self.accept_url), 'clans.membership.no_invite_rights')
        self.assertEqual(MembershipRequestPrototype._db_count(), 1)
        self.assertEqual(MembershipPrototype._db_count(), 1)

    def test_wrong_request_type(self):
        MembershipRequestPrototype._model_class.objects.all().update(type=MEMBERSHIP_REQUEST_TYPE.FROM_CLAN)
        self.check_ajax_error(self.post_ajax_json(self.accept_url), 'clans.membership.request_not_from_account')
        self.assertEqual(MembershipRequestPrototype._db_count(), 1)
        self.assertEqual(MembershipPrototype._db_count(), 1)

    def test_wrong_request_id(self):
        self.check_ajax_error(self.post_ajax_json(url('accounts:clans:membership:accept-request', request=666)), 'clan.membership.accept_request.request.not_found')
        self.check_ajax_error(self.post_ajax_json(url('accounts:clans:membership:accept-request', request='bla-bla')), 'clan.membership.accept_request.request.wrong_format')
        self.assertEqual(MembershipRequestPrototype._db_count(), 1)
        self.assertEqual(MembershipPrototype._db_count(), 1)

    def test_success(self):
        self.assertEqual(MessagePrototype._db_count(), 0)

        self.check_ajax_ok(self.post_ajax_json(self.accept_url))
        self.assertEqual(MembershipRequestPrototype._db_count(), 0)
        self.assertEqual(MembershipPrototype._db_count(), 2)
        self.assertTrue(MembershipPrototype._db_get_object(1).role.is_MEMBER)

        self.assertEqual(MessagePrototype._db_count(), 1)

        message = MessagePrototype._db_get_object(0)
        self.assertEqual(message.sender.id, self.account.id)
        self.assertEqual(message.recipient.id, self.account_2.id)


class MembershipAcceptInviteRequestsTests(BaseMembershipRequestsTests):

    def setUp(self):
        super(MembershipAcceptInviteRequestsTests, self).setUp()
        self.clan = self.create_clan(self.account, 0)
        self.account_2 = self.accounts_factory.create_account()
        self.request = MembershipRequestPrototype.create(initiator=self.account,
                                                         account=self.account_2,
                                                         clan=self.clan,
                                                         text='request',
                                                         type=MEMBERSHIP_REQUEST_TYPE.FROM_CLAN)

        self.accept_url = url('accounts:clans:membership:accept-invite', request=self.request.id)
        self.request_login(self.account_2.email)

    def test_login_required(self):
        self.request_logout()
        self.check_ajax_error(self.post_ajax_json(self.accept_url), 'common.login_required')
        self.assertEqual(MembershipRequestPrototype._db_count(), 1)
        self.assertEqual(MembershipPrototype._db_count(), 1)

    def test_not_in_clan(self):
        self.create_clan(self.account_2, 1)
        self.check_ajax_error(self.post_ajax_json(self.accept_url), 'clans.membership.already_in_clan')
        self.assertEqual(MembershipRequestPrototype._db_count(), 1)
        self.assertEqual(MembershipPrototype._db_count(), 2)

    def test_wrong_request_type(self):
        MembershipRequestPrototype._model_class.objects.all().update(type=MEMBERSHIP_REQUEST_TYPE.FROM_ACCOUNT)
        self.check_ajax_error(self.post_ajax_json(self.accept_url), 'clans.membership.request_not_from_clan')
        self.assertEqual(MembershipRequestPrototype._db_count(), 1)
        self.assertEqual(MembershipPrototype._db_count(), 1)

    def test_wrong_request_id(self):
        self.check_ajax_error(self.post_ajax_json(url('accounts:clans:membership:accept-invite', request=666)), 'clan.membership.accept_invite.request.not_found')
        self.check_ajax_error(self.post_ajax_json(url('accounts:clans:membership:accept-invite', request='bla-bla')), 'clan.membership.accept_invite.request.wrong_format')
        self.assertEqual(MembershipRequestPrototype._db_count(), 1)
        self.assertEqual(MembershipPrototype._db_count(), 1)

    def test_success(self):
        self.check_ajax_ok(self.post_ajax_json(self.accept_url))
        self.assertEqual(MembershipRequestPrototype._db_count(), 0)
        self.assertEqual(MembershipPrototype._db_count(), 2)
        self.assertTrue(MembershipPrototype._db_get_object(1).role.is_MEMBER)


class MembershipRejectRequestRequestsTests(BaseMembershipRequestsTests):

    def setUp(self):
        super(MembershipRejectRequestRequestsTests, self).setUp()
        self.clan = self.create_clan(self.account, 0)
        self.account_2 = self.accounts_factory.create_account()
        self.request = MembershipRequestPrototype.create(initiator=self.account_2,
                                                         account=self.account_2,
                                                         clan=self.clan,
                                                         text='request',
                                                         type=MEMBERSHIP_REQUEST_TYPE.FROM_ACCOUNT)

        self.reject_url = url('accounts:clans:membership:reject-request', request=self.request.id)
        self.request_login(self.account.email)

    def test_login_required(self):
        self.request_logout()
        self.check_ajax_error(self.post_ajax_json(self.reject_url), 'common.login_required')
        self.assertEqual(MembershipRequestPrototype._db_count(), 1)
        self.assertEqual(MembershipPrototype._db_count(), 1)

    def test_no_invite_rights(self):
        MembershipPrototype._model_class.objects.all().update(role=MEMBER_ROLE.MEMBER)
        self.check_ajax_error(self.post_ajax_json(self.reject_url), 'clans.membership.no_invite_rights')
        self.assertEqual(MembershipRequestPrototype._db_count(), 1)
        self.assertEqual(MembershipPrototype._db_count(), 1)

    def test_wrong_request_type(self):
        MembershipRequestPrototype._model_class.objects.all().update(type=MEMBERSHIP_REQUEST_TYPE.FROM_CLAN)
        self.check_ajax_error(self.post_ajax_json(self.reject_url), 'clans.membership.request_not_from_account')
        self.assertEqual(MembershipRequestPrototype._db_count(), 1)
        self.assertEqual(MembershipPrototype._db_count(), 1)

    def test_wrong_request_id(self):
        self.check_ajax_error(self.post_ajax_json(url('accounts:clans:membership:reject-request', request=666)), 'clan.membership.reject_request.request.not_found')
        self.check_ajax_error(self.post_ajax_json(url('accounts:clans:membership:reject-request', request='bla-bla')), 'clan.membership.reject_request.request.wrong_format')
        self.assertEqual(MembershipRequestPrototype._db_count(), 1)
        self.assertEqual(MembershipPrototype._db_count(), 1)

    def test_success(self):
        self.assertEqual(MessagePrototype._db_count(), 0)

        self.check_ajax_ok(self.post_ajax_json(self.reject_url))
        self.assertEqual(MembershipRequestPrototype._db_count(), 0)
        self.assertEqual(MembershipPrototype._db_count(), 1)

        self.assertEqual(MessagePrototype._db_count(), 1)

        message = MessagePrototype._db_get_object(0)
        self.assertEqual(message.sender.id, self.account.id)
        self.assertEqual(message.recipient.id, self.account_2.id)


class MembershipRejectInviteRequestsTests(BaseMembershipRequestsTests):

    def setUp(self):
        super(MembershipRejectInviteRequestsTests, self).setUp()
        self.clan = self.create_clan(self.account, 0)
        self.account_2 = self.accounts_factory.create_account()
        self.request = MembershipRequestPrototype.create(initiator=self.account,
                                                         account=self.account_2,
                                                         clan=self.clan,
                                                         text='request',
                                                         type=MEMBERSHIP_REQUEST_TYPE.FROM_CLAN)

        self.reject_url = url('accounts:clans:membership:reject-invite', request=self.request.id)
        self.request_login(self.account_2.email)

    def test_login_required(self):
        self.request_logout()
        self.check_ajax_error(self.post_ajax_json(self.reject_url), 'common.login_required')
        self.assertEqual(MembershipRequestPrototype._db_count(), 1)
        self.assertEqual(MembershipPrototype._db_count(), 1)

    def test_not_in_clan(self):
        self.create_clan(self.account_2, 1)
        self.check_ajax_error(self.post_ajax_json(self.reject_url), 'clans.membership.already_in_clan')
        self.assertEqual(MembershipRequestPrototype._db_count(), 1)
        self.assertEqual(MembershipPrototype._db_count(), 2)

    def test_wrong_request_type(self):
        MembershipRequestPrototype._model_class.objects.all().update(type=MEMBERSHIP_REQUEST_TYPE.FROM_ACCOUNT)
        self.check_ajax_error(self.post_ajax_json(self.reject_url), 'clans.membership.request_not_from_clan')
        self.assertEqual(MembershipRequestPrototype._db_count(), 1)
        self.assertEqual(MembershipPrototype._db_count(), 1)

    def test_wrong_request_id(self):
        self.check_ajax_error(self.post_ajax_json(url('accounts:clans:membership:reject-invite', request=666)), 'clan.membership.reject_invite.request.not_found')
        self.check_ajax_error(self.post_ajax_json(url('accounts:clans:membership:reject-invite', request='bla-bla')), 'clan.membership.reject_invite.request.wrong_format')
        self.assertEqual(MembershipRequestPrototype._db_count(), 1)
        self.assertEqual(MembershipPrototype._db_count(), 1)

    def test_success(self):
        self.check_ajax_ok(self.post_ajax_json(self.reject_url))
        self.assertEqual(MembershipRequestPrototype._db_count(), 0)
        self.assertEqual(MembershipPrototype._db_count(), 1)


class MembershipRemoveFromClanRequestsTests(BaseMembershipRequestsTests):

    def setUp(self):
        super(MembershipRemoveFromClanRequestsTests, self).setUp()
        self.clan = self.create_clan(self.account, 0)
        self.account_2 = self.accounts_factory.create_account()
        self.clan.add_member(self.account_2)

        self.remove_url = url('accounts:clans:membership:remove-from-clan', account=self.account_2.id)
        self.request_login(self.account.email)


    def test_login_required(self):
        self.request_logout()
        self.check_ajax_error(self.post_ajax_json(self.remove_url), 'common.login_required')
        self.assertEqual(MembershipPrototype._db_count(), 2)

    def test_wrong_account_id(self):
        self.check_ajax_error(self.post_ajax_json(url('accounts:clans:membership:remove-from-clan', account=666)), 'clan.membership.remove_from_clan.account.not_found')
        self.check_ajax_error(self.post_ajax_json(url('accounts:clans:membership:remove-from-clan', account='bla-bla')), 'clan.membership.remove_from_clan.account.wrong_format')
        self.assertEqual(MembershipPrototype._db_count(), 2)

    def test_no_remove_righs(self):
        self.request_logout()
        self.request_login(self.account_2.email)
        self.check_ajax_error(self.post_ajax_json(url('accounts:clans:membership:remove-from-clan', account=self.account.id)),
                              'clans.membership.no_remove_rights')
        self.assertEqual(MembershipPrototype._db_count(), 2)

    def test_wrong_clan(self):
        self.clan.remove_member(self.account_2)
        self.check_ajax_error(self.post_ajax_json(self.remove_url), 'clans.membership.remove_from_clan.not_in_clan')
        self.create_clan(self.account_2, 1)
        self.check_ajax_error(self.post_ajax_json(self.remove_url), 'clans.membership.remove_from_clan.not_in_clan')
        self.assertEqual(MembershipPrototype._db_count(), 2)

    @mock.patch('the_tale.accounts.clans.relations.MEMBER_ROLE.MEMBER.priority', MEMBER_ROLE.LEADER.priority)
    def test_wrong_priority(self):
        self.check_ajax_error(self.post_ajax_json(self.remove_url), 'clans.membership.remove_from_clan.wrong_role_priority')
        self.assertEqual(MembershipPrototype._db_count(), 2)

    def test_success(self):
        self.assertEqual(MessagePrototype._db_count(), 0)

        self.check_ajax_ok(self.post_ajax_json(self.remove_url))
        self.assertEqual(MembershipPrototype._db_count(), 1)
        membership = MembershipPrototype._db_get_object(0)
        self.assertEqual(membership.account_id, self.account.id)

        self.clan.reload()
        self.assertEqual(self.clan.members_number, 1)

        self.assertEqual(MessagePrototype._db_count(), 1)

        message = MessagePrototype._db_get_object(0)
        self.assertEqual(message.sender.id, self.account.id)
        self.assertEqual(message.recipient.id, self.account_2.id)



class MembershipLeaveClanRequestsTests(BaseMembershipRequestsTests):

    def setUp(self):
        super(MembershipLeaveClanRequestsTests, self).setUp()
        self.clan = self.create_clan(self.account, 0)
        self.account_2 = self.accounts_factory.create_account()
        self.clan.add_member(self.account_2)

        self.leave_url = url('accounts:clans:membership:leave-clan')
        self.request_login(self.account_2.email)


    def test_login_required(self):
        self.request_logout()
        self.check_ajax_error(self.post_ajax_json(self.leave_url), 'common.login_required')
        self.assertEqual(MembershipPrototype._db_count(), 2)

    def test_not_in_clan(self):
        self.clan.remove_member(self.account_2)
        self.check_ajax_error(self.post_ajax_json(self.leave_url), 'clans.membership.not_in_clan')
        self.assertEqual(MembershipPrototype._db_count(), 1)

    def test_leader(self):
        self.request_logout()
        self.request_login(self.account.email)
        self.check_ajax_error(self.post_ajax_json(url('accounts:clans:membership:leave-clan')), 'clans.membership.leave_clan.leader')
        self.assertEqual(MembershipPrototype._db_count(), 2)

    def test_success(self):
        self.check_ajax_ok(self.post_ajax_json(self.leave_url))
        self.assertEqual(MembershipPrototype._db_count(), 1)
        membership = MembershipPrototype._db_get_object(0)
        self.assertEqual(membership.account_id, self.account.id)

        self.clan.reload()
        self.assertEqual(self.clan.members_number, 1)
