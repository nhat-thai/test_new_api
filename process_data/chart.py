import os
from typing import List

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import datetime
import seaborn as sns
import pandas as pd

from process_data.utils import *
from process_data.extract_user_data import extract_energy_data

alpha = [1, 0.8, 0.6]


# Draw chart
# Basic chart
def export_chart(
    bg_dir,
    device_id,
    device_name,
    df_sensor,
    df_energy,
    df_activities: pd.DataFrame,
    date,
):
    track_day = "{}-{:02d}-{:02d}".format(date.year, date.month, date.day)

    fig, axs = plt.subplots(3, 1, sharex=True, facecolor="w", figsize=(15, 12))

    # Remove horizontal space between axes
    fig.subplots_adjust(hspace=0.05)

    # Adding grid line
    axs[0].grid(linestyle="--", alpha=0.5)
    axs[1].grid(linestyle="--", alpha=0.5)
    axs[2].grid(linestyle="--", alpha=0.5)

    # Set time limit in one day
    axs[0].set_xlim([date, date + datetime.timedelta(days=1)])

    # Set timestamp display format HH:MM
    # For each xticks, it'll display for each hours of 1 day, respectively
    axs[0].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    axs[0].xaxis.set_major_locator(mdates.HourLocator(interval=1))

    # Plot each graph, and manually set the y tick values
    """ Plot Energy and Power """
    p1 = axs[0].plot(
        df_energy["timestamp"],
        df_energy["energy"],
        color="blue",
        alpha=0.3,
        label="energy",
    )
    axs[0].fill_between(
        df_energy["timestamp"],
        df_energy["energy"],
        df_energy["energy"].min(),
        where=df_energy["energy"] > df_energy["energy"].min(),
        color="blue",
        label="energy",
        alpha=0.1,
        animated=True,
        hatch=".",
        facecolor="w",
    )
    axs[0].set_ylabel("Electricity Index (Wh)", fontsize=14)

    ax1 = axs[0].twinx()
    if df_energy["power"].max() < 1500:
        ax1.set_ylim([0, 1500])

    p2 = ax1.plot(
        df_energy["timestamp"], df_energy["power"], color="red", label="power"
    )
    ax1.set_ylabel("Power (Watt)", fontsize=14)

    if df_sensor["temperature"].min() > 20 and df_sensor["temperature"].max() < 32:
        axs[1].set_ylim([20, 32])

    axs[1].plot(
        df_sensor["timestamp"],
        df_sensor["temperature"],
        color="green",
        label="temperature",
    )
    axs[1].set_ylabel(r"Temperature ($^{\circ}C$)", fontsize=14)

    if df_sensor["humidity"].min() > 40 and df_sensor["humidity"].max() < 70:
        axs[2].set_ylim([40, 70])

    axs[2].plot(
        df_sensor["timestamp"], df_sensor["humidity"], color="y", label="humidity"
    )
    axs[2].set_ylabel("Humidity (%)", fontsize=14)

    p = p1 + p2
    labs = [plot.get_label() for plot in p]

    for i in range(len(df_activities)):
        axs[0].axvline(
            x=df_activities["timestamp"].iloc[i],
            label="activity" + str(i),
            alpha=0.5,
            color="navy",
        )
        axs[1].axvline(
            x=df_activities["timestamp"].iloc[i],
            label="activity" + str(i),
            alpha=0.5,
            color="navy",
        )
        axs[2].axvline(
            x=df_activities["timestamp"].iloc[i],
            label="activity" + str(i),
            alpha=0.5,
            color="navy",
        )

        flag_sch = False
        if df_activities["event_type"].iloc[i] == "update_scheduler":
            control = "UpSch_" + str(i)
            flag_sch = True
        elif df_activities["event_type"].iloc[i] == "add_scheduler":
            control = "AddSch_" + str(i)
            flag_sch = True
        elif df_activities["event_type"].iloc[i] == "delete_scheduler":
            control = "DelSch_" + str(i)
            flag_sch = True
        elif df_activities["event_type"].iloc[i] == "remote_control":
            control = "Remote_" + str(i)
        elif (
            df_activities["event_type"].iloc[i] == "set_temperature"
            or df_activities["event_type"].iloc[i] == "set_operation_mode"
        ):
            control = "App_" + str(i)
        elif df_activities["event_type"].iloc[i] == "scheduler_control":
            control = "Sche_" + str(i)
        else:
            control = "App_" + str(i)

        if df_activities["power"].iloc[i]:
            power = "ON"
            temp = str(int(df_activities["temperature"].iloc[i]))
        else:
            power = "OFF"
            temp = "--"

        if not flag_sch:
            act_info = """{}\n{}\n{}\n{}??C\nfan_{}
                """.format(
                power,
                control,
                df_activities["operation_mode"].iloc[i],
                temp,
                int(df_activities["fan_speed"].iloc[i]),
            )
        else:
            act_info = control

        axs[2].text(
            ((df_activities["timestamp"].iloc[i] - date).total_seconds() - 900) / 86400,
            -1.15,
            act_info,
            horizontalalignment="left",
            verticalalignment="top",
            transform=axs[1].transAxes,
            bbox={"alpha": 1, "pad": 2, "facecolor": "w"},
        )

    axs[0].text(
        0,
        1.2,
        "Device name: ",
        color="black",
        transform=axs[0].transAxes,
        fontsize=20,
    )
    axs[0].text(
        0,
        1.05,
        "ENERGY CONSUMPTION ("
        + track_day
        + "): "
        + str(get_energy_consumption(df_energy) / 1000)
        + " kWh",
        color="black",
        transform=axs[0].transAxes,
        fontsize=20,
    )

    axs[0].legend(p1 + p2, labs, loc=0)
    is_exist = os.path.exists(bg_dir)
    if not is_exist:
        os.makedirs(bg_dir)

    # fig.savefig(f"{bg_dir}/chart_{device_name[device_id]}.png")
    fig.savefig(f"{bg_dir}/chart_{device_name[device_id]}.png")
    plt.close()
    # plt.show()


## Energy Pie chart
def func(pct):
    return "{:.1f}%".format(pct)


def export_energy_pie_chart(
    bg_dir: str,
    device_list: List[str],
    energy_list: List[float],
    total_energy_consumption: float,
    device_name,
    track_day: str,
):
    # Assign label with device name
    label = []
    for device_id in device_list:
        label.append(device_name[device_id])

    # Wedge properties
    wp = {"linewidth": 2, "edgecolor": "black", "alpha": 0.75}

    fig, ax = plt.subplots(figsize=(8, 5), facecolor="w")
    wedges, texts, autotexts = ax.pie(
        energy_list,
        autopct=lambda pct: func(pct),
        startangle=90,
        wedgeprops=wp,
        textprops={"fontsize": 12},
    )

    label_list = []
    idx = 0
    for lab in label:
        label_list.append(lab + " (" + str(np.round(energy_list[idx])) + " kWh)")
        idx += 1

    # Adding legend
    ax.legend(
        wedges,
        label_list,
        title="Device List",
        loc="center right",
        bbox_to_anchor=(1, 0.5),
        fontsize=12,
        bbox_transform=plt.gcf().transFigure,
    )

    plt.setp(autotexts, size=12, weight="bold")

    total_energy_consumption = np.round(total_energy_consumption, 1)
    title = ax.set_title(
        f"Total Energy Consumption ({track_day}): "
        + r"$\bf{"
        + str(total_energy_consumption)
        + "} kWh$",
        fontsize=15,
        color="green",
    )
    title.set_ha("left")

    plt.subplots_adjust(left=0.0, bottom=0.1, right=0.45)
    plt.savefig(f"{bg_dir}/EnergyPieChart.png")
    plt.close()


def export_last_3_days_working_time(
        token: str,
        bg_dir: str,
        user_id: str,
        device_list: List[str],
        device_name,
        track_day: str
):
    date1 = pd.to_datetime(track_day)
    date2 = date1 - datetime.timedelta(days=1)
    date3 = date1 - datetime.timedelta(days=2)

    track_day_2 = "{}-{:02d}-{:02d}".format(date2.year, date2.month, date2.day)
    track_day_3 = "{}-{:02d}-{:02d}".format(date3.year, date3.month, date3.day)

    e = [[], [], []]
    t = [[], [], []]
    label = []

    for device_id in device_list:
        df_energy_1 = extract_energy_data(token, user_id, device_id, track_day)
        df_energy_2 = extract_energy_data(token, user_id, device_id, track_day_2)
        df_energy_3 = extract_energy_data(token, user_id, device_id, track_day_3)

        ec1 = get_energy_consumption(df_energy_1) / 1000
        ec2 = get_energy_consumption(df_energy_2) / 1000
        ec3 = get_energy_consumption(df_energy_3) / 1000

        wt1 = get_working_time(df_energy_1) / 3600
        wt2 = get_working_time(df_energy_2) / 3600
        wt3 = get_working_time(df_energy_3) / 3600

        if not np.isnan(ec1):
            e[0].append(ec1)
        else:
            e[0].append(0)

        if not np.isnan(ec2):
            e[1].append(ec2)
        else:
            e[1].append(0)

        if not np.isnan(ec3):
            e[2].append(ec3)
        else:
            e[2].append(0)

        if not np.isnan(wt1):
            t[0].append(wt1)
        else:
            t[0].append(0)

        if not np.isnan(wt2):
            t[1].append(wt2)
        else:
            t[1].append(0)

        if not np.isnan(wt3):
            t[2].append(wt3)
        else:
            t[2].append(0)

        label.append(device_name[device_id])

    df_energy_consumption = pd.DataFrame(
        {"Device Name": label, "Last 2 days": e[2], "Yesterday": e[1], "Today": e[0]}
    )

    df_working_time = pd.DataFrame(
        {"Device Name": label, "Last 2 days": t[2], "Yesterday": t[1], "Today": t[0]}
    )

    df_energy_consumption = pd.melt(
        df_energy_consumption,
        id_vars="Device Name",
        var_name="Track Day",
        value_name="Energy Consumption (kWh)",
    )
    df_working_time = pd.melt(
        df_working_time,
        id_vars="Device Name",
        var_name="Track Day",
        value_name="Working Time (Hours)",
    )

    fig, axs = plt.subplots(2, 1, sharex=True, figsize=(12, 10))
    fig.subplots_adjust(hspace=0.05)

    axs[0].yaxis.grid(linestyle="--", alpha=0.5, color="gray", zorder=0)
    axs[1].yaxis.grid(linestyle="--", alpha=0.5, color="gray", zorder=0)

    g = sns.barplot(
        ax=axs[0],
        x="Device Name",
        y="Energy Consumption (kWh)",
        hue="Track Day",
        data=df_energy_consumption,
        color="green",
        zorder=3,
    )
    for al, bar in zip(alpha, axs[0].containers[0]):
        bar.set_alpha(alpha=al)
    axs[0].get_legend().remove()

    g.set(xlabel=None)
    ax = axs[0]

    idx = [i + 1 for i in range(len(device_list) * 3)]

    for index, p in zip(idx, ax.patches):
        if index >= len(device_list) * 2 + 1:
            axs[0].text(
                p.get_x() + p.get_width() / 2.0,
                p.get_height(),
                "%.1f" % p.get_height(),
                fontsize=10,
                color="red",
                ha="center",
                va="bottom",
            )

    axs[1].set_ylim(0, 25)
    sns.barplot(
        ax=axs[1],
        x="Device Name",
        y="Working Time (Hours)",
        hue="Track Day",
        data=df_working_time,
        color="green",
        zorder=3,
    )
    for al, bar in zip(alpha, axs[1].containers[0]):
        bar.set_alpha(alpha=al)

    ax = axs[1]
    for index, p in zip(idx, ax.patches):
        if index >= len(device_list) * 2 + 1:
            working_hour = p.get_height()
            hour = int(working_hour)
            minute = int((p.get_height() - hour) * 60)
            time_display = "{:02d}:{:02d}".format(hour, minute)

            axs[1].text(
                p.get_x() + p.get_width() / 2.0,
                p.get_height(),
                time_display,
                fontsize=10,
                color="red",
                ha="center",
                va="bottom",
            )

    plt.xticks(rotation=30)
    plt.legend(fontsize=10)

    axs[0].set_title(
        f"Energy and Working Hour of the last 3 days - from {track_day_3} to {track_day}",
        fontsize=14,
        color="green",
    )

    plt.savefig(f"{bg_dir}/Last3DaysChart.png")
    plt.close()
