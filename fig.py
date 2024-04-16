import matplotlib.pyplot as plt
import numpy as np


def is_circle_in_shape(circle_center, circle_radius, shape_bbox):
    """
    简化的检查函数，用于确定圆是否至少部分位于矩形内。
    在这个简化的版本中，shape_bbox是一个四元组(x_min, y_min, x_max, y_max)。
    """
    x, y = circle_center
    x_min, y_min, x_max, y_max = shape_bbox

    # 检查圆的任何部分是否与矩形相交
    if x + circle_radius < x_min or x - circle_radius > x_max:
        return False
    if y + circle_radius < y_min or y - circle_radius > y_max:
        return False
    return True


def cover_rectangle_with_circles(rectangle_bbox, radius=1):
    x_min, y_min, x_max, y_max = rectangle_bbox
    grid_size = radius * 2  # 网格大小基于圆半径调整，以减少重叠

    fig, ax = plt.subplots()

    # 绘制矩形
    rectangle = plt.Rectangle((x_min, y_min), x_max - x_min, y_max - y_min, edgecolor='r', fill=False)
    ax.add_patch(rectangle)

    # 绘制原网格上的圆，调整x_positions和y_positions的计算，以确保覆盖矩形的边界
    x_positions = np.arange(x_min, x_max + radius, grid_size)  # 确保x方向上的圆可以覆盖到矩形的右边界
    y_positions = np.arange(y_min, y_max + radius, grid_size)  # 确保y方向上的圆可以覆盖到矩形的上边界

    # 绘制偏移网格上的圆，同样调整计算方式
    x_positions_offset = np.arange(x_min + radius, x_max + radius, grid_size)  # 同样确保偏移的圆也能覆盖到矩形的右边界
    y_positions_offset = np.arange(y_min + radius, y_max + radius, grid_size)  # 同样确保偏移的圆也能覆盖到矩形的上边界

    # 绘制原网格上的圆
    for x in x_positions:
        for y in y_positions:
            if is_circle_in_shape((x, y), radius, rectangle_bbox):
                circle = plt.Circle((x, y), radius, edgecolor='b', fill=False, alpha=0.5)
                ax.add_patch(circle)

    # 绘制偏移网格上的圆，以填补空隙
    for x in x_positions_offset:
        for y in y_positions_offset:
            if is_circle_in_shape((x, y), radius, rectangle_bbox):
                circle = plt.Circle((x, y), radius, edgecolor='g', fill=False, alpha=0.5)  # 使用不同颜色以示区分
                ax.add_patch(circle)

    plt.xlim(x_min - radius, x_max + radius)
    plt.ylim(y_min - radius, y_max + radius)
    ax.set_aspect('equal', 'box')
    plt.show()


# 定义矩形的边界框：(x_min, y_min, x_max, y_max)
rectangle_bbox = (-7, 3, -2, 6)

# 调用函数，尝试用圆覆盖这个矩形
cover_rectangle_with_circles(rectangle_bbox)


