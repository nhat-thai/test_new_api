import os
from typing import List, Dict, Any

import numpy as np
import pandas as pd
from flask import Response, jsonify
import io
from matplotlib.figure import Figure
from google.cloud import storage
import shutil
import pytz

import smtplib
from xhtml2pdf import pisa
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText

from bkreport import BenKonReport, BenKonReportData, ACActivity
from process_data.extract_user_data import *
from process_data.chart import *
from api.device_info.controllers import *

power = {True: "ON", False: "OFF", None: "Không có"}
local_chart_dir = os.path.join(os.getcwd(), "/tmp/chart")
local_report_dir = os.path.join(os.getcwd(), "/tmp/report")


def convert_html_to_pdf(source_html: str, output_filename: str) -> int:
    # convert HTML to PDF
    result_file = open(output_filename + "summary.pdf", "w+b")
    pisa_status = pisa.CreatePDF(
        source_html.encode("utf-8"), dest=result_file, encoding="utf-8",
    )  # file handle to recieve result
    result_file.close()

    # return False on success and True on errors
    return pisa_status.err


def upload_to_bucket(blob_name: str, path_to_file: str, bucket_name: str) -> str:
    """ Upload data to a bucket"""
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(path_to_file)

    return blob.public_url


def get_username_dict(df_info: pd.DataFrame) -> Dict[Any, Any]:
    # Convert user_id and user_name to dict type
    df_username = df_info[["user_id", "user_name"]]
    df_username = df_username.drop_duplicates().reset_index(drop=True)
    username = dict(zip(df_username["user_id"], df_username["user_name"]))
    return username


def get_username(df_info: pd.DataFrame, user_id: str) -> str:
    return df_info[df_info["user_id"] == user_id]["user_name"].iloc[0]


def get_device_name(df_info: pd.DataFrame) -> Dict[Any, Any]:
    # Convert device_id and device_name to dict type
    df_device_name = df_info[df_info["status"] == 1]
    df_device_name = df_device_name[["device_id", "device_name"]]
    df_device_name = df_device_name.drop_duplicates().reset_index(drop=True)
    device_name = dict(zip(df_device_name["device_id"], df_device_name["device_name"]))
    return device_name


def get_device_list(df_info: pd.DataFrame, user_id: str) -> List[str]:
    df_device_list = df_info[(df_info["user_id"] == user_id) & df_info["status"] == 1]
    return df_device_list["device_id"].tolist()


def get_df_info():
    records = get_device_info()
    df_info = pd.DataFrame(
        records,
        columns=[
            "no",
            "customer_id",
            "customer_name",
            "user_id",
            "user_name",
            "device_id",
            "device_name",
            "status",
            "outdoor_unit",
        ],
    )
    return df_info


def gen_report(
    token: str,
    df_info: pd.DataFrame,
    user_id: str,
    track_day: str,
    folder_id: str = "",
    df_house: pd.DataFrame = pd.DataFrame(),
) -> None:

    if df_house.empty:
        username = get_username(df_info, user_id)
        device_name = get_device_name(df_info)
        device_id_list = get_device_list(df_info, user_id)
    else:
        username = df_house["name"].iloc[0]
        device_name = dict(zip(df_house["device_id"], df_house["alias"]))
        device_id_list = df_house["device_id"].to_list()

    energy_list = []
    device_list = []
    data = []

    # if os.path.exists(local_chart_dir):
    #     shutil.rmtree(local_chart_dir)

    unix_time = convert_to_unix_timestamp(track_day)

    os.makedirs(local_chart_dir, exist_ok=True)
    for device_id in device_id_list:
        print(device_name[device_id])

        date = pd.to_datetime(track_day)

        df_sensor, df_energy, df_activities = extract_user_data(
            token=token,
            user_id=user_id,
            device_id=device_id,
            track_day=track_day
        )

        if (df_sensor.empty and df_energy.empty) or np.isnan(df_energy["energy"].min()):
            pass
        else:
            if (not np.isnan(get_energy_consumption(df_energy))) and (
                get_energy_consumption(df_energy) > 1000
            ):
                energy_list.append(get_energy_consumption(df_energy) / 1000)
                device_list.append(device_id)

            export_chart(
                local_chart_dir,
                device_id,
                device_name,
                df_sensor,
                df_energy,
                df_activities,
                date
            )

        # Load AC's activities to list
        activities = []
        for i in range(len(df_activities)):

            # Convert time
            _time = df_activities["timestamp"].iloc[i]
            act_time = "{:02d}:{:02d}:{:02d}".format(
                _time.hour, _time.minute, _time.second
            )

            # If event_type relates to scheduler
            if df_activities["event_type"].iloc[i] == "delete_scheduler":
                row_act = ACActivity(
                    type=df_activities["event_type"].iloc[i],
                    power_status=power[df_activities["power"].iloc[i]],
                    op_mode="Không có",
                    op_time=act_time,
                    configured_temp="Không có",
                    fan_speed="Không có",
                )
            else:

                # Fan Speed
                if df_activities["fan_speed"].iloc[i] == 7:
                    fan_speed = "Auto"
                else:
                    fan_speed = str(int(df_activities["fan_speed"].iloc[i]))

                # Temperature
                if power[df_activities["power"].iloc[i]] in ["OFF", "Không có"]:
                    configured_temp = "-- °C"
                else:
                    configured_temp = (
                        str(int(df_activities["temperature"].iloc[i])) + "°C"
                    )

                row_act = ACActivity(
                    type=df_activities["event_type"].iloc[i],
                    power_status=power[df_activities["power"].iloc[i]],
                    op_mode=df_activities["operation_mode"].iloc[i],
                    op_time=act_time,
                    configured_temp=configured_temp,
                    fan_speed=fan_speed,
                )
            activities.append(row_act)

        # Get chart URL
        chart_url = f"{local_chart_dir}/chart_{device_name[device_id]}.png"
        if not os.path.exists(chart_url):
            chart_url = ""

        print('[DEBUG] CHART URL: ', chart_url)

        # Gen report's page for each device
        data_report = BenKonReportData(
            user=username,
            device=device_name[device_id],
            report_date=pd.to_datetime(track_day),
            chart_url=chart_url,
            energy_kwh=np.round(get_energy_consumption(df_energy) / 1000, 3),
            activities=activities,
        )
        data.append(data_report)

    total_energy_consumption = float(np.sum(energy_list))
    if len(device_list) <= 8:
        pass
    else:
        df = pd.DataFrame(
            data=zip(device_list, energy_list),
            columns=["device_id", "energy_consumption"],
        )
        df = df.sort_values(by="energy_consumption", ascending=False).reset_index(
            drop=True
        )
        device_list = df.iloc[:8]["device_id"].to_list()
        energy_list = df.iloc[:8]["energy_consumption"].to_list()

    # Summary page information
    if len(energy_list) == 0 or len(device_list) == 0:
        # Không có device nào có năng lượng
        isGenSummaryPage = False
        pass
    else:
        isGenSummaryPage = True

        print(energy_list)

        export_energy_pie_chart(
            local_chart_dir,
            device_list,
            energy_list,
            total_energy_consumption,
            device_name,
            track_day,
        )

        export_last_3_days_working_time(
            token,
            local_chart_dir,
            user_id,
            device_list,
            device_name,
            track_day
        )

    # Check if pie chart is exists
    url_pie_chart = f"{local_chart_dir}/EnergyPieChart.png"
    if not os.path.exists(url_pie_chart):
        url_pie_chart = ""

    # Check if bar chart is exists
    url_bar_chart = f"{local_chart_dir}/Last3DaysChart.png"
    if not os.path.exists(url_bar_chart):
        url_bar_chart = ""

    os.makedirs(f"{local_report_dir}", exist_ok=True)

    year, month, day = track_day.split("-")
    filename = f"BenKon Daily Report.pdf"
    filepath = f"reports/{user_id}/{year}/{month}/{day}/{filename}"
    os.makedirs(filepath, exist_ok=True)

    local_pdf = f"{filepath}/BenKon_Daily_Report.pdf"

    BenKonReport(
        f"{local_pdf}",
        isGenSummaryPage=isGenSummaryPage,
        url_pie_chart=url_pie_chart,
        url_bar_chart=url_bar_chart,
        data=data,
    )


