# coding: utf-8

from dext.forms import forms, fields

from the_tale.common.utils import bbcode

from the_tale.accounts.clans.models import Clan, MembershipRequest

class ClanForm(forms.Form):

    name = fields.CharField(label='Название', max_length=Clan.MAX_NAME_LENGTH, min_length=Clan.MIN_NAME_LENGTH)
    abbr = fields.CharField(label='Аббревиатура (до %d символов)' % Clan.MAX_ABBR_LENGTH, max_length=Clan.MAX_ABBR_LENGTH, min_length=Clan.MIN_ABBR_LENGTH)
    motto = fields.CharField(label='Девиз', max_length=Clan.MAX_MOTTO_LENGTH)
    description = bbcode.BBField(label='Описание', max_length=Clan.MAX_DESCRIPTION_LENGTH)


class MembershipRequestForm(forms.Form):
    text = bbcode.BBField(label='Текст', max_length=MembershipRequest.MAX_TEXT_LENGTH)
