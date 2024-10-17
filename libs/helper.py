import json
import os
import re
import uuid
import streamlit as st
import pandas as pd
from .custom import *
import copy
import io
from text_toolkit import text_toolkit
from intra_button_toolkit import intra_button_toolkit
import markdown


def get_history_chats(path: str) -> list:
    if "apikey" in st.secrets:
        os.makedirs(path, exist_ok=True)
        files = [f for f in os.listdir(f'./{path}') if f.endswith('.json')]
        files_with_time = [(f, os.stat(f'./{path}/' + f).st_ctime) for f in files]
        sorted_files = sorted(files_with_time, key=lambda x: x[1], reverse=True)
        chat_names = [os.path.splitext(f[0])[0] for f in sorted_files]
        if len(chat_names) == 0:
            chat_names.append('New Chat_' + str(uuid.uuid4()))
    else:
        chat_names = ['New Chat_' + str(uuid.uuid4())]
    return chat_names


def save_data(path: str, file_name: str, history: list, **kwargs):
    print("save", path, file_name, history)
    if not os.path.exists(path):
        os.makedirs(path)
    with open(f"./{path}/{file_name}.json", 'w', encoding='utf-8') as f:
        json.dump({"history": history, **kwargs}, f, ensure_ascii=False, indent=2)


def remove_data(path: str, chat_name: str):
    try:
        os.remove(f"./{path}/{chat_name}.json")
    except FileNotFoundError:
        pass
    # 清除缓存
    try:
        st.session_state.pop('history' + chat_name)
        for item in ["context_select", "context_input", "context_level", *initial_content_all['paras']]:
            st.session_state.pop(item + chat_name + "value")
    except KeyError:
        pass


def load_data(path: str, file_name: str) -> dict:
    try:
        with open(f"./{path}/{file_name}.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except FileNotFoundError:
        content = copy.deepcopy(initial_content_all)
        if "apikey" in st.secrets:
            with open(f"./{path}/{file_name}.json", 'w', encoding='utf-8') as f:
                f.write(json.dumps(content))
        return content


def show_each_message(message: str, role: str, idr: str, area=None, buttons=None):
    if area is None:
        area = [st.markdown] * 2
    if role == 'user':
        icon = user_svg
        name = user_name
        background_color = user_background_color
        data_idr = idr + "_user"
        class_name = 'user'
    else:
        icon = gpt_svg
        name = gpt_name
        background_color = gpt_background_color
        data_idr = idr + "_assistant"
        class_name = 'assistant'
    if buttons:
        btn_code = ""
        for btn_name in buttons:
            btn_code += f"<button class='intra-button' node_name='{btn_name}'>{btn_name}</button>"
        btn_block_code = f"<div>{btn_code}</div>"
        
    message = url_correction(message)
    area[0](f"\n<div class='avatar'>{icon}<h2>{name}:</h2></div>", unsafe_allow_html=True)
    if "[TX_SEP]" in message:
        messages = message.split("[TX_SEP]")[1:]
    else:
        messages = [message]
    div_template = f"""<div class='content-div {class_name}' data-idr='{data_idr}' style='background-color: {background_color};'>\n\n"""
    generate_html = ""
    head = True
    for message in messages:
        if not head:
            generate_html += "</div>"
        else:
            head = False
        generate_html += (div_template + message)
    if buttons:
        generate_html += btn_block_code
    area[1](generate_html, unsafe_allow_html=True)

def show_spin_message(area):
    icon = gpt_svg
    name = gpt_name
    area(f"\n<div class='avatar'>{icon}<h2>{name}:</h2></div>", unsafe_allow_html=True)


def show_messages(current_chat: str, messages: list):
    id_role = 0
    id_assistant = 0
    for i, each in enumerate(messages):
        if each["role"] == "user":
            idr = id_role
            id_role += 1
        elif each["role"] == "assistant":
            idr = id_assistant
            id_assistant += 1
        else:
            idr = False
        if idr is not False:
            show_each_message(each["content"], each["role"], str(idr), buttons=each['button'] if i == len(messages) - 1 else None)
            if "open_text_toolkit_value" not in st.session_state or st.session_state["open_text_toolkit_value"]:
                # st.session_state['frontend_msg_dict'][current_chat + ">" + str(idr)] = text_toolkit(
                #     data_idr=str(idr) + '_' + each["role"], ratings=each.get("ratings", {}), clicked=each.get("clicked", {}))
                st.session_state['frontend_msg_dict'][current_chat + ">" + str(idr)] = text_toolkit(
                    data_idr=str(idr) + '_' + each["role"], ratings=each.get("ratings", {}))
        if each["role"] == "assistant":
            st.write("---")


# 根据context_level提取history
def get_history_input(history: list, level: int) -> list:
    if level != 0 and history:
        df_input = pd.DataFrame(history).query('role!="system"')
        df_input = df_input[-level * 2:]
        res = df_input.to_dict('records')
    else:
        res = []
    return res


# 去除#号右边的空格
# def remove_hashtag_right__space(text: str) -> str:
#     text = re.sub(r"(#+)\s*", r"\1", text)
#     return text


# 提取文本
def extract_chars(text: str, num: int) -> str:
    char_num = 0
    chars = ''
    for char in text:
        # 汉字算两个字符
        if '\u4e00' <= char <= '\u9fff':
            char_num += 2
        else:
            char_num += 1
        chars += char
        if char_num >= num:
            break
    return chars


@st.cache_data(max_entries=20, show_spinner=False)
def download_history(history: list):
    md_text = ""
    for msg in history:
        if msg['role'] == 'user':
            md_text += f'## {user_name}：\n{msg["content"]}\n'
        elif msg['role'] == 'assistant':
            md_text += f'## {gpt_name}：\n{msg["content"]}\n'
    output = io.BytesIO()
    output.write(md_text.encode('utf-8'))
    output.seek(0)
    return output


def filename_correction(filename: str) -> str:
    pattern = r'[^\w\.-]'
    filename = re.sub(pattern, '', filename)
    return filename


def url_correction(text: str) -> str:
    pattern = r'((?:http[s]?://|www\.)(?:[a-zA-Z0-9]|[$-_\~#!])+)'
    text = re.sub(pattern, r' \g<1> ', text)
    return text

# st的markdown会错误渲染英文引号加英文字符，例如 :abc
# def colon_correction(text):
#     pattern = r':[a-zA-Z]'
#     if re.search(pattern, text):
#         text = text.replace(":", "&#58;")
#         pattern = r'`([^`]*)&#58;([^`]*)`|```([^`]*)&#58;([^`]*)```'
#         text = re.sub(pattern, lambda m: m.group(0).replace('&#58;', ':') if '&#58;' in m.group(0) else m.group(0),
#                       text)
#     return text
