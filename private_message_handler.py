# -*- coding: utf-8 -*-

import peewee

import db
import scenario_handlers
from settings import SCENARIOS

from random import random

from telegram import (Update, InlineQueryResultArticle, InputTextMessageContent,
                      InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (filters, MessageHandler, ApplicationBuilder, ContextTypes,
                          CommandHandler, InlineQueryHandler, CallbackQueryHandler)


async def private_messages_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.effective_message.text

    if db.UserConversation.select().where(db.UserConversation.user_id == user_id):
        user_in_db = db.UserConversation.select().where(db.UserConversation.user_id == user_id).get()

        if user_in_db.scenario_name:
            return scenario_handler(user_text=user_text, user_in_db=user_in_db)
        else:
            user_in_db.context['messages'].append(update.effective_message.text)
            user_in_db.save()

    else:
        new_user = db.UserConversation.create(
            user_id=user_id,
            scenario_name=None,
            step_name=None,
            context={'messages': [update.effective_message.text]}
        )
    return None


async def scenario_handler(user_text, user_in_db):
    scenario_name = user_in_db.scenario_name
    steps = SCENARIOS[scenario_name]['steps']
    step = steps[user_in_db.step_name]
    dispatch_dict = {}

    handler = getattr(scenario_handlers, step['handler'])
    handler(user_text=user_text, user_in_db=user_in_db, dispatch_dict=dispatch_dict)

    if dispatch_dict['next_step']:
        if step['next_step']:
            user_in_db.step_name = step['next_step']
        else:
            user_in_db.step_name = None
            user_in_db.scenario_name = None

        user_in_db.save()

    return dispatch_dict




    # admin_active_list = db.AdminLogin.select().where(db.AdminLogin.is_active is True)

    # if user_id in (x.user_id for x in admin_active_list):
    #     await message_from_admin(update=update, context=context)
    # else:
    #     await message_from_user(
    #         update=update,
    #         context=context,
    #         user_id=user_id,
    #         admin_active_list=admin_active_list
    #     )


# async def message_from_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     pass


# async def message_from_user(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, admin_active_list):
#
#     if db.UserConversation.select().where(db.UserConversation.user_id == user_id)[0].title:
#         user_in_db = db.UserConversation.select().where(db.UserConversation.user_id == user_id)[0].title
#
#         if user_in_db.scenario == 'Задать вопрос':
#             await conversation_handler(
#                 update=update,
#                 context=context,
#                 user_in_db=user_in_db,
#                 admin_active_list=admin_active_list
#             )
#         elif user_in_db.scenario == 'Авторизоваться':
#             pass
#         else:
#             user_in_db.context['messages'].append(update.effective_message.text)
#             user_in_db.save()
#
#     else:
#         new_user = db.UserConversation.create(
#             user_id=user_id,
#             scenario_name=None,
#             step_name=None,
#             context={'messages': [update.effective_message.text]}
#         )

