import pandas as pd
from datetime import time
import pytz

from api.notification import gen_notifications
from api.task import *
from api.device_info.controllers import *
from api.utils import *
from process_data.extract_user_data import *
from process_data.chart import export_chart

token = 'Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjFhZWY1NjlmNTI0MTRlOWY0YTcxMDRiNmQwNzFmMDY2ZGZlZWQ2NzciLCJ0eXAiOiJKV1QifQ.eyJuYW1lIjoiTmhhdCBUaGFpIiwicGljdHVyZSI6Imh0dHBzOi8vbGgzLmdvb2dsZXVzZXJjb250ZW50LmNvbS9hL0FBVFhBSngxVlFiRkRrTW1sSWRidl9DWTRaWFhPM1B3MTJyT2FPYTlpbGdPPXM5Ni1jIiwiaXNzIjoiaHR0cHM6Ly9zZWN1cmV0b2tlbi5nb29nbGUuY29tL2Jlbmtvbi1jbG91ZGJlIiwiYXVkIjoiYmVua29uLWNsb3VkYmUiLCJhdXRoX3RpbWUiOjE2NTQ2MDQwODksInVzZXJfaWQiOiJCSHRKV3ZUSFdUTk1TWW9wRHFvZzI5c0RTZjAyIiwic3ViIjoiQkh0Sld2VEhXVE5NU1lvcERxb2cyOXNEU2YwMiIsImlhdCI6MTY1NTE3MjExNCwiZXhwIjoxNjU1MTc1NzE0LCJlbWFpbCI6Im5oYXQudGhhaUBsYWIybGl2ZXMuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsImZpcmViYXNlIjp7ImlkZW50aXRpZXMiOnsiZ29vZ2xlLmNvbSI6WyIxMTE0ODg0Nzc2MzU1NTAwODgyMTAiXSwiZW1haWwiOlsibmhhdC50aGFpQGxhYjJsaXZlcy5jb20iXX0sInNpZ25faW5fcHJvdmlkZXIiOiJnb29nbGUuY29tIn19.ceEYDtu_MKAZyOxJ5jgDqCb1QEAAS-z_-qlyy_KPQZTgrkGWQCeiePOR40AdrgTh0Jatxg59Fa322Sj0l0ToR4zstPbjuYp-Gb_ZWNsTkIAipkwK5YQlcxY-rO2xf5gJ3uwft9eC-d0BxAB4Vsr70gVespHaAOVybBxokILFcDgBQuIrF7RgXKAyG6ssMSVUM_TaYGjzOLgyFgZJsgrZOL7odHL9ADmjKBCgIMd0gGOXSHnXKWZyNH4wBPvWjgNPclBKOZ_zlghduPRQAH7f6Xi5vA5424dCIsgfcf_zrBVYfK-ZeRUHe2ovvOvdEPo0Mi5bYoRLgXt2iF6Whg2gfw'


if __name__ == '__main__':

    authorization_login()

    df_info = get_df_info()

    start_time = '2022-05-14'
    end_time = '2022-06-13'
    customer_id = "33"

    date = pd.to_datetime(start_time)
    while date <= pd.to_datetime(end_time):

        track_day = date.strftime('%Y-%m-%d')
        print(track_day)

        gen_notifications(
            token=token,
            customer_id=customer_id,
            track_day=track_day,
            mail_list=[],
            bcc_list=[]
        )

        date += pd.to_timedelta(1, 'D')
