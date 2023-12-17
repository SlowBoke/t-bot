# -*- coding: utf-8 -*-

import peewee
import telegram
import asyncio

import db
from settings import TOKEN, SCENARIOS
from private_message_handler import private_messages_handler, start_scenario

from telegram import (Update, InlineQueryResultArticle, InputTextMessageContent, BotCommand, MenuButton,
                      MenuButtonCommands, InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (filters, MessageHandler, Application, ApplicationBuilder, ContextTypes,
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

    # command1 = BotCommand(command='start', description='Начните отсюда, чтоб выбрать действие.')
    # command2 = BotCommand(command='help', description='Краткое описание возможностей бота.')
    # await context.bot.set_my_commands([command1, command2])
    # await update.effective_user.set_menu_button(menu_button=MenuButtonCommands())


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.effective_chat.send_message(text='Данный бот осуществляет коммуникацию между пользователями '
                                                  'и модераторами Телеграм-канала "НеймХолдер, \n'
                                                  'проводит первичную модерацию сообщений внутри канала, \n'
                                                  'обеспечивает модераторов и владельца канала инструментами '
                                                  'своевременного оповещения о нарушениях политики канала и '
                                                  'сбора информации о действиях внутри канала для '
                                                  'их дальнейшего анализа.')


async def admin_logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    try:
        user_db = db.UserConversation.select().where(db.UserConversation.user_id == user.id).get()

        if user_db.scenario_name == 'Администратор':
            db.UserConversation.delete().where(db.UserConversation.user_id == user.id).execute()
            await update.effective_user.send_message(text='Выход произведён, всего доброго.')

            new_menu = {
                'start': 'Начните отсюда, чтобы выбрать действие.',
                'help': 'Краткое описание возможностей бота.'
            }
            await menu_button(update=update, context=context, command_dict=new_menu)
        else:
            await update.effective_user.send_message(text='Вы не являетесь модератором.')
    except peewee.DoesNotExist as exc:
        await update.effective_user.send_message(text='Вы не являетесь модератором.')


async def admin_conversation_over(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    try:
        admin_db = db.UserConversation.select().where(db.UserConversation.user_id == user.id).get()
        if admin_db.scenario_name == 'Администратор':
            if admin_db.step_name == 'step2':
                customer_id = admin_db.context['customer_id']
                customer_db = db.UserConversation.select().where(db.UserConversation.user_id == customer_id).get()

                admin_db.step_name = SCENARIOS[admin_db.scenario_name]['first_step']
                admin_db.context = {}
                admin_db.save()

                customer_steps = SCENARIOS[customer_db.scenario_name]['steps']
                customer_db.step_name = customer_steps[customer_db.step_name]['next_step']
                customer_db.save()

                await update.effective_user.send_message(text='Диалог завершён.')
                await context.bot.send_message(chat_id=customer_id, text='Благодарим за обращение. \n'
                                                                         'Остались ли вы довольны общением? '
                                                                         'Напишите "1", если да,''"0" - если нет.')
            else:
                await update.effective_user.send_message(text='У вас нет активных диалогов.')
        else:
            await update.effective_user.send_message(text='Вы не являетесь модератором.')
    except peewee.DoesNotExist as exc:
        await update.effective_user.send_message(text='Вы не являетесь модератором.')


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
    dispatch_dict = {}
    await private_messages_handler(update=update, context=context, dispatch_dict=dispatch_dict)
    if dispatch_dict:
        if 'text_list' in dispatch_dict:
            for text in dispatch_dict['text_list']:
                await context.bot.send_message(chat_id=dispatch_dict['receiver_id'], text=text)
        if 'start' in dispatch_dict:
            await start(update=update, context=context)
        if 'menu_change' in dispatch_dict:
            new_menu = {
                'logout': 'Выход из режима модерации.',
                'close': 'Завершить текущий диалог.',
                'help': 'Краткое описание возможностей бота.'
            }
            await menu_button(update=update, context=context, command_dict=new_menu)


async def menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE, command_dict):  # TODO: no individual menu
    command_list = [BotCommand(command=key, description=arg) for key, arg in command_dict.items()]

    await context.bot.set_my_commands(command_list)
    await update.effective_user.set_menu_button(menu_button=MenuButtonCommands())


def main():
    db_init()

    application = ApplicationBuilder().token(TOKEN).concurrent_updates(True).build()

    start_handler = CommandHandler('start', start)
    help_handler = CommandHandler('help', help)
    logout_handler = CommandHandler('logout', admin_logout)
    close_handler = CommandHandler('close', admin_conversation_over)
    button_handler = CallbackQueryHandler(button)
    private_message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), private_message)

    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(logout_handler)
    application.add_handler(close_handler)
    application.add_handler(button_handler)
    application.add_handler(private_message_handler)

    application.run_polling()



# async def dispatch_dict_handler(dispatch_dict, context: ContextTypes.DEFAULT_TYPE):
#     if 'text_list' in dispatch_dict:
#         for text in dispatch_dict['text_list']:
#             await context.bot.send_message(chat_id=dispatch_dict['receiver_id'], text=text)


if __name__ == '__main__':
    main()
