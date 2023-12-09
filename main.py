# -*- coding: utf-8 -*-

import peewee

import db
from settings import TOKEN, SCENARIOS
from private_message_handler import private_messages_handler, start_scenario

from telegram import (Update, InlineQueryResultArticle, InputTextMessageContent,
                      InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (filters, MessageHandler, ApplicationBuilder, ContextTypes,
                          CommandHandler, InlineQueryHandler, CallbackQueryHandler)


def db_init():
    """Initialising the database"""
    database = peewee.SqliteDatabase('db\\db.db')
    db.database_proxy.initialize(database)

    database.create_tables([db.UserConversation, db.AdminLogin, db.GroupViolation], safe=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.effective_user.send_message(text='Вас приветствует бот Телеграм-канала "НеймХолдер". '
                                                  'Укажите, чем могу вам помочь.')

    keyboard = [
        [InlineKeyboardButton("Задать вопрос", callback_data='Задать вопрос')],
        [InlineKeyboardButton("Авторизоваться (админ)", callback_data='Авторизация')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text('Пожалуйста, выберите:', reply_markup=reply_markup)


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.effective_chat.send_message(text='Данный бот осуществляет коммуникацию между пользователями '
                                                  'и модераторами Телеграм-канала "НеймХолдер, \n'
                                                  'проводит первичную модерацию сообщений внутри канала, \n'
                                                  'обеспечивает модераторов и владельца канала инструментами '
                                                  'своевременного оповещения о нарушениях политики канала и '
                                                  'сбора информации о действиях внутри канала для '
                                                  'их дальнейшего анализа.')


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    scenario_name = query.data
    user = update.effective_user

    await query.edit_message_text(text=f"Выбранно: {scenario_name}")

    dispatch_dict = start_scenario(user=user, scenario_name=scenario_name)
    if dispatch_dict:
        if 'text_list' in dispatch_dict:
            for text in dispatch_dict['text_list']:
                await context.bot.send_message(chat_id=dispatch_dict['receiver_id'], text=text)


async def private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dispatch_dict = private_messages_handler(update=update, context=context)
    if dispatch_dict:
        if 'text_list' in dispatch_dict:
            for text in dispatch_dict['text_list']:
                await context.bot.send_message(chat_id=dispatch_dict['receiver_id'], text=text)


# async def dispatch_dict_handler(dispatch_dict, context: ContextTypes.DEFAULT_TYPE):
#     if 'text_list' in dispatch_dict:
#         for text in dispatch_dict['text_list']:
#             await context.bot.send_message(chat_id=dispatch_dict['receiver_id'], text=text)


if __name__ == '__main__':
    db_init()

    application = ApplicationBuilder().token(TOKEN).build()

    start_handler = CommandHandler('start', start)
    help_handler = CommandHandler('help', help)
    button_handler = CallbackQueryHandler(button)
    private_message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), private_message)

    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(button_handler)
    application.add_handler(private_message_handler)

    application.run_polling()
