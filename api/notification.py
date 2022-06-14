import copy
import os

import numpy as np
import pandas as pd

from bkreport import BenKonReport, BenKonReportData, ACActivity
from process_data.chart import *
from process_data.extract_user_data import *
from process_data.utils import get_working_time, get_energy_consumption
from api.utils import *
from api.abnormal_detect import abnormal_humidity, abnormal_power


def get_notifications_content(
        token: str,
        df_info: pd.DataFrame,
        user_id: str,
        track_day: str,
):
    username = get_username(df_info, user_id)
    device_name = get_device_name(df_info)
    device_id_list = get_device_list(df_info, user_id)

    print(username)

    ####################################################
    """
        INITIALIZE SUMMARY CONTENT
    """
    content_BAS = ""
    content_overview = ""
    content_out_of_working_time = ""
    content_summary = ""
    content_abnormal = ""

    content_overview_list = []
    out_of_working_time_list = []
    list_abnormal_devices = []
    avg_cnt_max = 0

    total_energy_consumption = 0
    total_energy_consumption_avg_7_days = 0

    working_time = {"start_time": 6.25, "end_time": 22.75}

    start_time = pd.to_datetime(track_day) + pd.to_timedelta(
        working_time.get("start_time"), "H"
    )
    end_time = pd.to_datetime(track_day) + pd.to_timedelta(
        working_time.get("end_time"), "H"
    )

    print("START TIME:", start_time)
    print("END TIME:", end_time)

    """
        END INITIALIZE SUMMARY CONTENT
    """

    for device_id in device_id_list:
        print(device_name[device_id])

        df_sensor, df_energy, df_activities = extract_user_data(
            token=token,
            user_id=user_id,
            device_id=device_id,
            track_day=track_day
        )

        ##################################################
        """
            GENERATE SUMMARY PROCESS
        """
        """ ======================================================================================= """
        # TOTAL ENERGY CONSUMPTION AND WORKING HOURS

        energy_consumption = get_energy_consumption(df_energy) / 1000
        total_energy_consumption_7_days = 0

        if not np.isnan(energy_consumption):
            total_energy_consumption += energy_consumption

        # 7 days ago
        history_track_day = (
            pd.to_datetime(track_day) - pd.to_timedelta(7, "D")
        ).strftime("%Y-%m-%d")
        history_date = pd.to_datetime(history_track_day)

        avg_cnt = 0
        cnt = 7
        while history_date <= pd.to_datetime(
            (pd.to_datetime(track_day) - pd.to_timedelta(1, "D")).strftime("%Y-%m-%d")
        ):
            df_energy_history = extract_energy_data(
                token=token,
                user_id=user_id,
                device_id=device_id,
                track_day=history_track_day
            )

            energy_consumption_history = get_energy_consumption(df_energy_history)
            if (
                not np.isnan(energy_consumption_history)
                and energy_consumption_history > 1000
            ):
                avg_cnt += 1
                total_energy_consumption_7_days += (energy_consumption_history / 1000)

            history_date += pd.to_timedelta(1, "D")
            history_track_day = history_date.strftime('%Y-%m-%d')
            cnt -= 1

        if total_energy_consumption_7_days > 1:
            total_energy_consumption_avg_7_days += (total_energy_consumption_7_days / avg_cnt)
            if avg_cnt_max < avg_cnt:
                avg_cnt_max = avg_cnt

        """ ======================================================================================= """

        """ ======================================================================================= """
        # OVERVIEW
        df_activities_overview = df_activities.drop(
            df_activities[df_activities["event_type"] == "update_scheduler"].index
        )

        # Locate the index of scheduler_control event
        scheduler_control_index = df_activities_overview.iloc[
            np.where(df_activities_overview["event_type"] == "scheduler_control")[0]
        ].index
        # Total time working under 24 degree Celsius
        total_time = 0
        # Check point for each point which under 24 degree Celsius
        checkPoint = False

        checkPoint_time = 0
        for idx in range(len(df_activities_overview)):
            if idx not in scheduler_control_index:
                if df_activities_overview.iloc[idx]["temperature"] <= 24:
                    if not checkPoint:
                        checkPoint_time = df_activities_overview.iloc[idx]["timestamp"]
                        checkPoint = True
                    else:
                        continue
                else:
                    if checkPoint:
                        total_time += (
                            df_activities_overview.iloc[idx]["timestamp"]
                            - checkPoint_time
                        ).total_seconds()
                        checkPoint_time = df_activities_overview.iloc[idx]["timestamp"]
                        checkPoint = False
                    else:
                        continue
            else:
                if checkPoint:
                    total_time += (
                        df_activities_overview.iloc[idx]["timestamp"] - checkPoint_time
                    ).total_seconds()
                    checkPoint_time = df_activities_overview.iloc[idx]["timestamp"]
                    checkPoint = False
                else:
                    continue

        hour = int(np.floor(total_time / 3600))
        minute = int(int(total_time - 3600 * hour) / 60)
        _time = f"{hour} giờ {minute} phút"

        if total_time > 30 * 60:
            content_overview_list.append((username, device_name[device_id], _time))
        """ ======================================================================================= """

        """ ======================================================================================= """
        # RUN OUT OF WORKING TIME
        df_outRange_1 = df_energy[df_energy["timestamp"] <= start_time]
        df_outRange_2 = df_energy[df_energy["timestamp"] >= end_time]

        df_outRange_1 = df_outRange_1[df_outRange_1["power"] >= 100]
        df_outRange_2 = df_outRange_2[df_outRange_2["power"] >= 100]

        def process_outRange(df):
            _idx = 0

            print(df)

            while _idx < len(df):
                st = df.iloc[_idx]["timestamp"].strftime("%H:%M")

                while _idx < len(df) - 1:
                    if (
                        df.iloc[_idx + 1]["timestamp"] - df.iloc[_idx]["timestamp"]
                    ).total_seconds() >= 30 * 60:
                        break
                    else:
                        _idx += 1

                et = df.iloc[_idx]["timestamp"].strftime("%H:%M")

                print(et, " ", st)

                delta_time = (pd.to_datetime(et) - pd.to_datetime(st)).total_seconds()
                _hour = int(delta_time // 3600)
                _minute = int((delta_time // 60) % 60)
                delta_time_full_text = f"{_hour} giờ {_minute} phút"

                out_of_working_time_list.append(
                    (device_name[device_id], st, et, delta_time_full_text)
                )

                _idx += 1

        process_outRange(df_outRange_1)
        process_outRange(df_outRange_2)
        """ ======================================================================================= """

        """ ======================================================================================= """
        # ABNORMAL DEVICE CHECK
        if abnormal_humidity(
            df_sensor=df_sensor,
            df_energy=df_energy,
            df_activities=df_activities,
            track_day=track_day,
            start_working_time=6.5,
            end_working_time=22,
        ) or abnormal_power(df_energy=df_energy, df_activities=df_activities):
            list_abnormal_devices.append(device_name[device_id])
        """ ======================================================================================= """

        """ ======================================================================================= """
        # OVERWRITE BAS
        # AC_overwrite_BAS = f"""
        #         <table>
        #         <tbody>
        #             <th>Thời gian bắt đầu ghi đè</th>
        #             <th>Nhiệt độ</th>
        #             <th>Thời lượng ghi đè</th>
        #         """
        #
        # df_activities_BAS = df_activities.drop(df_activities[df_activities['event_type'] == 'update_scheduler'].index)
        #
        # # Locate the index of scheduler_control event
        # scheduler_control_index = df_activities_BAS.iloc[np.where(df_activities_BAS['event_type'] == 'scheduler_control')[0]].index
        # # Variable for counting the number of activities that overwritten the BAS
        # total_overwrite_BAS = 0
        # # Scheduler_flag for checking the first scheduler_control of the day
        # scheduler_flag = False
        #
        # # Loop for all activities
        # for idx in range(len(df_activities_BAS)):
        #
        #     # If this is the scheduler_control event
        #     if idx in scheduler_control_index:
        #         if idx - 1 in scheduler_control_index:
        #             continue
        #
        #         # If it is not the FIRST scheduler_control event
        #         if scheduler_flag:
        #             # Take the information of the last control
        #             _time = df_activities_BAS.iloc[idx - 1]['timestamp'].strftime('%H:%M')
        #             temp_config = df_activities_BAS.iloc[idx - 1]['temperature']
        #             duration = (df_activities_BAS.iloc[idx]['timestamp'] - df_activities_BAS.iloc[idx - 1]['timestamp']).total_seconds()
        #             hour = int(np.floor(duration / 3600))
        #             minute = int(int(duration - 3600 * hour) / 60)
        #             duration_str = '{:02d} tiếng {:02d} phút'.format(hour, minute)
        #             AC_overwrite_BAS += f"""
        #                                     <tr>
        #                                         <td>{_time}</td>
        #                                         <td>{int(temp_config)}°C</td>
        #                                         <td>{duration_str}</td>
        #                                     </tr>
        #                                 """
        #         else:
        #             # Toggle the flag
        #             scheduler_flag = True
        #     # Trong trường hợp không phải là scheduler control
        #     else:
        #         if scheduler_flag:
        #             # Increase the number of overwrite-BAS activities
        #             total_overwrite_BAS += 1
        #
        #             # If the activities before is scheduler_control
        #             if idx - 1 in scheduler_control_index:
        #                 continue
        #             else:
        #                 _time = df_activities_BAS.iloc[idx - 1]['timestamp'].strftime('%H:%M')
        #                 temp_config = df_activities_BAS.iloc[idx - 1]['temperature']
        #                 duration = (df_activities_BAS.iloc[idx]['timestamp'] - df_activities_BAS.iloc[idx - 1]['timestamp']).total_seconds()
        #                 hour = int(np.floor(duration / 3600))
        #                 minute = int(int(duration - 3600 * hour) / 60)
        #                 duration_str = '{:02d} tiếng {:02d} phút'.format(hour, minute)
        #                 AC_overwrite_BAS += f"""
        #                                         <tr>
        #                                             <td>{_time}</td>
        #                                             <td>{temp_config}</td>
        #                                             <td>{duration_str}</td>
        #                                         </tr>
        #                                     """
        #         else:
        #             continue
        #
        # AC_overwrite_BAS += f"""
        #                         </tbody>
        #                     </table>
        #                     <br>
        #                     """
        #
        # if total_overwrite_BAS > 0:
        #     content_BAS += f"<h4>Tên thiết bị: {device_name[device_id]} </h4>"
        #     content_BAS += f"<p>Số lần ghi đè của các activities lên tính năng BAS: <b>{total_overwrite_BAS}</b> </p>"
        #     content_BAS += AC_overwrite_BAS
        """ ======================================================================================= """
        """
            END GENERATE SUMMARY PROCESS
        """

    #################################################################
    """
        GENERATE SUMMARY PROCESS
    """
    # Create summary table
    percent_present = total_energy_consumption
    percent_history = total_energy_consumption_avg_7_days

    print(f'PRESENT: {percent_present} - HISTORY: {percent_history}')

    if percent_present >= percent_history:
        color = "#ff0000"
        percent = "+ {:.1f} %".format(
            (percent_present - percent_history) / percent_history * 100
        )
    else:
        color = "#339966"
        percent = "- {:.1f} %".format(
            (percent_history - percent_present) / percent_history * 100
        )

    content_summary += f"""
        <tr>
            <td> {username} </td>
            <td> {np.round(total_energy_consumption, 1)} </td>
            <td> <b><span style="color: {color};"> {percent} </span> </b> </td>
        </tr>
    """

    # Create table overview
    if len(content_overview_list) >= 1:
        content_overview += f"""
        <tr>
            <td rowspan="{len(content_overview_list)}"> {content_overview_list[0][0]} </td>
            <td> {content_overview_list[0][1]} </td>
            <td> {content_overview_list[0][2]} </td>
        </tr>
        """
        if len(content_overview_list) > 1:
            for idx in range(1, len(content_overview_list)):
                content_overview += f"""
                <tr>
                    <td> {content_overview_list[idx][1]} </td>
                    <td> {content_overview_list[idx][2]} </td>
                </tr>
                """

    # Create table out of working hours
    if len(out_of_working_time_list) >= 1:
        content_out_of_working_time += f"""
        <tr>
            <td rowspan="{len(out_of_working_time_list)}"> {username} </td>
            <td> {out_of_working_time_list[0][0]} </td>
            <td> {out_of_working_time_list[0][1]} </td>
            <td> {out_of_working_time_list[0][2]} </td>
            <td> {out_of_working_time_list[0][3]} </td>
        </tr>
        """
        if len(out_of_working_time_list) > 1:
            for idx in range(1, len(out_of_working_time_list)):
                content_out_of_working_time += f"""
                <tr>
                    <td> {out_of_working_time_list[idx][0]} </td>
                    <td> {out_of_working_time_list[idx][1]} </td>
                    <td> {out_of_working_time_list[idx][2]} </td>
                    <td> {out_of_working_time_list[idx][3]} </td>
                </tr>
                """

    if len(list_abnormal_devices) >= 1:
        content_abnormal += f"""
        <tr>
            <td rowspan="{len(list_abnormal_devices)}"> {username} </td>
            <td> {list_abnormal_devices[0]} </td>
        </tr>
        """
        if len(list_abnormal_devices) > 1:
            for idx in range(1, len(list_abnormal_devices)):
                content_abnormal += f"""
                <tr>
                    <td> {list_abnormal_devices[idx]} </td>
                </tr>
                """
    """
        END GENERATE SUMMARY PROCESS
    """

    return (
        content_summary,
        content_overview,
        content_out_of_working_time,
        content_abnormal,
        content_BAS,
    )


def gen_notifications(
        token: str,
        customer_id: str,
        track_day: str,
        mail_list: List[str],
        bcc_list: List[str],
):
    start_time = time.time()

    df_info = get_df_info()

    df_customer = df_info[df_info["customer_id"] == customer_id]
    ids = df_customer["user_id"].drop_duplicates().to_list()

    summary = ""
    overview = ""
    out_of_working_time = ""
    abnormal = ""

    for user_id in ids:

        authorization_user_id(token, user_id)

        (
            content_summary,
            content_overview,
            content_out_of_working_time,
            content_abnormal,
            _,
        ) = get_notifications_content(
            token=token,
            df_info=df_info,
            user_id=user_id,
            track_day=track_day
        )

        summary += content_summary
        overview += content_overview
        out_of_working_time += content_out_of_working_time
        abnormal += content_abnormal

    # DONE -> Complete mail content by merging each part of content

    mail_content = """
            <html>
            <head>
                <meta charset="UTF-8" />
                <style>
                    table, th, td {
                        border: 1px solid black;
                        border-collapse: collapse;
                    }
                    th, td {
                        padding: 5px;
                        text-align: left;  
                        font-size: 12px  
                    }  
                    p {
                        font-size: 15px;
                        font-family: NotoSans;
                    }
                    body {
                        font-family: NotoSansBold;
                    }
                    @font-face {
                        font-family: "NotoSans";
                        src: url('fonts/NotoSans-Regular.ttf');
                    }
                    @font-face {
                        font-family: "NotoSansBold";
                        src: url('fonts/NotoSans-Bold.ttf');
                    }   
                </style>
            </head>
        """

    mail_content += f"""
            <body>
            <p>Đây là email thông báo tự động. Quý khách hàng vui lòng liên hệ nhân viên BenKon để được hỗ trợ tốt nhất. </p>
            
            <h3> 1. Thống kê tại các địa điểm </h3>
            
            <table>
            <tbody>
                <th>Tên địa điểm</th>
                <th>Tổng điện năng tiêu thụ (kWh)</th>
                <th>So với 7 ngày trước</th>
        """
    mail_content += summary
    mail_content += "</tbody></table>"

    mail_content += f"""
            <h3> 2. Thống kê hoạt động điều chỉnh nhiệt độ dưới <b>24°C</b> do nhân viên thực hiện </h3>

            <table>
            <tbody>
                <th>Tên địa điểm</th>
                <th>Tên thiết bị</th>
                <th>Tổng thời lượng điều chỉnh dưới 24°C</th>
        """

    mail_content += overview
    mail_content += "</tbody></table>"

    mail_content += f"""
    <br>

    <h3>3. Thiết bị hoạt động ngoài khung giờ quy định: </h3>
    <table>
        <tbody>
            <th>Tên địa điểm</th>
            <th>Tên thiết bị</th>
            <th>Thời gian bắt đầu</th>
            <th>Thời gian kết thúc</th>
            <th>Thời lượng</th>
    """

    mail_content += out_of_working_time

    mail_content += "</tbody></table>"

    mail_content += f"""
    <h3>4. Thiết bị có khả năng hư hỏng </h3>

    <table>
        <tbody>
            <th>Tên địa điểm</th>
            <th>Tên thiết bị</th>
    """

    mail_content += abnormal

    mail_content += "</tbody></table>"

    mail_content += """
        <br>
        <p>Cám ơn quý khách hàng đã sử dụng dịch vụ Quản lý sử dụng điều hoà hiệu quả của BenKon.</p>
        </body>
        </html>
        """
    pdf_content = mail_content.replace(
        "<p>Đây là email thông báo tự động. Quý khách hàng vui lòng liên hệ nhân viên BenKon để được hỗ trợ tốt nhất. </p>",
        "",
    )
    print(mail_content)

    os.makedirs('./tmp/', exist_ok=True)
    pdf_local_path = "./tmp/summary.pdf"
    convert_html_to_pdf(pdf_content, pdf_local_path)
    year, month, day = track_day.split("-")
    gcs_path = f"summaries/{customer_id}/{year}/{month}/{day}/summary.pdf"
    GCS_BUCKET = os.environ.get("GCS_BUCKET")
    upload_to_bucket(gcs_path, pdf_local_path, GCS_BUCKET)

    print("Total time: ", time.time() - start_time)

