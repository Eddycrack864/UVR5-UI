import json
import os
import importlib
import gradio as gr

now_dir = os.getcwd()

folder = os.path.join(now_dir, "assets", "themes")
config_file = os.path.join(now_dir, "assets", "config.json")

import sys

sys.path.append(folder)


def get_class(filename):
    with open(filename, "r", encoding="utf8") as file:
        for line_number, line in enumerate(file, start=1):
            if "class " in line:
                found = line.split("class ")[1].split(":")[0].split("(")[0].strip()
                return found
                break
    return None


def get_list():

    themes_from_files = [
        os.path.splitext(name)[0]
        for root, _, files in os.walk(folder, topdown=False)
        for name in files
        if name.endswith(".py") and root == folder and name != "loadThemes.py"
    ]

    json_file_path = os.path.join(folder, "themes_list.json")

    try:
        with open(json_file_path, "r", encoding="utf8") as json_file:
            themes_from_url = [item["id"] for item in json.load(json_file)]
    except FileNotFoundError:
        themes_from_url = []

    combined_themes = set(themes_from_files + themes_from_url)

    return list(combined_themes)


def select_theme(name):
    selected_file = name + ".py"
    full_path = os.path.join(folder, selected_file)

    if not os.path.exists(full_path):
        with open(config_file, "r", encoding="utf8") as json_file:
            config_data = json.load(json_file)

        config_data["theme"]["file"] = None
        config_data["theme"]["class"] = name

        with open(config_file, "w", encoding="utf8") as json_file:
            json.dump(config_data, json_file, indent=2)
        print(f"Theme {name} successfully selected, restart the App.")
        gr.Info(f"Theme {name} successfully selected, restart the App.")
        return

    class_found = get_class(full_path)
    if class_found:
        with open(config_file, "r", encoding="utf8") as json_file:
            config_data = json.load(json_file)

        config_data["theme"]["file"] = selected_file
        config_data["theme"]["class"] = class_found

        with open(config_file, "w", encoding="utf8") as json_file:
            json.dump(config_data, json_file, indent=2)
        print(f"Theme {name} successfully selected, restart the App.")
        gr.Info(f"Theme {name} successfully selected, restart the App.")
    else:
        print(f"Theme {name} was not found.")

def select_mode(mode: str):
    with open(config_file, "r", encoding="utf8") as json_file:
        config_data = json.load(json_file)

    config_data["theme"]["mode"] = mode

    with open(config_file, "w", encoding="utf8") as json_file:
        json.dump(config_data, json_file, indent=2)

    print(f"Mode {mode} successfully selected, restart the App.")
    gr.Info(f"Mode {mode} successfully selected, restart the App.")

def read_json():
    try:
        with open(config_file, "r", encoding="utf8") as json_file:
            data = json.load(json_file)
            selected_file = data["theme"]["file"]
            class_name = data["theme"]["class"]

            if selected_file is not None and class_name:
                return class_name
            elif selected_file == None and class_name:
                return class_name
            else:
                return "NoCrypt/miku"
    except Exception as error:
        print(f"An error occurred loading the theme: {error}")
        return "NoCrypt/miku"


def load_json():
    try:
        with open(config_file, "r", encoding="utf8") as json_file:
            data = json.load(json_file)
            selected_file = data["theme"]["file"]
            class_name = data["theme"]["class"]

            if selected_file is not None and class_name:
                module = importlib.import_module(selected_file[:-3])
                obtained_class = getattr(module, class_name)
                instance = obtained_class()
                print(f"Theme {class_name} successfully loaded.")
                return instance
            elif selected_file == None and class_name:
                return class_name
            else:
                print("The theme is incorrect.")
                return None
    except Exception as error:
        print(f"An error occurred loading the theme: {error}")
        return None
