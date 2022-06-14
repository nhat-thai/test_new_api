import pandas as pd
import numpy as np

HUMIDITY_THRESHOLD = 70
POWER_THRESHOLD = 100


def abnormal_humidity(
        df_sensor: pd.DataFrame,
        df_energy: pd.DataFrame,
        df_activities: pd.DataFrame,
        track_day: str,
        start_working_time: float,
        end_working_time: float
):
    # If df_energy is empty or all null -> No data to compare -> Can't conclude device is abnormal -> return False
    if df_energy.empty or np.isnan(df_sensor['humidity'].mean()) or df_activities.empty:
        return False

    # Get start time and end time at type of Timestamp
    start_time = pd.to_datetime(track_day) + pd.to_timedelta(start_working_time, 'H')
    end_time = pd.to_datetime(track_day) + pd.to_timedelta(end_working_time, 'H')

    print(start_time, end_time)

    # Get the last activities before start time
    df_act_before = df_activities[df_activities['timestamp'] < start_time]

    # If there is no activities -> Check the AC power at the last time before start time
    if df_act_before.empty:

        # Get df_energy before start time
        df_energy_before = df_energy[df_energy['timestamp'] < start_time]
        if not df_energy_before.empty:
            if df_energy[df_energy['timestamp'] < start_time].iloc[-1]['power'] > 100:
                last_power_status = True
            else:
                last_power_status = False

        # If start time is sooner the first energy record -> df_energy before start time is empty -> Get the first activities power
        else:
            last_power_status = df_activities.iloc[0]['power']

    # If there is activities -> get the last power status
    else:
        last_power_status = df_act_before.iloc[-1]['power']

    print('LAST POWER STATUS: ', last_power_status)

    df_activities = df_activities[
        (df_activities['timestamp'] >= start_time) & (df_activities['timestamp'] <= end_time)
    ].reset_index(drop=True)

    df_sensor = df_sensor[
        (df_sensor['timestamp'] > start_time) & (df_sensor['timestamp'] < end_time)
    ].reset_index(drop=True)

    activities_OFF = np.where(df_activities['power'] == False)[0]
    print(activities_OFF)

    # If we have activities OFF
    if len(activities_OFF) > 0:
        range_list = []

        if not df_activities.iloc[0]['power']:
            range_list.append((start_time, df_activities.iloc[0]['timestamp']))
        else:
            df_activities.at[0, 'timestamp'] = start_time

        i = 0
        while i < len(df_activities):
            if df_activities.iloc[i]['power']:
                j = i + 1
                while j < len(df_activities):
                    if df_activities.iloc[j]['power']:
                        j += 1
                    else:
                        range_list.append((df_activities.iloc[i]['timestamp'], df_activities.iloc[j]['timestamp']))
                        i = j
                        break
            i += 1

        print(range_list)

        df_sensor_calc = pd.DataFrame()
        for _range in range_list:
            df_sub_sensor = df_sensor[(df_sensor['timestamp'] > _range[0]) & (df_sensor['timestamp'] < _range[1])]
            df_sensor_calc = pd.concat([df_sensor_calc, df_sub_sensor], ignore_index=True)

        mean_humidity = df_sensor_calc['humidity'].mean()
        print('MEAN HUMIDITY: ', mean_humidity)
        if mean_humidity > HUMIDITY_THRESHOLD:
            return True
        else:
            return False

    # In case no event OFF -> use all domain from start_time to end_time
    else:
        if last_power_status:
            new_start_time = start_time
            new_end_time = end_time
        else:
            if df_activities.empty:
                new_start_time = start_time
            else:
                new_start_time = df_activities.iloc[0]['timestamp']
            new_end_time = end_time

        df_sensor = df_sensor[
            (df_sensor['timestamp'] >= new_start_time) & (df_sensor['timestamp'] <= new_end_time)
        ]

        mean_humidity = df_sensor['humidity'].mean()
        print('MEAN HUMIDITY: ', mean_humidity)
        if mean_humidity > HUMIDITY_THRESHOLD:
            return True
        else:
            return False


def abnormal_power(
        df_energy: pd.DataFrame,
        df_activities: pd.DataFrame
):
    # Collect ALL ACTIVITIES POWER ON, including set temperature, and TURN ON AC
    activities_ON = np.where(df_activities['power'] == True)[0]
    activities_turn_ON = []

    # Filter TURN ON ACTIVITIES
    for idx in activities_ON:
        # If this is the first activity of day -> pass
        if idx == 0:
            pass
        else:
            # If this is not the first activity -> check the previous, if it's ON -> Continue
            if df_activities.iloc[idx - 1]['power']:
                continue

        df_temp = df_energy[df_energy['timestamp'] <= df_activities.iloc[idx]['timestamp']]
        if not df_temp.empty:
            if df_temp['power'].iloc[-1] < 100:
                activities_turn_ON.append(idx)

    activities_ON, activities_turn_ON = list(set(activities_ON).difference(activities_turn_ON)), list(
        set(activities_turn_ON).difference(activities_ON))

    # Drop some set temperature activities; Keep the TURN ON and TURN OFF activities
    df_activities = df_activities.drop(index=activities_ON).reset_index(drop=True)

    for idx in range(len(df_activities)):

        collect_time = df_activities.iloc[idx]['timestamp']
        df_sub_energy = df_energy[(df_energy['timestamp'] >= collect_time) & (
                    df_energy['timestamp'] <= collect_time + pd.to_timedelta(5, 'm'))]

        print(df_sub_energy)
        print('[DEBUG] AVG POWER: ', df_sub_energy['power'].mean())
        print('-------------------')

        if df_activities.iloc[idx]['power']:
            if df_sub_energy['power'].mean() < POWER_THRESHOLD:
                return True
            else:
                continue
        else:
            if df_sub_energy['power'].mean() > POWER_THRESHOLD:
                return True
            else:
                continue

    return False

