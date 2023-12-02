# -*- coding: utf-8 -*-

import peewee

import db
from settings import SCENARIOS

from random import random

from telegram import (Update, InlineQueryResultArticle, InputTextMessageContent,
                      InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (filters, MessageHandler, ApplicationBuilder, ContextTypes,
                          CommandHandler, InlineQueryHandler, CallbackQueryHandler)


async def admin_receiver(user_text, user_in_db, dispatch_dict):
    if user_in_db.context['admin_id']:
        admin_id = user_in_db.context['admin_id']
        dispatch_dict['messages'] = []
    else:
        admins_ready_list = db.UserConversation.select().where(
            db.UserConversation.scenario_name == 'Администратор' and
            db.UserConversation.step_name is None
        )
        admin = admins_ready_list.sort(key=lambda args: random)[0]
        admin_id = admin.user_id
        admin.step_name = SCENARIOS[admin.scenario_name]['first_step']
        admin.save()

        user_in_db.context['admin_id'] = admin_id
        dispatch_dict['text_list'] = user_in_db.context['messages']
        user_in_db.context['messages'] = []
        user_in_db.save()

    dispatch_dict['messages'].append(user_text)
    dispatch_dict['receiver_id'] = admin_id




