# -*- coding: utf-8 -*-

import peewee

import db
from settings import TOKEN

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
        [InlineKeyboardButton("Авторизоваться (админ)", callback_data='Авторизоваться')],
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
    variant = query.data

    await query.edit_message_text(text=f"Выбранно: {variant}")


if __name__ == '__main__':
    db_init()

    application = ApplicationBuilder().token(TOKEN).build()

    start_handler = CommandHandler('start', start)
    help_handler = CommandHandler('help', help)
    button_handler = CallbackQueryHandler(button)

    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(button_handler)

    application.run_polling()
