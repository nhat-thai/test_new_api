from datetime import datetime as dt
import pandas as pd
import numpy as np
from scipy.stats import zscore

MISSING_THRESHOLD = 11*60  # seconds

# Activities parser
OPS_MODES = {
    1: "Dry",
    2: "Fan Only",
    3: "Heat",
    4: "Cool",
    7: "Auto"
}


def parse_payload_str(row):
    # payload = row["payload"].replace("=>", ": ")
    # payload_dict = json.loads(payload)
    payload_dict = row.get("payload", {})

    state_dict = payload_dict.get('state')
    if state_dict is None:
        power = payload_dict.get("power")
        temp = payload_dict.get("temperature")
        fan_speed = payload_dict.get("fan_speed")
        ops_mode = OPS_MODES.get(payload_dict.get("operation_mode"))
    else:
        power = state_dict.get("power")
        temp = state_dict.get("temperature")
        fan_speed = state_dict.get("fan_speed")
        ops_mode = OPS_MODES.get(state_dict.get("operation_mode"))

    return pd.Series([power, temp, fan_speed, ops_mode])


def parse_date(row):
    date = dt.utcfromtimestamp(row['timestamp'])
    return date.strftime('%Y-%m-%d %H:%M:%S')


def process_activities(df_activities: pd.DataFrame) -> pd.DataFrame:
    df_activities[["power", "temperature", "fan_speed", "operation_mode"]] = df_activities.apply(parse_payload_str, axis=1)
    df_activities["date"] = df_activities.apply(parse_date, axis=1)

    necessary_columns = ["event_type", "is_success", "timestamp", "date", "power", "temperature", "fan_speed", "operation_mode"]
    return df_activities.loc[df_activities["is_success"] == True][necessary_columns]


## Drop duplicated data
def drop_duplicated(df, f='n'):

    df.drop_duplicates(inplace=True)
    df.reset_index(drop=True, inplace=True)

    return df


## Outliers
def process_outliers(df: pd.DataFrame) -> pd.DataFrame:

    if df.empty:
        return df

    cnt_loop = 0
    while True:
        z_score = zscore(df['temperature'])
        z_score = np.abs(z_score)
        outliers = np.where(z_score > 3)[0]

        for i in outliers:
            if i == 0:
                df.at[i, 'temperature'] = df['temperature'].iloc[i + 1]
                df.at[i, 'humidity'] = df['humidity'].iloc[i + 1]
            else:
                df.at[i, 'temperature'] = df['temperature'].iloc[i - 1]
                df.at[i, 'humidity'] = df['humidity'].iloc[i - 1]

        if len(outliers) == 0 or cnt_loop >= 5:
            break

        cnt_loop += 1

    return df


def power_filter(df: pd.DataFrame) -> pd.DataFrame:
    z_score = zscore(df['power'])
    z_score = np.abs(z_score)
    outliers = np.where(z_score > 3)[0]

    for i in outliers:
        if i == 0:
            df.at[i, 'power'] = df['power'].iloc[i + 1]
            df.at[i, 'energy'] = df['energy'].iloc[i + 1]
        else:
            df.at[i, 'power'] = df['power'].iloc[i - 1]
            df.at[i, 'energy'] = df['energy'].iloc[i - 1]

    return df


def energy_filter(df: pd.DataFrame) -> pd.DataFrame:
    z_score = zscore(df['energy'])
    z_score = np.abs(z_score)
    outliers = np.where(z_score > 3)[0]

    for i in outliers:
        if i == 0:
            df.at[i, 'power'] = df['power'].iloc[i + 1]
            df.at[i, 'energy'] = df['energy'].iloc[i + 1]
        else:
            df.at[i, 'power'] = df['power'].iloc[i - 1]
            df.at[i, 'energy'] = df['energy'].iloc[i - 1]

    return df


## Reset Energy
def process_reset(df: pd.DataFrame) -> pd.DataFrame:

    if df.empty:
        return df

    cnt_loop = 0
    while True:

        z_score = zscore(df['energy'])
        z_score = np.abs(z_score)
        outliers = np.where(z_score > 3)[0]

        for i in outliers:
            if i == 0:
                df.at[i, 'energy'] = df['energy'].iloc[i + 1]
                df.at[i, 'power'] = df['power'].iloc[i + 1]
            else:
                df.at[i, 'energy'] = df['energy'].iloc[i - 1]
                df.at[i, 'power'] = df['power'].iloc[i - 1]

        if len(outliers) == 0 or cnt_loop >= 5:
            break

        cnt_loop += 1

    return df


def process_power(df: pd.DataFrame, track_day: str) -> pd.DataFrame:
    date = pd.to_datetime(track_day)

    df2 = pd.DataFrame()
    for i in range(1, 25):
        df_cut = df[(df['timestamp'] > date + pd.to_timedelta(i - 1, 'D')) & (
                    df['timestamp'] < date + pd.to_timedelta(i, 'D'))]
        df_cut = energy_filter(df_cut)
        df_cut = power_filter(df_cut)
        df2 = pd.concat([df2, df_cut], ignore_index=True)

    return df2


## Missing data
def process_missing_data(df, data_type):

    missing_list = []
    missing_time = 0

    for i in range(len(df) - 1):
        curr_time = df['timestamp'].iloc[i]
        next_time = df['timestamp'].iloc[i + 1]
        delta_time = next_time - curr_time

        if delta_time.total_seconds() > MISSING_THRESHOLD:
            missing_list.append((i, i + 1, curr_time, next_time, delta_time))
            missing_time += delta_time.total_seconds()

    ## Resample missing data
    k = 0
    new_list = []

    for i in range(len(missing_list)):
        info = missing_list[i]

        df_temp = pd.DataFrame(columns=df.columns)

        # Get time
        df1 = df[k:info[0]]

        df_temp['timestamp'] = pd.date_range(start=info[2] + pd.to_timedelta(30, 'S'),
                                             end=info[3] - pd.to_timedelta(30, 'S'),
                                             freq='30S'
                                             )

        if info[4].total_seconds() > MISSING_THRESHOLD:
            if data_type == 'sensor':
                df_temp['temperature'] = np.nan
                df_temp['humidity'] = np.nan
            else:
                df_temp['energy'] = np.nan
                df_temp['power'] = np.nan
        else:
            if data_type == 'sensor':
                df_temp['temperature'] = (df['temperature'].iloc[info[0]] + df['temperature'].iloc[info[1]]) / 2
                df_temp['humidity'] = (df['humidity'].iloc[info[0]] + df['humidity'].iloc[info[1]]) / 2
            else:
                df_temp['energy'] = (df['energy'].iloc[info[0]] + df['energy'].iloc[info[1]]) / 2
                df_temp['power'] = (df['power'].iloc[info[0]] + df['power'].iloc[info[1]]) / 2

        df1 = pd.concat([df1, df_temp], ignore_index=True)

        new_list.append(df1)
        k = info[1] + 1

    df1 = df[k:len(df)]
    new_list.append(df1)

    new_df = pd.concat(new_list, ignore_index=True)
    new_df.drop_duplicates(inplace=True)

    return new_df


## Get Energy Consumption
def get_energy_consumption(df):
    if df.empty:
        return np.nan
    else:
        return df['energy'].max() - df['energy'].min()


## Get Working Time
def get_working_time(df):
    
    df_working = df[df['power'] >= 100].reset_index(drop=True)
    working_time = 0
    
    for i in range(len(df_working) - 1):
        if (df_working['timestamp'].iloc[i + 1] - df_working['timestamp'].iloc[i]).total_seconds() > MISSING_THRESHOLD:
            pass
        else:
            working_time += (df_working['timestamp'].iloc[i + 1] - df_working['timestamp'].iloc[i]).total_seconds()

    return working_time
