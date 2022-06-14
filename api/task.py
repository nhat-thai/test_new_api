import requests
import pandas as pd
import json


def authorization_login():
    # LOG IN
    headers = {
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.63 Safari/537.36',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="102", "Google Chrome";v="102"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }

    response = requests.get('https://benkon-cloudbe.web.app/', headers=headers)
    print(f'[INFO] Response Login Status: {response}')


def authorization_user_id(
        token: str,
        user_id: str
):
    # ACCESS TO USER_ID
    headers = {
        'authority': 'benkon-api-dev-3nuez2dx.an.gateway.dev',
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'authorization': token,
        'origin': 'https://benkon-cloudbe.web.app',
        'referer': 'https://benkon-cloudbe.web.app/',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="102", "Google Chrome";v="102"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.63 Safari/537.36',
    }

    params = {
        'user': user_id,
    }

    response = requests.get('https://benkon-api-dev-3nuez2dx.an.gateway.dev/v1/devices', params=params, headers=headers)
    print(f'[INFO] Response Access User ID: {response}')


def get_data(
        token: str,
        device_id: str,
        track_day: str,
        data_type: str
) -> pd.DataFrame:
    # GET DATA
    headers = {
        'authority': 'benkon-api-dev-3nuez2dx.an.gateway.dev',
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'authorization': token,
        'origin': 'https://benkon-cloudbe.web.app',
        'referer': 'https://benkon-cloudbe.web.app/',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="102", "Google Chrome";v="102"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.63 Safari/537.36',
    }

    start_time_ISO = track_day + 'T00:00:00+07:00'
    end_time_ISO = track_day + 'T23:59:59+07:00'

    params = {
        'fromISO': start_time_ISO,
        'toISO': end_time_ISO,
    }

    response = requests.get(f'https://benkon-api-dev-3nuez2dx.an.gateway.dev/v1/devices/{device_id}/data/{data_type}',
                            params=params, headers=headers)
    print(f'[INFO] Response get {data_type} data: {response}')

    json_data = json.loads(response.text)
    item = json_data.get('items')
    df = pd.DataFrame(item)

    return df
