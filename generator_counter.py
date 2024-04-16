from baidu_api import *

area_name = "上海"
radius = 1000
radius_rate = 0.5

area_config = next((area for area in config.area_infos if area["area_name"] == area_name), None)
tar_area = area_config["points"]
new_tasks = area_config["new_tasks"]
check_point = area_config["check_point"]
print(f'当前check point:{check_point}')
result_path = f'{area_name}园区_{check_point}-{check_point + new_tasks - 1}.xlsx'

tar_points = parse_coordinates(tar_area)

x_values, y_values = zip(*tar_points)
x_min, x_max = min(x_values), max(x_values)
y_min, y_max = min(y_values), max(y_values)
generator = circle_generator(x_min=x_min, x_max=x_max, y_min=y_min, y_max=y_max, radius=int(radius * radius_rate))
print(next(islice(generator, 74095, None), None))
