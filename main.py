# -*- coding: utf-8 -*-

import peewee
import telegram
import asyncio
import datetime

import db
from settings import TOKEN, SCENARIOS
from private_message_handler import private_messages_handler, start_scenario

from telegram import (Update, InlineQueryResultArticle, InputTextMessageContent, BotCommand, MenuButton, ChatMember,
                      MenuButtonCommands, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions)

from telegram.ext import (filters, MessageHandler, Application, ApplicationBuilder, ContextTypes,
                          CommandHandler, InlineQueryHandler, CallbackQueryHandler,
                          ChatMemberHandler, ChatJoinRequestHandler)


def db_init():
    """Initialising the database"""
    database = peewee.SqliteDatabase('db\\db.db')
    db.database_proxy.initialize(database)

    database.create_tables([db.UserConversation, db.AdminLogin, db.GroupViolation], safe=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        await update.effective_user.send_message(
            text='Вас приветствует бот Телеграм-канала "НеймХолдер". Укажите, чем могу вам помочь.'
        )

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
    if update.effective_chat.type == 'private':
        await update.effective_chat.send_message(
            text='Данный бот осуществляет коммуникацию между пользователями и модераторами Телеграм-канала "НеймХолдер,'
                 '\nпроводит первичную модерацию сообщений внутри канала, \nобеспечивает модераторов и владельца '
                 'канала инструментами своевременного оповещения о нарушениях политики канала и сбора информации о '
                 'действиях внутри канала для их дальнейшего анализа.'
        )


async def admin_logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
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
    if update.effective_chat.type == 'private':
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
                    await context.bot.send_message(
                        chat_id=customer_id,
                        text='Благодарим за обращение. \nОстались ли вы довольны общением? '
                             'Напишите "1", если да,''"0" - если нет.'
                    )
                else:
                    await update.effective_user.send_message(text='У вас нет активных диалогов.')
            else:
                await update.effective_user.send_message(text='Вы не являетесь модератором.')
        except peewee.DoesNotExist as exc:
            await update.effective_user.send_message(text='Вы не являетесь модератором.')


async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_admins = await update.effective_chat.get_administrators()
    if update.effective_user in (admin.user for admin in chat_admins):
        guilty_user = update.message.reply_to_message.from_user

        await guilty_user.send_message(
            text=f'Вы были исключены из группы "НеймХолдер", причиной послужило ваше сообщение:'
        )
        await update.message.reply_to_message.copy(chat_id=guilty_user.id)
        await guilty_user.send_message(
            text=f'Для восстановления в группе обратитесь к модератору посредством данного бота.'
        )

        await update.message.reply_to_message.delete()
        await update.message.delete()
        await update.effective_chat.ban_member(user_id=guilty_user.id)


async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_admins = await update.effective_chat.get_administrators()
    if update.effective_user in (admin.user for admin in chat_admins):
        guilty_user = update.message.reply_to_message.from_user
        acceptable_warning_quantity = 4

        try:
            user_db = db.GroupViolation.select().where(db.GroupViolation.user_id == guilty_user.id).get()
            user_db.violation_quantity += 1
            user_db.save()

            if user_db.violation_quantity > acceptable_warning_quantity:

                await guilty_user.send_message(
                    text=f'Вы были исключены из группы "НеймХолдер", причиной послужило ваше сообщение:'
                )
                await update.message.reply_to_message.copy(chat_id=guilty_user.id)
                await guilty_user.send_message(
                    text=f'Для восстановления в группе обратитесь к модератору посредством данного бота.'
                )

                await update.message.reply_to_message.delete()
                await update.message.delete()
                await update.effective_chat.ban_member(user_id=guilty_user.id)

                db.GroupViolation.delete().where(db.GroupViolation.user_id == guilty_user.id).execute()
                return
        except peewee.DoesNotExist as exc:
            db.GroupViolation.create(user_id=guilty_user.id, violation_quantity=1)
        finally:
            user_db = db.GroupViolation.select().where(db.GroupViolation.user_id == guilty_user.id).get()

            if user_db.violation_quantity == acceptable_warning_quantity:
                await guilty_user.send_message(
                    text=f'Вам вынесено предупреждение вследствие нарушения правил группы "НеймХолдер" вашим сообщением:'
                )
                await update.message.reply_to_message.copy(chat_id=guilty_user.id)
                await guilty_user.send_message(
                    text=f'Внимание! Это - крайнее предупреждение, следующее нарушение правил приведёт к исключению '
                         f'из группы'
                )

            else:
                await guilty_user.send_message(
                    text=f'Вам вынесено предупреждение вследствие нарушения правил группы "НеймХолдер" вашим сообщением:'
                )
                await update.message.reply_to_message.copy(chat_id=guilty_user.id)
                await guilty_user.send_message(
                    text=f'Дальнейшее игнорирование предписаний может повлечь за собой исключение из группы, '
                         f'будьте внимательны!'
                )

            await update.message.reply_to_message.delete()
            await update.message.delete()


async def new_user_restrict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in ['supergroup', 'channel']:
        chat_member_update = update.chat_member
        status_change = chat_member_update.difference().get('status')
        old_is_member, new_is_member = chat_member_update.difference().get('is_member', (None, None))
        if status_change is None:
            return None

        old_status, new_status = status_change
        was_member = old_status in [
            ChatMember.MEMBER,
            ChatMember.OWNER,
            ChatMember.ADMINISTRATOR,
        ] or (old_status == ChatMember.RESTRICTED and old_is_member is True)
        is_member = new_status in [
            ChatMember.MEMBER,
            ChatMember.OWNER,
            ChatMember.ADMINISTRATOR,
        ] or (new_status == ChatMember.RESTRICTED and new_is_member is True)

        if not was_member and is_member:
            datetime_now = datetime.datetime.utcnow()
            datetime_restricted = datetime_now + datetime.timedelta(minutes=1)
            new_user_id = update.chat_member.new_chat_member.user.id
            permissions_new = ChatPermissions(
                can_send_messages=False,
                can_send_polls=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False,
                can_change_info=False,
                can_invite_users=True,
                can_pin_messages=False,
                can_manage_topics=False,
                can_send_audios=False,
                can_send_documents=False,
                can_send_photos=False,
                can_send_videos=False,
                can_send_video_notes=False,
                can_send_voice_notes=False
            )

            await update.effective_chat.restrict_member(
                user_id=new_user_id,
                until_date=datetime_restricted,
                permissions=permissions_new,
            )
            await context.bot.send_message(
                chat_id=new_user_id,
                text='Рад приветствовать вас в группе "НеймХолдер". Для новых пользователей в течение часа действует '
                     'ограничение на отправку медиа и ссылок.'
            )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
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
    if update.effective_chat.type == 'private':
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
    ban_handler = CommandHandler('ban', ban_user)
    warning_handler = CommandHandler('warn', warn_user)
    button_handler = CallbackQueryHandler(button)
    new_member_handler = ChatMemberHandler(new_user_restrict, ChatMemberHandler.CHAT_MEMBER)
    private_message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), private_message)

    application.add_handlers([start_handler, help_handler, logout_handler, close_handler, ban_handler, warning_handler])
    application.add_handler(button_handler)
    application.add_handler(new_member_handler)
    application.add_handler(private_message_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES)



# async def dispatch_dict_handler(dispatch_dict, context: ContextTypes.DEFAULT_TYPE):
#     if 'text_list' in dispatch_dict:
#         for text in dispatch_dict['text_list']:
#             await context.bot.send_message(chat_id=dispatch_dict['receiver_id'], text=text)


if __name__ == '__main__':
    main()
