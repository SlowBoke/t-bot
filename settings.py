# -*- coding: utf-8 -*-

TOKEN = '6321442559:AAENhbJLQWyTLlxLY9aHMQR9ntWNfL61F98'

TOKEN_PATH = 'data/token.json'

SHEET_ID = "1q-_OhzeE8yrEN7bYRHf4pNkEzi9bR5XSEiCfgm754Wc"

ACCEPTABLE_WARNING_QUANTITY = 15

INTENTS = [
    {
        'name': 'Приветствие',
        'tokens': ('привет', 'здоров', 'здрас', 'добр'),
        'scenario': None,
        'answer': 'Приветствую. Я - бот-ассистент мероприятия РобоФест, готов помочь с регистрацией на ивент '
                  'и прояснить организационные вопросы.'
    },
    {
        'name': 'Дата проведения',
        'tokens': ('когда', 'сколько', 'дата', 'дату', 'врем'),
        'scenario': None,
        'answer': 'Мероприятие проводится пятнадцатого апреля (15.04.2024), начало регистрации в 10 утра.'
    },
    {
        'name': 'Место проведения',
        'tokens': ('где', 'место', 'локац', 'адрес', 'метро'),
        'scenario': None,
        'answer': 'РобоФест пройдёт в павильоне 18Г в Экспоцентре.'
    },
    {
        'name': 'Регистрация',
        'tokens': ('регистр', 'добав', 'зарега', 'запиши', 'регай'),
        'scenario': 'registration',
        'answer': None
    },
    {
        'name': 'Любезность',
        'tokens': ('спасиб', 'благодар'),
        'scenario': None,
        'answer': 'Всегда рад помочь. Если остались ещё вопросы, постараюсь разрешить их.'
    },
    {
        'name': 'Прощание',
        'tokens': ('пока', 'досвид', 'доброго', 'хорошего', 'прощай', 'увидимся'),
        'scenario': None,
        'answer': 'До встречи на РобоФесте!'
    },
]

SCENARIOS = {
    'Задать вопрос': {
        'first_step': 'step1',
        'steps': {
            'step1': {
                'handler': None,
                'message': 'Задайте интересующий вас вопрос:',
                'next_step': 'step2'
            },
            'step2': {
                'handler': 'admin_receiver',
                'next_step': 'step3'
            },
            'step3': {
                'handler': 'rating_handler',
                'message1': 'Спасибо за оценку.',
                'message0': 'Сожалеем, мы учтём ваш опыт в будущем.',
                'next_step': None
            },
        }
    },
    'Авторизация': {
        'first_step': 'step1',
        'steps': {
            'step1': {
                'handler': None,
                'message': 'Вход в режим модератора. Введите логин:',
                'next_step': 'step2'
            },
            'step2': {
                'handler': 'login_handler',
                'message': 'Введите логин:',
                'message_failure': 'Неверный логин.',
                'next_step': 'step3'
            },
            'step3': {
                'handler': 'password_handler',
                'message': 'Введите пароль:',
                'message_failure': 'Неверный пароль.',
                'message_final': 'Добро пожаловать, {admin_name}.',
                'next_step': None
            },
        }
    },
    'Администратор': {
        'first_step': 'step1',
        'steps': {
            'step1': {
                'handler': None,
                'next_step': 'step2'
            },
            'step2': {
                'handler': 'customer_receiver',
                'next_step': None
            },
        }
    }
}
