# -*- coding: utf-8 -*-

import peewee

import db
from settings import SCENARIOS

from random import random

from telegram import (Update, InlineQueryResultArticle, InputTextMessageContent,
                      InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (filters, MessageHandler, ApplicationBuilder, ContextTypes,
                          CommandHandler, InlineQueryHandler, CallbackQueryHandler)


def admin_receiver(user, user_text, user_in_db, dispatch_dict, **kwargs):
    text_new_task = 'Новое обращение от пользователя {user_link}:'.format(user_link=user.link)

    if 'admin_id' in user_in_db.context:
        admin_id = user_in_db.context['admin_id']
        dispatch_dict['text_list'] = []
    else:
        admins_ready = db.UserConversation.select().where(
            db.UserConversation.scenario_name == 'Администратор' and
            db.UserConversation.step_name == 'step1'
        )

        # TODO: разобраться с числом админов
        admin = admins_ready.get()  # _list.sort(key=lambda args: random())[0]
        admin_id = admin.user_id
        admin.step_name = SCENARIOS[admin.scenario_name]['steps'][admin.step_name]['next_step']
        admin.context['customer_id'] = user.id
        admin.save()

        dispatch_dict['text_list'] = user_in_db.context['messages']
        dispatch_dict['text_list'].insert(0, text_new_task)

        user_in_db.context['admin_id'] = admin_id
        user_in_db.context['messages'] = []
        user_in_db.save()

    dispatch_dict['text_list'].append(user_text)
    dispatch_dict['receiver_id'] = admin_id
    dispatch_dict['same_step'] = True


def customer_receiver(user, user_text, user_in_db, dispatch_dict, **kwargs):
    customer_id = user_in_db.context['customer_id']
    admin_name = db.AdminLogin.select().where(db.AdminLogin.user_id == user.id).get().admin_name
    text_with_admin_name = f'{admin_name}:\n\n{user_text}'

    dispatch_dict['receiver_id'] = customer_id
    dispatch_dict['text_list'] = [text_with_admin_name]
    dispatch_dict['same_step'] = True




def login_handler(user_text, user_in_db, dispatch_dict, steps, step, **kwargs):
    admins = db.AdminLogin.select()

    for admin in admins:
        if user_text == admin.login:
            dispatch_dict['text_list'] = [steps[step['next_step']]['message']]
            user_in_db.context['login'] = user_text
            user_in_db.save()
            break
    else:
        dispatch_dict['text_list'] = [step['message_failure']]
        dispatch_dict['text_list'].append(step['message'])
        dispatch_dict['same_step'] = True

    dispatch_dict['receiver_id'] = user_in_db.user_id


def password_handler(user_text, user_in_db, dispatch_dict, step, **kwargs):
    admin = db.AdminLogin.select().where(db.AdminLogin.login == user_in_db.context['login']).get()
    admin_name = admin.admin_name
    new_scenario = 'Администратор'

    if user_text != admin.password:
        dispatch_dict['text_list'] = [step['message_failure']]
        dispatch_dict['text_list'].append(step['message'])
        dispatch_dict['receiver_id'] = user_in_db.user_id
        dispatch_dict['same_step'] = True
    else:
        dispatch_dict['text_list'] = [step['message_final'].format(admin_name=admin_name)]
        dispatch_dict['receiver_id'] = user_in_db.user_id
        dispatch_dict['same_step'] = True

        admin.user_id = user_in_db.user_id
        admin.save()

        user_in_db.scenario_name = new_scenario
        user_in_db.step_name = SCENARIOS[new_scenario]['first_step']
        user_in_db.context = {'messages': []}
        user_in_db.save()
