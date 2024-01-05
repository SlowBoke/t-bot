# -*- coding: utf-8 -*-
import csv

import peewee
import telegram
import asyncio
import datetime
import re

import db
from settings import TOKEN, SCENARIOS, FORBIDDEN_WORDS, ACCEPTABLE_WARNING_QUANTITY
from private_message_handler import private_messages_handler, start_scenario, private_attachments_handler
from sheet_record import sheet_init, sheet_append

from telegram import (
    Update, InlineQueryResultArticle, InputTextMessageContent, BotCommand, BotCommandScopeAllPrivateChats,
    BotCommandScopeChat, BotCommandScopeAllChatAdministrators, MenuButton, ChatMember, MenuButtonCommands,
    InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
)

from telegram.ext import (
    filters, MessageHandler, Application, ApplicationBuilder, ContextTypes, CommandHandler, InlineQueryHandler,
    CallbackQueryHandler, ChatMemberHandler, ChatJoinRequestHandler
)


def db_init():
    """Initialising the database"""
    database = peewee.SqliteDatabase('data\\db\\db.db')
    db.database_proxy.initialize(database)

    database.create_tables([db.UserConversation, db.AdminLogin, db.GroupViolation, db.SheetInfo], safe=True)

    admin_list = [{'admin_name': '', 'login': 'mainadmin', 'password': '2468admin'}]
    for admin in admin_list:
        try:
            db.AdminLogin.select().where(db.AdminLogin.login == admin['login']).get()
        except peewee.DoesNotExist:
            db.AdminLogin.create(user_id=0, **admin)

    try:
        db.SheetInfo.select().where(db.SheetInfo.cur_row != 0).get()
    except peewee.DoesNotExist:
        db.SheetInfo.create(cur_row=2)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        try:
            user_db = db.UserConversation.select().where(
                db.UserConversation.scenario_name == 'Задать вопрос' and
                db.UserConversation.step_name == 'step2' and
                db.UserConversation.user_id == update.effective_user.id
            ).get()
        except peewee.DoesNotExist:
            user_db = None

        if not user_db:
            await update.effective_user.send_message(
                text='Вас приветствует бот Телеграм-канала "НеймХолдер". Укажите, чем могу вам помочь.'
            )

            keyboard = [
                [InlineKeyboardButton("Задать вопрос", callback_data='Задать вопрос')],
                [InlineKeyboardButton("Авторизоваться (админ)", callback_data='Авторизация')],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text('Пожалуйста, выберите:', reply_markup=reply_markup)
        else:
            await update.effective_user.send_message(text='Дождитесь завершения текущего диалога.')
            await context.bot.send_message(
                chat_id=user_db.context['admin_id'],
                text='Бот:\nПользователь попытался вызвать комманду "/start" в текущем активном диалоге.'
            )

        ### First launch menu button setup ###

        new_menu_chat = {
            'start': 'Начните отсюда, чтобы выбрать действие.',
            'help': 'Краткое описание возможностей бота.'
        }
        new_menu_group_admin = {
            'ban': 'Забанить пользователя.',
            'warn': 'Вынести пользователю предупреждение.',
            'delete': 'Удалить сообщение.'
        }

        await menu_button(
            update=update,
            context=context,
            command_dict=new_menu_chat,
            scope=BotCommandScopeAllPrivateChats()
        )
        await menu_button(
            update=update,
            context=context,
            command_dict=new_menu_group_admin,
            scope=BotCommandScopeAllChatAdministrators()
        )


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

                if user_db.step_name == 'step2':
                    await admin_conversation_over(update=update, context=context)

                db.UserConversation.delete().where(db.UserConversation.user_id == user.id).execute()

                await update.effective_user.send_message(text='Выход произведён, всего доброго.')

                new_menu_chat = {
                    'start': 'Начните отсюда, чтобы выбрать действие.',
                    'help': 'Краткое описание возможностей бота.'
                }
                await menu_button(
                    update=update,
                    context=context,
                    command_dict=new_menu_chat,
                    scope=BotCommandScopeChat(chat_id=update.effective_chat.id)
                )

                color_dict = {'g': 1, 'b': 1}
                admin_login = db.AdminLogin.select().where(
                    db.AdminLogin.user_id == update.effective_user.id).get().login
                sheet_append(
                    event='ВЫХОД',
                    admin=admin_login,
                    color_dict=color_dict
                )

                admin_db = db.AdminLogin.select().where(db.AdminLogin.user_id == user.id).get()
                admin_db.user_id = 0
                admin_db.save()
            else:
                await update.effective_user.send_message(text='Вы не являетесь модератором.')
        except peewee.DoesNotExist:
            await update.effective_user.send_message(text='Вы не являетесь модератором.')


async def admin_conversation_over(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        user = update.effective_user

        try:
            admin_db = db.UserConversation.select().where(db.UserConversation.user_id == user.id).get()
            if admin_db.scenario_name == 'Администратор':
                if admin_db.step_name == 'step2':
                    customer_id = admin_db.context['customer_id']
                    customer_link = admin_db.context['customer_link']
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

                    color_dict = {'g': 1}
                    admin_login = db.AdminLogin.select().where(db.AdminLogin.user_id == user.id).get().login
                    sheet_append(
                        event='ОБРАЩЕНИЕ',
                        admin=admin_login,
                        context=f'Юзер: {customer_link}\nКомментарий: {" ".join(context.args)}',
                        color_dict=color_dict
                    )
                else:
                    await update.effective_user.send_message(text='У вас нет активных диалогов.')
            else:
                await update.effective_user.send_message(text='Вы не являетесь модератором.')
        except peewee.DoesNotExist:
            await update.effective_user.send_message(text='Вы не являетесь модератором.')
            
            
async def delete_chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_admins = await update.effective_chat.get_administrators()
    if update.effective_user in (admin.user for admin in chat_admins):
        await update.message.reply_to_message.delete()
        await update.message.delete()


async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_admins = await update.effective_chat.get_administrators()
    if update.effective_user in (admin.user for admin in chat_admins):
        guilty_user = update.message.reply_to_message.from_user

        await banning_sample(update=update, guilty_user=guilty_user)

        color_dict = {'r': 1}
        admin_login = db.AdminLogin.select().where(db.AdminLogin.user_id == update.effective_user.id).get().login
        sheet_append(
            event='БАН',
            admin=admin_login,
            context=f'Юзер: {guilty_user.link}\nКомментарий: {" ".join(context.args)}',
            color_dict=color_dict
        )


async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_admins = await update.effective_chat.get_administrators()
    if update.effective_user in (admin.user for admin in chat_admins):
        try:
            db.UserConversation.select().where(
                db.UserConversation.user_id == update.effective_user.id
                and db.UserConversation.scenario_name == 'Администратор'
            ).get()
            guilty_user = update.message.reply_to_message.from_user
            guilty_message = update.message.reply_to_message

            await warning_sample(update=update, guilty_user=guilty_user, guilty_message=guilty_message)

            color_dict = {'r': 1, 'g': -125}
            admin_login = db.AdminLogin.select().where(db.AdminLogin.user_id == update.effective_user.id).get().login
            sheet_append(
                event='ПРЕДУПРЕЖДЕНИЕ',
                admin=admin_login,
                context=f'Юзер: {guilty_user.link}\nКомментарий: {" ".join(context.args)}',
                color_dict=color_dict
            )
        except peewee.DoesNotExist:
            pass


async def banning_sample(update, guilty_user):
    await guilty_user.send_message(
        text=f'Вы были исключены из группы "НеймХолдер", Для восстановления в группе обратитесь к модератору '
             f'посредством данного бота. Причиной послужило ваше сообщение:'
    )
    await update.message.reply_to_message.copy(chat_id=guilty_user.id)

    await update.message.reply_to_message.delete()
    await update.message.delete()
    await update.effective_chat.ban_member(user_id=guilty_user.id)

    try:
        db.GroupViolation.delete().where(db.GroupViolation.user_id == guilty_user.id).execute()
    except peewee.DoesNotExist:
        pass


async def warning_sample(update, guilty_user, guilty_message):
    try:
        user_db = db.GroupViolation.select().where(db.GroupViolation.user_id == guilty_user.id).get()
        user_db.violation_quantity += 1
        user_db.save()

        if user_db.violation_quantity > ACCEPTABLE_WARNING_QUANTITY:
            await banning_sample(update=update, guilty_user=guilty_user)
            return
    except peewee.DoesNotExist:
        db.GroupViolation.create(user_id=guilty_user.id, violation_quantity=1)
    finally:
        user_db = db.GroupViolation.select().where(db.GroupViolation.user_id == guilty_user.id).get()

        if user_db.violation_quantity == ACCEPTABLE_WARNING_QUANTITY:
            await guilty_user.send_message(
                text=f'Внимание! Это - крайнее предупреждение, следующее нарушение правил приведёт к исключению '
                     f'из группы "НеймХолдер".\nВаше сообщение:'
            )
            await guilty_message.copy(chat_id=guilty_user.id)

        else:
            await guilty_user.send_message(
                text=f'Вам вынесено предупреждение вследствие нарушения правил группы "НеймХолдер"\n'
                     f'Дальнейшее игнорирование предписаний может повлечь за собой исключение из группы, '
                     f'будьте внимательны!\nВаше сообщение:'
            )
            await guilty_message.copy(chat_id=guilty_user.id)

        if guilty_message != update.message:
            await guilty_message.delete()
        await update.message.delete()


async def new_user_restrict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'supergroup':
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
                can_send_messages=True,
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
        if 'text_list' in dispatch_dict:
            for text in dispatch_dict['text_list']:
                await context.bot.send_message(chat_id=dispatch_dict['receiver_id'], text=text)
        if 'message_list' in dispatch_dict:
            for message_id in dispatch_dict['message_list']:
                await context.bot.copy_message(
                    chat_id=dispatch_dict['receiver_id'],
                    from_chat_id=update.message.chat_id,
                    message_id=message_id
                )
        if 'attachment_list' in dispatch_dict:
            for attachment in dispatch_dict['attachment_list']:
                await private_attachments_handler(
                    context=context,
                    attachment=attachment,
                    receiver_id=dispatch_dict['receiver_id']
                )
        if 'advice' in dispatch_dict:
            await start(update=update, context=context)
        if 'menu_change' in dispatch_dict:
            new_menu_chat_admin = {
                'logout': 'Выход из режима модерации.',
                'close': 'Завершить текущий диалог.',
                'help': 'Краткое описание возможностей бота.'
            }
            await menu_button(
                update=update,
                context=context,
                command_dict=new_menu_chat_admin,
                scope=BotCommandScopeChat(chat_id=update.effective_chat.id)
            )
        if 'delete_message' in dispatch_dict:
            await update.effective_message.delete()
        if 'login' in dispatch_dict:
            color_dict = {'g': 1, 'b': 1}
            sheet_append(
                event='ВХОД',
                admin=dispatch_dict['login'],
                color_dict=color_dict
            )
    else:
        # words filter for groups/channels
        try:
            message_text = update.effective_message.text.lower()
            with open('data/bad_words.csv', 'r', newline='', encoding='utf8') as csv_file:
                csv_data = csv.reader(csv_file)
                for bad_word in csv_data:
                    word_pattern = f'[\\W]{bad_word[0]}[\\W]|[\\W]{bad_word[0]}$|^{bad_word[0]}[\\W]|^{bad_word[0]}$'
                    matched = re.search(word_pattern, message_text)
                    if matched:
                        await warning_sample(
                            update=update,
                            guilty_user=update.effective_user,
                            guilty_message=update.effective_message
                        )

                        color_dict = {'r': 1, 'b': 1}
                        sheet_append(
                            event='ФИЛЬТР',
                            admin=None,
                            context=f'Юзер: {update.effective_user.link}\nСлово: {bad_word}',
                            color_dict=color_dict
                        )
                        break
        except TypeError:
            pass
        except AttributeError:
            pass


async def menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE, command_dict, scope):

    command_list = [BotCommand(command=key, description=arg) for key, arg in command_dict.items()]

    await context.bot.set_my_commands(command_list, scope=scope)
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
    delete_handler = CommandHandler('delete', delete_chat_message)
    button_handler = CallbackQueryHandler(button)
    new_member_handler = ChatMemberHandler(new_user_restrict, ChatMemberHandler.CHAT_MEMBER)
    private_message_handler = MessageHandler((~filters.COMMAND), private_message)

    application.add_handlers([start_handler, help_handler, logout_handler, delete_handler,
                              close_handler, ban_handler, warning_handler])
    application.add_handler(button_handler)
    application.add_handler(new_member_handler)
    application.add_handler(private_message_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
