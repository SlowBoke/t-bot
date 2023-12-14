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


def private_messages_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_text = update.effective_message.text

    if db.UserConversation.select().where(db.UserConversation.user_id == user.id):
        user_in_db = db.UserConversation.select().where(db.UserConversation.user_id == user.id).get()

        if user_in_db.scenario_name != 'NULL':
            return continue_scenario(user_text=user_text, user_in_db=user_in_db, user=user)
        else:
            user_in_db.context['messages'].append(update.effective_message.text)
            user_in_db.save()

    else:
        new_user = db.UserConversation.create(
            user_id=user.id,
            scenario_name='NULL',
            step_name='NULL',
            context={'messages': [update.effective_message.text]}
        )


def start_scenario(user, scenario_name, **kwargs):
    first_step_name = SCENARIOS[scenario_name]['first_step']
    steps = SCENARIOS[scenario_name]['steps']
    step = steps[first_step_name]
    dispatch_dict = {'receiver_id': user.id}

    if db.UserConversation.select().where(db.UserConversation.user_id == user.id):
        user_in_db = db.UserConversation.select().where(db.UserConversation.user_id == user.id).get()
        user_in_db.scenario_name = scenario_name
        user_in_db.step_name = step
        user_in_db.save()
    else:
        user_in_db = db.UserConversation.create(
            user_id=user.id,
            scenario_name=scenario_name,
            step_name=step,
            context={'messages': []}
        )

    if 'message' in step:
        dispatch_dict['text_list'] = [step['message']]

    user_in_db.step_name = step['next_step']
    user_in_db.save()

    return dispatch_dict


def continue_scenario(user_text, user_in_db, user):
    scenario_name = user_in_db.scenario_name
    steps = SCENARIOS[scenario_name]['steps']
    step = steps[user_in_db.step_name]
    dispatch_dict = {}

    if 'handler' in step:
        handler = getattr(scenario_handlers, step['handler'])
        handler(
            user=user,
            user_text=user_text,
            user_in_db=user_in_db,
            dispatch_dict=dispatch_dict,
            steps=steps,
            step=step
        )
    else:
        general_step_handler(user_id=user.id, dispatch_dict=dispatch_dict, step=step, scenario_name=scenario_name)

    if 'same_step' not in dispatch_dict:
        if 'next_step' in step:
            user_in_db.step_name = step['next_step']
        else:
            user_in_db.step_name = None
            user_in_db.scenario_name = None
            user_in_db.context = {'messages': []}

        user_in_db.save()

    return dispatch_dict


def general_step_handler(user_id, dispatch_dict, step, scenario_name):
    if scenario_name in ['Задать вопрос', 'Авторизация']:
        if 'message' in step:
            dispatch_dict['text_list'] = step['message']
            dispatch_dict['receiver_id'] = user_id
    elif scenario_name == 'Администратор':
        pass
    else:
        dispatch_dict['start'] = True




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

