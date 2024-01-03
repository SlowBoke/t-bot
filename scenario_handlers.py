# -*- coding: utf-8 -*-

import asyncio
import peewee
import time

import telegram

import db
from settings import SCENARIOS
from sheet_record import sheet_append

from random import random

from telegram import (Update, InlineQueryResultArticle, InputTextMessageContent,
                      InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (filters, MessageHandler, ApplicationBuilder, ContextTypes,
                          CommandHandler, InlineQueryHandler, CallbackQueryHandler)


async def admin_receiver(user, message, user_in_db, dispatch_dict, **kwargs):
    text_new_task = 'Новое обращение от пользователя {user_link}:'.format(user_link=user.link)

    if 'admin_id' in user_in_db.context:
        dispatch_dict['receiver_id'] = user_in_db.context['admin_id']
        dispatch_dict['message_list'] = []
    else:
        try:
            admin = await connect_to_admin(user, message, user_in_db, dispatch_dict, text_new_task)
            await user.send_message(text=f'Запрос принят и рассматривается. '
                                         f'С вами будет общаться наш модератор {admin.admin_name}.')
        except peewee.DoesNotExist:
            await user.send_message(text='В данный момент все модераторы заняты. Пожалуйста, подождите.')
            while True:
                await asyncio.sleep(10)
                try:
                    admin = await connect_to_admin(user, message, user_in_db, dispatch_dict, text_new_task)
                    await user.send_message(text=f'Запрос принят и рассматривается. '
                                                 f'С вами будет общаться наш модератор {admin.admin_name}.')
                    break
                except peewee.DoesNotExist:
                    pass
        dispatch_dict['receiver_id'] = admin.user_id

    dispatch_dict['message_list'].append(message.id)
    dispatch_dict['same_step'] = True


async def connect_to_admin(user, message, user_in_db, dispatch_dict, text_new_task):
    admin = db.UserConversation.select().where(
        db.UserConversation.scenario_name == 'Администратор' and
        db.UserConversation.step_name == 'step1'
    ).get()

    admin_db = db.AdminLogin.select().where(db.AdminLogin.user_id == admin.user_id).get()

    # TODO: разобраться с числом админов
    # admin = admins_ready.get()  # _list.sort(key=lambda args: random())[0]
    admin.step_name = SCENARIOS[admin.scenario_name]['steps'][admin.step_name]['next_step']
    admin.context['customer_id'] = message.chat_id
    admin.context['customer_link'] = user.link
    admin.save()

    dispatch_dict['message_list'] = user_in_db.context['messages']
    dispatch_dict['text_list'] = [text_new_task]

    user_in_db.context['admin_id'] = admin.user_id
    user_in_db.context['messages'] = []
    user_in_db.save()

    return admin_db


async def customer_receiver(user, message, user_in_db, dispatch_dict, **kwargs):
    customer_id = user_in_db.context['customer_id']
    admin_name = db.AdminLogin.select().where(db.AdminLogin.user_id == message.chat_id).get().admin_name

    if message.text:
        text_with_admin_name = f'{admin_name}:\n{message.text}'
        dispatch_dict['text_list'] = [text_with_admin_name]
    if message.effective_attachment:
        attachments = message.effective_attachment
        dispatch_dict['attachment_list'] = [attachments]

    dispatch_dict['receiver_id'] = customer_id
    dispatch_dict['same_step'] = True


async def login_handler(message, user_in_db, dispatch_dict, steps, step, **kwargs):
    try:
        db.AdminLogin.select().where(db.AdminLogin.login == message.text).get()
        dispatch_dict['text_list'] = [steps[step['next_step']]['message']]
        user_in_db.context['login'] = message.text
        user_in_db.save()
    except peewee.DoesNotExist:
        dispatch_dict['text_list'] = [step['message_failure']]
        dispatch_dict['text_list'].append(step['message'])
        dispatch_dict['same_step'] = True

    dispatch_dict['receiver_id'] = user_in_db.user_id


async def password_handler(message, user_in_db, dispatch_dict, step, **kwargs):
    admin = db.AdminLogin.select().where(db.AdminLogin.login == user_in_db.context['login']).get()
    admin_name = admin.admin_name
    new_scenario = 'Администратор'
    dispatch_dict['delete_message'] = True

    if message.text != admin.password:
        dispatch_dict['text_list'] = [step['message_failure']]
        dispatch_dict['text_list'].append(step['message'])
        dispatch_dict['receiver_id'] = user_in_db.user_id
        dispatch_dict['same_step'] = True
    else:
        dispatch_dict['text_list'] = [step['message_final'].format(admin_name=admin_name)]
        dispatch_dict['receiver_id'] = user_in_db.user_id
        dispatch_dict['same_step'] = True
        dispatch_dict['menu_change'] = True
        dispatch_dict['login'] = admin.login

        admin.user_id = user_in_db.user_id
        admin.save()

        user_in_db.scenario_name = new_scenario
        user_in_db.step_name = SCENARIOS[new_scenario]['first_step']
        user_in_db.context = {'messages': []}
        user_in_db.save()


async def rating_handler(message, user_in_db, dispatch_dict, steps, step, **kwargs):
    if message.text == '1':
        pass
        dispatch_dict['text_list'] = [step['message1']]
    else:
        pass
        dispatch_dict['text_list'] = [step['message0']]

    dispatch_dict['receiver_id'] = user_in_db.user_id
