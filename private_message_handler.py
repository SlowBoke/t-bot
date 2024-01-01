# -*- coding: utf-8 -*-

import peewee
import telegram

import db
import scenario_handlers
from settings import SCENARIOS

from random import random

from telegram import (Update, InlineQueryResultArticle, InputTextMessageContent,
                      InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (filters, MessageHandler, ApplicationBuilder, ContextTypes,
                          CommandHandler, InlineQueryHandler, CallbackQueryHandler)


async def private_messages_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, dispatch_dict):
    user = update.effective_user
    message = update.message

    if db.UserConversation.select().where(db.UserConversation.user_id == user.id):
        user_in_db = db.UserConversation.select().where(db.UserConversation.user_id == user.id).get()

        if user_in_db.scenario_name != 'NULL':
            await continue_scenario(message=message, user_in_db=user_in_db, user=user, dispatch_dict=dispatch_dict)
        else:
            user_in_db.context['messages'].append(message.message_id)
            user_in_db.save()

    else:
        new_user = db.UserConversation.create(
            user_id=user.id,
            scenario_name='NULL',
            step_name='NULL',
            context={'messages': [message.message_id]}
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


async def continue_scenario(message, user_in_db, user, dispatch_dict):
    scenario_name = user_in_db.scenario_name
    steps = SCENARIOS[scenario_name]['steps']
    step = steps[user_in_db.step_name]

    if 'handler' in step:
        handler = getattr(scenario_handlers, step['handler'])
        await handler(
            user=user,
            message=message,
            user_in_db=user_in_db,
            dispatch_dict=dispatch_dict,
            steps=steps,
            step=step
        )
    else:
        await general_step_handler(user_id=user.id, dispatch_dict=dispatch_dict, step=step, scenario_name=scenario_name)

    if 'same_step' not in dispatch_dict:
        if step['next_step']:
            user_in_db.step_name = step['next_step']
            user_in_db.save()
        else:
            db.UserConversation.delete().where(db.UserConversation.user_id == user.id).execute()


async def general_step_handler(user_id, dispatch_dict, step, scenario_name):
    if scenario_name in ['Задать вопрос', 'Авторизация']:
        if 'message' in step:
            dispatch_dict['text_list'] = step['message']
            dispatch_dict['receiver_id'] = user_id
    elif scenario_name == 'Администратор':
        pass
    else:
        dispatch_dict['start'] = True


async def private_attachments_handler(context: ContextTypes.DEFAULT_TYPE, attachment, receiver_id):
    if type(attachment) is tuple:
        # attach_id_set = set()
        # attach_list = []
        # for attach in attachment:
        #     if attach.file_id not in attach_id_set:
        #         attach_list.append(attach)
        #         attach_id_set.add(attach.file_id)
        # for attach_unique in attach_list:
        await attachment_type(context=context, attachment=attachment[0], receiver_id=receiver_id)
    else:
        await attachment_type(context=context, attachment=attachment, receiver_id=receiver_id)


async def attachment_type(context: ContextTypes.DEFAULT_TYPE, attachment, receiver_id):
    if type(attachment) is telegram.PhotoSize:
        await context.bot.send_photo(chat_id=receiver_id, photo=attachment)
    elif type(attachment) is telegram.Sticker:
        await context.bot.send_sticker(chat_id=receiver_id, sticker=attachment)
    elif type(attachment) is telegram.Animation:
        await context.bot.send_animation(chat_id=receiver_id, animation=attachment)
    elif type(attachment) is telegram.Audio:
        await context.bot.send_audio(chat_id=receiver_id, audio=attachment)
    elif type(attachment) is telegram.Document:
        await context.bot.send_document(chat_id=receiver_id, document=attachment)
    elif type(attachment) is telegram.Contact:
        await context.bot.send_contact(chat_id=receiver_id, contact=attachment)
    elif type(attachment) is telegram.Voice:
        await context.bot.send_voice(chat_id=receiver_id, voice=attachment)
    elif type(attachment) is telegram.Video:
        await context.bot.send_video(chat_id=receiver_id, video=attachment)
    elif type(attachment) is telegram.VideoNote:
        await context.bot.send_video_note(chat_id=receiver_id, video_note=attachment)
    elif type(attachment) is telegram.Location:
        await context.bot.send_location(chat_id=receiver_id, location=attachment)
