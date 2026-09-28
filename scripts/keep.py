#!/usr/bin/python
# -*- coding: UTF-8 -*-
import argparse
import os
from dotenv import load_dotenv
import pendulum
from notion_helper import NotionHelper
import requests
import utils
from config import workout_properties_type_dict
LOGIN_API = "https://api.gotokeep.com/v1.1/users/login"
RUN_DATA_API = "https://api.gotokeep.com/pd/v3/stats/detail?dateUnit=all&type=running&lastDate={last_date}"
RUN_LOG_API = "https://api.gotokeep.com/pd/v3/runninglog/{run_id}"

keep_headers = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0",
    "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
}
load_dotenv()

def login():
    mobile = os.getenv("KEEP_MOBILE")
    password = os.getenv("KEEP_PASSWORD")
    data = {"mobile": mobile, "password": password}
    r = requests.post(LOGIN_API, headers=keep_headers, data=data)
    if r.ok:
        print("登录成功")
        token = (r.json().get("data") or {}).get("token")
        keep_headers["Authorization"] = f"Bearer {token}"
        return get_run_id()
    else:
        print(r.text)
        return None


def get_run_id():
    last_date = 0
    results = []
    while 1:
        r = requests.get(RUN_DATA_API.format(
            last_date=last_date), headers=keep_headers)
        if r.ok:
            last_date = (r.json().get("data") or {}).get("lastTimestamp")
            records = (r.json().get("data") or {}).get("records") or []
            logs = [item.get("stats") for sublist in records for item in sublist['logs']]
            for log in logs:
                if log.get("id")==latest_id:
                    return results
                else:
                    results.append(log)
        print(f"last date = {last_date}")
        if not last_date:
            break
    return results


def get_lastest():
    sorts=[
        {
            "property": "结束时间",
            "direction": "descending"
        }
    ]
    response = notion_helper.query(database_id=notion_helper.workout_database_id, sorts=sorts,page_size=1)
    results = response.get("results")
    if len(results)>0:
        return utils.get_property_value(response.get("results")[0].get("properties").get("Id"))
    else:
        return None





def get_run_data(id,name):
    r = requests.get(RUN_LOG_API.format(run_id=id), headers=keep_headers)
    if r.ok:
        workout = {}
        data = r.json().get("data")
        end_time = pendulum.from_timestamp(data.get("endTime")/1000, tz="Asia/Shanghai")
        workout["标题"] = end_time.to_datetime_string()
        workout["名字"] = name
        workout["Id"] = id
        workout["开始时间"] = data.get("startTime")/1000
        workout["结束时间"] = data.get("endTime")/1000
        workout["距离"] = round(data.get("distance"))
        workout["运动时长"] = data.get("duration")
        workout["平均配速"] = data.get("averagePace")
        workout["消耗热量"] = data.get("calorie")
        heartRate= data.get("heartRate")
        if heartRate:
            workout["平均心率"] = heartRate.get("averageHeartRate")
            workout["最大心率"] = heartRate.get("maxHeartRate")
        end_time = pendulum.from_timestamp(data.get("endTime")/1000, tz="Asia/Shanghai")
        cover= data.get("shareImg")
        add_to_notion(workout,end_time,cover)

def add_to_notion(workout,end_time,cover):
    properties = utils.get_properties(workout, workout_properties_type_dict)
    notion_helper.get_date_relation(properties,end_time)
    parent = {
        "database_id": notion_helper.workout_database_id,
        "type": "database_id",
    }
    icon = {"type": "emoji", "emoji": "🏃🏻"}
    #封面长图有限制
    if cover and len(cover) <=2000:
        pass
    else:
        cover = utils.upload_cover(cover)
        if cover is None:
            cover="https://images.unsplash.com/photo-1547483238-f400e65ccd56?q=80&w=2970&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
    notion_helper.create_page(
        parent=parent, properties=properties,cover=utils.get_icon(cover), icon=icon
    )



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    notion_helper=NotionHelper()
    latest_id = get_lastest()
    print(f"latest_id = {latest_id}")
    logs = login()
    if logs:
        #按照结束时间倒序排序
        logs = sorted(logs, key=lambda x: x['endTime'])
        for log in logs:
            id = log.get("id")
            name = log.get("name")
            print(f"id = {id} {name}")
            if id == latest_id:
                break
            get_run_data(id,name)