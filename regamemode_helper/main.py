import os
import json
import re

from mcdreforged.api.all import *
from typing import NamedTuple

camera_player = 0
# 临时存储数据
temp_data_list: dict = {}
DATA_FILE = 'config/gamemode_helper.json'


# Reference Here Plugin
class Position(NamedTuple):
    x: float
    y: float
    z: float


# 这一部分是将 Rcon 返回的数据进行处理
def process_coordinate(text: str) -> Position:
    data = text[1:-1].replace('d', '').split(', ')
    data = [(x + 'E0').split('E') for x in data]
    assert len(data) == 3
    return Position(*[float(e[0]) * 10 ** int(e[1]) for e in data])


def process_dimension(text: str) -> str:
    return text.replace(re.match(r'[\w ]+: ', text).group(), '', 1).strip('"\' ')


def process_facing(text: str) -> str:
    data = text[1:-1].replace('f', '').split(', ')
    return ' '.join(data)


def on_info(server: PluginServerInterface, info: Info):
    global camera_player
    if info.is_player and info.content == "!c":
        player_name = info.player
        # Rcon 是否连接并运行
        if server.is_rcon_running():
            if player_name not in temp_data_list.keys():
                # 坐标
                position = process_coordinate(
                    re.search(r'\[.*]', server.rcon_query('data get entity {} Pos'.format(player_name))).group()
                )
                # 面向
                rotation = process_facing(
                    re.search(r'\[.*]', server.rcon_query('data get entity {} Rotation'.format(player_name))).group()
                )
                # 维度
                dimension = process_dimension(
                    server.rcon_query('data get entity {} Dimension'.format(player_name))
                )
                temp_data_list[player_name] = {
                    "x": position.x,
                    "y": position.y,
                    "z": position.z,
                    "facing": rotation,
                    "dimension": dimension
                }
                server.execute("gamemode spectator {}".format(player_name))
            else:
                return
        else:
            camera_player += 1
            server.execute('data get entity ' + info.player)

    elif info.is_player and info.content == "!s":
        player_name = info.player
        if player_name in temp_data_list.keys():
            player_position = temp_data_list.get(player_name)
            x = player_position['x']
            y = player_position['y']
            z = player_position['z']
            facing = player_position['facing']
            dimension = player_position['dimension']
            server.execute(f"execute in {dimension} run tp {player_name} {x} {y} {z} {facing}")
            server.execute(f"gamemode survival {player_name}")
            del temp_data_list[player_name]

    # 如果没有 rcon
    if not info.is_player and camera_player > 0 and re.match(r'\w+ has the following entity data: ', info.content) is not None:
        name = info.content.split(' ')[0]
        position_str = re.search(r'(?<=Pos: )\[.*?]', info.content).group()
        dimension = re.search(r'(?<= Dimension: )(.*?),', info.content).group().replace('"', '').replace("'", '').replace(',', '')
        facing_str = re.search(r'(?<=Rotation: )\[.*?]', info.content).group()
        position = process_coordinate(position_str)
        rotation = process_facing(facing_str)
        temp_data_list[name] = {
            "x": position.x,
            "y": position.y,
            "z": position.z,
            "facing": rotation,
            "dimension": dimension
        }
        server.execute("gamemode spectator {}".format(name))
        camera_player -= 1


# 服务器被关闭, 无论是崩溃还是正常关闭
def on_server_stop(server: PluginServerInterface, server_return_code: int):
    with open(DATA_FILE, 'w', encoding='utf8') as data_file:
        json.dump(temp_data_list, data_file, ensure_ascii=False, indent=2)


# 插件被卸载
def on_unload(server: PluginServerInterface):
    with open(DATA_FILE, 'w', encoding='utf8') as data_file:
        json.dump(temp_data_list, data_file, ensure_ascii=False, indent=2)


def on_load(server: PluginServerInterface, old):
    global temp_data_list
    if os.path.exists(DATA_FILE) is False:
        with open(DATA_FILE, 'w', encoding='utf8') as data_file:
            json.dump({}, data_file, ensure_ascii=False, indent=2)
            temp_data_list = {}
    elif os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf8') as data_file:
            temp_data_list = json.load(data_file)
    server.register_help_message('!c', '切换为旁观者模式')
    server.register_help_message('!s', '切换回生存并回到切换为旁观者时的位置')
