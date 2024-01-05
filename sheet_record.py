# -*- coding: utf-8 -*-

import datetime
import os

import googleapiclient.discovery
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError

import db
from settings import TOKEN_PATH, SHEET_ID
from g_sheets_start.quickstart import new_token


def sheet_init():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, scopes)
    return googleapiclient.discovery.build("sheets", "v4", credentials=creds)


def sheet_append(event, admin, color_dict, context=None):
    try:
        sheet_db = db.SheetInfo.select().get()

        datetime_now = datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        date, time = datetime_now.split(" ")

        service = sheet_init()
        row = [date, time, event, admin, context]
        values = [
            {
                'userEnteredFormat': {
                    'backgroundColor': {
                        'red': color_handler(color='r', color_dict=color_dict, col_index=row.index(col)),
                        'green': color_handler(color='g', color_dict=color_dict, col_index=row.index(col)),
                        'blue': color_handler(color='b', color_dict=color_dict, col_index=row.index(col))
                    },
                    'borders': {
                        'bottom': {
                            'style': 'SOLID_MEDIUM'
                        },
                        'left': {
                            'style': 'SOLID_MEDIUM'
                        },
                        'right': {
                            'style': 'SOLID_MEDIUM'
                        }
                    }
                },
                'userEnteredValue': {
                    'stringValue': col
                }
            } for col in row
        ]

        requests = {
            'requests': [
                {'appendCells': {
                    'rows': [
                        {
                            'values': values
                        }
                    ],
                    'fields':
                        'userEnteredFormat, userEnteredValue', 'sheetId': 0
                }
                }
            ]
        }

        service.spreadsheets().batchUpdate(spreadsheetId=SHEET_ID, body=requests).execute()

        service.spreadsheets().values().batchUpdate(spreadsheetId=SHEET_ID, body={
            "valueInputOption": "USER_ENTERED",
            "data": [
                {"range": f"Лист1!A{sheet_db.cur_row}:B{sheet_db.cur_row}",
                 "majorDimension": "ROWS",
                 "values": [[date, time]]
                 }
            ]
        }).execute()

        sheet_db.cur_row += 1
        sheet_db.save()
    except (RefreshError, FileNotFoundError):
        os.remove('token.json')
        new_token()
        sheet_append(event, admin, color_dict, context)

def color_handler(color, color_dict, col_index):
    if color in color_dict:
        if color_dict[color] == 1:
            return color_dict[color]
        else:
            if col_index % 2 == 0:
                return int((-color_dict[color]-255)*0.7-color_dict[color])
            else:
                return int((-color_dict[color]-255)*0.8-color_dict[color])
    else:
        if col_index % 2 == 0:
            return int(-255*0.7)
        else:
            return int(-255*0.8)
