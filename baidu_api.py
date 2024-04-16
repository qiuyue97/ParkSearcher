# encoding:utf-8

import re
from itertools import islice
from shapely.geometry import Point, Polygon
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Thread, Lock
from queue import Queue
import config
import configparser


def parse_coordinates(coordinates_str):
    shape_points = []
    for line in coordinates_str.strip().split('\n'):
        line = line.strip()
        if not line:
            continue  # 跳过空行
        # 使用正则表达式提取经纬度（考虑可能的空格）
        match = re.search(r'(\d+\.\d+)\s*,\s*(\d+\.\d+)', line)
        if match:
            shape_points.append((float(match.group(1)), float(match.group(2))))
        else:
            print(f"无法解析坐标：{line}")
    if len(shape_points) <= 100:
        request_coords = ""
        for coord in shape_points:
            request_coords += str(coord[0]) + ',' + str(coord[1]) + ';'
        url = "https://api.map.baidu.com/geoconv/v2/"
        params = {
            "coords": request_coords[:-1],
            "model": "3",
            "ak": ak,
        }
        response = requests.get(url=url, params=params)
        bd09mc = []
        if response.json()['status'] == 0:
            for result in response.json()['result']:
                bd09mc.append((result['x'], result['y']))
        return bd09mc
    else:
        raise ValueError

def circle_generator(x_min, x_max, y_min, y_max, radius=1000):
    """
    生成器函数，按需生成圆的中心点和位置（上或下）。

    参数:
    - x_min, x_max, y_min, y_max: 矩形参数。
    - radius: 圆的半径。

    返回:
    - 生成下一个圆的中心坐标和位置。
    """
    start_x = x_min
    start_y = y_max - 1
    x = start_x
    y = start_y
    position = 'down'

    while True:
        yield x, y, position
        if x >= x_max:
            # 当前行点已超出范围，另起一行
            next_x = x_min
            next_y = y - radius * (3 if position == 'up' else 2)
            next_position = 'down'
            if next_y <= y_min - 2 * radius:
                # 下一个y超出范围，结束
                break
        else:
            if position == 'down':
                next_x = x + radius
                next_y = y + radius
                next_position = 'up'
            else:
                next_x = x + radius
                next_y = y - radius
                next_position = 'down'

        # 更新当前坐标和位置，准备生成下一个圆的信息
        x, y, position = next_x, next_y, next_position


def requester(location, radius, return_city=False, coordtype="bd09mc"):
    params = {
        "ak": ak,
        "output": "json",
        "coordtype": coordtype,
        "extensions_poi": "1",
        "radius": str(radius),
        "location": location,
    }
    response = requests.get(url="https://api.map.baidu.com/reverse_geocoding/v3", params=params)
    if response.json()['status'] == 0:
        result = response.json()['result']
        yq_pois = [poi for poi in result['pois'] if '园区' in poi['tag']]
        if return_city:
            city = result['addressComponent']['city']
            return pd.json_normalize(yq_pois), city
        else:
            return pd.json_normalize(yq_pois), None
    return None, None


def process_main(circle_info, data_queue, radius):
    x, y = circle_info[:2]
    point = Point(x, y)
    if polygon.contains(point) or point.distance(polygon.exterior) <= 1000:
        location = f"{x},{y}"
        df, _ = requester(location, radius)
        if len(df) != 0:
            data_queue.put(df)


def process_queue(data_queue, result_df, lock, radius):
    all_dfs = []  # 用于收集所有DataFrame对象的列表

    while True:
        df = data_queue.get()
        if df is None:  # 接收到结束信号
            data_queue.task_done()
            break  # 退出循环，进行数据合并和处理

        all_dfs.append(df)  # 添加到列表中
        data_queue.task_done()

    # 在队列处理完毕后进行DataFrame的合并、去重和删除列操作
    if all_dfs:
        with lock:  # 确保线程安全
            # 合并所有DataFrame
            combined_df = pd.concat(all_dfs, ignore_index=True)

            # 删除不需要的列
            columns_to_remove = ["cp", "direction", "distance", "parent_poi.direction", "parent_poi.distance"]
            combined_df.drop(columns=columns_to_remove, errors='ignore', inplace=True)

            # 根据uid去重
            combined_df = combined_df.drop_duplicates(subset=['uid'])
            # 添加城市信息
            final_df = add_city_info(combined_df, radius)

            # 清空result_df并将最终的DataFrame赋值给result_df
            result_df.clear()
            result_df.append(final_df)


def update_progress(current, total):
    progress_percentage = (current / total) * 100
    print(f"\r当前进度: {current}/{total} ({progress_percentage:.2f}%)", end='')


def update_config_check_point(area_name, new_value):
    config_file_path = 'config.py'

    # 打开并读取配置文件
    with open(config_file_path, 'r', encoding='utf-8') as file:
        config_content = file.read()

    # 构建用于定位特定区域check_point值的正则表达式
    # 注意：这里假设area_infos是config.py中唯一的列表字典定义
    pattern = re.compile(
        r'({\s*"area_name"\s*:\s*"' + re.escape(area_name) + r'"[^}]*"check_point"\s*:\s*)(\d+)',
        re.DOTALL
    )

    # 使用正则表达式查找并更新check_point的值
    new_content, count = pattern.subn(r'\g<1>{}'.format(new_value), config_content)

    # 确保我们确实找到并更新了check_point的值
    if count == 0:
        print(
            f"Warning: No check_point updated for area '{area_name}'. Make sure the area_name exists and is correctly spelled.")
    else:
        # 保存更改回配置文件
        with open(config_file_path, 'w', encoding='utf-8') as file:
            file.write(new_content)
        print(f"Updated check_point for area '{area_name}' to {new_value}.")


def add_city_info(df, radius):
    print(f"\n初步request已完成，共找到{len(df)}条园区信息，正在进行二次request...")
    index = 0
    while index < len(df):
        row = df.iloc[index]
        if pd.isna(row.get('city', None)):
            location = f"{row['point.y']},{row['point.x']}"
            new_df, city = requester(location, radius, return_city=True, coordtype="wgs84")
            df.at[index, 'city'] = city  # 更新当前行的城市信息

            if new_df is not None and not new_df.empty:
                # 删除不需要的列
                columns_to_remove = ["cp", "direction", "distance", "parent_poi.direction", "parent_poi.distance"]
                new_df.drop(columns=columns_to_remove, errors='ignore', inplace=True)

                # 根据"uid"去除重复的项
                existing_uids = df['uid'].unique()
                new_df = new_df[~new_df['uid'].isin(existing_uids)]

                # 如果经过去重后new_df非空，则将其添加到原始df的末尾
                if not new_df.empty:
                    df = pd.concat([df, new_df], ignore_index=True)

        # 更新进度信息
        progress_percentage = ((index + 1) / len(df)) * 100
        print(f"\r当前进度: {index + 1}/{len(df)} ({progress_percentage:.2f}%)", end='')
        index += 1  # 处理下一行
    return df


if __name__ == '__main__':

    area_name = "上海"
    radius = 1000
    radius_rate = 0.5

    area_config = next((area for area in config.area_infos if area["area_name"] == area_name), None)
    tar_area = area_config["points"]
    new_tasks = area_config["new_tasks"]
    check_point = area_config["check_point"]
    print(f'当前check point:{check_point}')
    result_path = f'{area_name}园区_{check_point}-{check_point + new_tasks - 1}.xlsx'

    ak_config = configparser.ConfigParser()
    ak_config.read('ak_config.ini')
    ak = ak_config['ak']['ak']

    tar_points = parse_coordinates(tar_area)
    polygon = Polygon(tar_points)

    x_values, y_values = zip(*tar_points)
    x_min, x_max = min(x_values), max(x_values)
    y_min, y_max = min(y_values), max(y_values)
    generator = circle_generator(x_min=x_min, x_max=x_max, y_min=y_min, y_max=y_max, radius=int(radius*radius_rate))
    data_queue = Queue()
    result_df = []
    lock = Lock()

    # 启动数据处理线程
    processor_thread = Thread(target=process_queue, args=(data_queue, result_df, lock, radius))
    processor_thread.start()
    processed_count = 0  # 已处理计数器

    # 使用ThreadPoolExecutor生成数据
    with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
        # 从generator获取从check_point开始的new_tasks个任务
        tasks = islice(generator, check_point, check_point + new_tasks)
        futures = {executor.submit(process_main, info, data_queue, radius): info for info in tasks}

        # 等待每个任务完成，并实时更新进度
        for future in as_completed(futures):
            future.result()
            processed_count += 1  # 每完成一个任务，计数器加1
            update_progress(processed_count, new_tasks)  # 更新进度提示

    check_point += processed_count

    # 在所有数据生成任务完成后，向队列中添加结束信号
    data_queue.put(None)

    # 等待数据处理线程结束
    processor_thread.join()
    print("\n所有任务完成，正在保存数据...")

    # 保存结果DataFrame到Excel
    if result_df:
        print(f'共找到{len(result_df[0])}条园区数据。')
        result_df[0].to_excel(result_path, index=False)
    else:
        print(f'{check_point}-{check_point + new_tasks - 1}无任何园区。')

    # 更新check_point
    update_config_check_point(area_name, check_point)
