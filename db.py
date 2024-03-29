# -*- coding: utf-8 -*-

import peewee
from playhouse.sqlite_ext import JSONField

database_proxy = peewee.Proxy()


class BaseModel(peewee.Model):

    class Meta:
        database = database_proxy


class UserConversation(BaseModel):
    """User's state inside a scenario."""
    user_id = peewee.IntegerField(unique=True)
    scenario_name = peewee.CharField()
    step_name = peewee.CharField()
    context = JSONField()


class AdminLogin(BaseModel):
    """Admins' info."""
    admin_name = peewee.CharField()
    login = peewee.CharField()
    password = peewee.CharField()
    user_id = peewee.IntegerField()


class GroupViolation(BaseModel):
    """Quantity of violations per user."""
    user_id = peewee.IntegerField(unique=True)
    violation_quantity = peewee.IntegerField()


class SheetInfo(BaseModel):
    """Current number of Google Sheets' row."""
    cur_row = peewee.IntegerField()
