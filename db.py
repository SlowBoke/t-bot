# -*- coding: utf-8 -*-

import peewee

database_proxy = peewee.Proxy()


class BaseModel(peewee.Model):

    class Meta:
        database = database_proxy


class UserConversation(BaseModel):
    """User's state inside a scenario."""
    user_id = peewee.IntegerField(unique=True)
    scenario_name = peewee.CharField()
    step_name = peewee.CharField()


class AdminLogin(BaseModel):
    user_id = peewee.IntegerField(unique=True)
    login = peewee.CharField()
    password = peewee.CharField()
    is_active = peewee.BooleanField()


class GroupViolation(BaseModel):
    user_id = peewee.IntegerField(unique=True)
    violation_quantity = peewee.IntegerField()
