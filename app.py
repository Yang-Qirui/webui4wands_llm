import os.path
from libs.helper import *
import streamlit as st
import uuid
import pandas as pd
import openai
from requests.models import ChunkedEncodingError
from streamlit.components import v1
from voice_toolkit import voice_toolkit
import requests
import ast

LOCAL_HOST = "http://127.0.0.1:5000"
if "apibase" in st.secrets:
    openai.api_base = st.secrets["apibase"]
else:
    openai.api_base = "https://api.openai.com/v1"

st.set_page_config(
    page_title="UniMate",
    layout="wide",
    page_icon=ICON,
)
# 自定义元素样式
st.markdown(css_code, unsafe_allow_html=True)
if "initial_settings" not in st.session_state:
    # 历史聊天窗口
    st.session_state["path"] = "history_chats_file"
    st.session_state["history_chats"] = get_history_chats(st.session_state["path"])
    # ss参数初始化
    st.session_state["frontend_msg_dict"] = {}
    st.session_state["jump_msg_dict"] = {}
    st.session_state["ratings"] = {}
    st.session_state["delete_count"] = 0
    st.session_state["voice_flag"] = ""
    st.session_state["user_voice_value"] = ""
    st.session_state["error_info"] = ""
    st.session_state["current_chat_index"] = 0
    st.session_state["user_input_content"] = ""
    st.session_state["option_nodes"] = None
    st.session_state["user_query_from_button"] = None
    st.session_state["button_response"] = None
    
    # 读取全局设置
    if os.path.exists("./set.json"):
        with open("./set.json", "r", encoding="utf-8") as f:
            data_set = json.load(f)
        for key, value in data_set.items():
            st.session_state[key] = value
    # 设置完成
    st.session_state["initial_settings"] = True        
        
with st.sidebar:
    st.markdown(wands_svg,unsafe_allow_html=True)
    st.header("Chat History")
    # 创建容器的目的是配合自定义组件的监听操作
    chat_container = st.container()
    with chat_container:
        current_chat = st.radio(
            label="history_chat",
            format_func=lambda x: x.split("_")[0] if "_" in x else x,
            options=st.session_state["history_chats"],
            label_visibility="collapsed",
            index=st.session_state["current_chat_index"],
            key="current_chat"
            + st.session_state["history_chats"][st.session_state["current_chat_index"]],
            # on_change=current_chat_callback  # 此处不适合用回调，无法识别到窗口增减的变动
        )
    st.write("---")

# 数据写入文件
def write_data(new_chat_name=current_chat):
    save_data(
        st.session_state["path"],
        new_chat_name,
        st.session_state["history" + current_chat]
    )


def reset_chat_name_fun(chat_name):
    chat_name = chat_name + "_" + str(uuid.uuid4())
    new_name = filename_correction(chat_name)
    current_chat_index = st.session_state["history_chats"].index(current_chat)
    st.session_state["history_chats"][current_chat_index] = new_name
    st.session_state["current_chat_index"] = current_chat_index
    # 写入新文件
    write_data(new_name)
    # 转移数据
    st.session_state["history" + new_name] = st.session_state["history" + current_chat]
    remove_data(st.session_state["path"], current_chat)


def create_chat_fun():
    st.session_state["history_chats"] = [
        "New Chat_" + str(uuid.uuid4())
    ] + st.session_state["history_chats"]
    st.session_state["current_chat_index"] = 0


def delete_chat_fun():
    if len(st.session_state["history_chats"]) == 1:
        chat_init = "New Chat_" + str(uuid.uuid4())
        st.session_state["history_chats"].append(chat_init)
    pre_chat_index = st.session_state["history_chats"].index(current_chat)
    if pre_chat_index > 0:
        st.session_state["current_chat_index"] = (
            st.session_state["history_chats"].index(current_chat) - 1
        )
    else:
        st.session_state["current_chat_index"] = 0
    st.session_state["history_chats"].remove(current_chat)
    remove_data(st.session_state["path"], current_chat)


with st.sidebar:
    c1, c2 = st.columns(2)
    create_chat_button = c1.button(
        "New Chat", use_container_width=True, key="create_chat_button"
    )
    if create_chat_button:
        create_chat_fun()
        st.rerun()

    delete_chat_button = c2.button(
        "Delete", use_container_width=True, key="delete_chat_button"
    )
    if delete_chat_button:
        delete_chat_fun()
        st.rerun()

with st.sidebar:
    if ("set_chat_name" in st.session_state) and st.session_state[
        "set_chat_name"
    ] != "":
        reset_chat_name_fun(st.session_state["set_chat_name"])
        st.session_state["set_chat_name"] = ""
        st.rerun()

    st.write("\n")
    st.text_input("Set Chat Name", key="set_chat_name", placeholder="Click to input")
    st.caption(
        """
    - Double-click or press "/" to position the input field
    - Ctrl + Enter for quick submission
    """
    )

# 加载数据
if "history" + current_chat not in st.session_state:
    for key, value in load_data(st.session_state["path"], current_chat).items():
        if key == "history":
            st.session_state[key + current_chat] = value
        else:
            for k, v in value.items():
                st.session_state[k + current_chat + "value"] = v

# 保证不同chat的页面层次一致，否则会导致自定义组件重新渲染
container_show_messages = st.container()
container_show_messages.write("")
# 对话展示
if not st.session_state["history" + current_chat]:
    try:
        response = requests.post(LOCAL_HOST + "/query", json={"query": ""}, headers={"Content-Type": "application/json"})
        candidate_options = requests.get(LOCAL_HOST + "/get-options")
        candidate_options = ast.literal_eval(candidate_options.text)
        st.session_state["history" + current_chat].append({"role": "assistant", "content": response.text, "button": candidate_options})
        st.session_state["option_nodes"] = candidate_options
    except Exception as e:
        st.session_state["history" + current_chat].append({"role": "assistant", "content": str(e), "button": candidate_options})

        
with container_show_messages:
    if st.session_state["history" + current_chat]:
        show_messages(current_chat, st.session_state["history" + current_chat])


# 核查是否有对话需要删除
st.session_state["jump_msg_dict"] = intra_button_toolkit()
print(st.session_state["jump_msg_dict"])
if st.session_state["jump_msg_dict"]:
    jump_msg_dict = st.session_state["jump_msg_dict"]
    st.session_state["user_query_from_button"] = jump_msg_dict["user_query_from_button"]
    st.session_state["button_response"] = jump_msg_dict["button_response"]
    st.session_state["jump_msg_dict"] = None

if any(st.session_state["frontend_msg_dict"].values()):
    for key, value in st.session_state["frontend_msg_dict"].items():
        try:
            ratings = value.get("ratings")
        except AttributeError:
            ratings = None
        if ratings:
            select_keys = key
            select_current_chat, idr = select_keys.split(">")

            df_history_tem = pd.DataFrame(
                st.session_state["history" + select_current_chat]
            )

            assistant_mask = df_history_tem["role"] == "assistant"
            assistant_indices = df_history_tem[assistant_mask].index

            if int(idr) < len(assistant_indices):
                target_index = assistant_indices[int(idr)]

                if "ratings" not in df_history_tem.columns:
                    df_history_tem["ratings"] = None

                df_history_tem.at[target_index, "ratings"] = ratings

            # 更新会话状态
            st.session_state["history" + select_current_chat] = df_history_tem.to_dict("records")
            write_data()
            st.rerun()

        else:
            try:
                deleteCount = value.get("deleteCount")
            except AttributeError:
                deleteCount = None
            if deleteCount == st.session_state["delete_count"]:
                delete_keys = key
                st.session_state["delete_count"] = deleteCount + 1
                delete_current_chat, idr = delete_keys.split(">")
                df_history_tem = pd.DataFrame(
                    st.session_state["history" + delete_current_chat]
                )
                df_history_tem.drop(
                    index=df_history_tem.query("role=='user'").iloc[[int(idr)], :].index,
                    inplace=True,
                )
                df_history_tem.drop(
                    index=df_history_tem.query("role=='assistant'")
                    .iloc[[int(idr)], :]
                    .index,
                    inplace=True,
                )
                st.session_state["history" + delete_current_chat] = df_history_tem.to_dict(
                    "records"
                )
                write_data()
                st.rerun()

def callback_fun(arg):
    # 连续快速点击新建与删除会触发错误回调，增加判断
    if ("history" + current_chat in st.session_state) and (
        "frequency_penalty" + current_chat in st.session_state
    ):
        write_data()
        st.session_state[arg + current_chat + "value"] = st.session_state[
            arg + current_chat
        ]


def clear_button_callback():
    st.session_state["history" + current_chat] = []
    write_data()


def delete_all_chat_button_callback():
    if "apikey" in st.secrets:
        folder_path = st.session_state["path"]
        file_list = os.listdir(folder_path)
        for file_name in file_list:
            file_path = os.path.join(folder_path, file_name)
            if file_name.endswith(".json") and os.path.isfile(file_path):
                os.remove(file_path)
    st.session_state["current_chat_index"] = 0
    st.session_state["history_chats"] = ["New Chat_" + str(uuid.uuid4())]


def save_set(arg):
    st.session_state[arg + "_value"] = st.session_state[arg]
    if "apikey" in st.secrets:
        with open("./set.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "open_text_toolkit_value": st.session_state["open_text_toolkit"],
                    "open_voice_toolkit_value": st.session_state["open_voice_toolkit"],
                },
                f,
            )


# 输入内容展示
area_user_svg = st.empty()
area_user_content = st.empty()
# 回复展示
area_gpt_svg = st.empty()
area_gpt_content = st.empty()
area_btn = st.empty()
# 报错展示
area_error = st.empty()

st.write("\n")
icon_text = f"""
    <div class="icon-text-container">
        <img src='data:image/png;base64,{ICON_base64}' alt='icon'>
        <span style='font-size: 24px; padding-left: 10px;'>Chat with UniMate</span>
    </div>
    """
st.markdown(icon_text, unsafe_allow_html=True)

input_placeholder = st.empty()
with input_placeholder.container():

    def input_callback():
        if st.session_state["user_input_area"] != "":
            # 修改窗口名称
            user_input_content = st.session_state["user_input_area"]
            df_history = pd.DataFrame(st.session_state["history" + current_chat])
            if df_history.empty or len(df_history.query('role!="system"')) == 0:
                new_name = extract_chars(user_input_content, 18)
                reset_chat_name_fun(new_name)

    with st.form("input_form", clear_on_submit=True):
        user_input = st.text_area(
            "**Input:**",
            key="user_input_area",
            help=ETHIC_CODE,
            value=st.session_state["user_voice_value"],
        )
        submitted = st.form_submit_button(
            "Submit", use_container_width=True, on_click=input_callback
        )
    if submitted:
        st.session_state["user_input_content"] = user_input
        st.session_state["user_voice_value"] = ""
        # st.rerun()

    if "open_voice_toolkit_value" not in st.session_state:
        st.session_state["open_voice_toolkit_value"] = False
    
    if (
        st.session_state["open_voice_toolkit_value"]
    ):
        # 语音输入功能
        vocie_result = voice_toolkit()
        # vocie_result会保存最后一次结果
        if (
            vocie_result and vocie_result["voice_result"]["flag"] == "interim"
        ) or st.session_state["voice_flag"] == "interim":
            st.session_state["voice_flag"] = "interim"
            st.session_state["user_voice_value"] = vocie_result["voice_result"]["value"]
            if vocie_result["voice_result"]["flag"] == "final":
                st.session_state["voice_flag"] = "final"
                st.rerun() 
    
if st.session_state["user_input_content"] != "":
    if "r" in st.session_state:
        st.session_state.pop("r")
        st.session_state[current_chat + "report"] = ""
    st.session_state["pre_user_input_content"] = st.session_state["user_input_content"]
    st.session_state["user_input_content"] = ""
    # 临时展示
    show_each_message(
        st.session_state["pre_user_input_content"],
        "user",
        "tem",
        [area_user_svg.markdown, area_user_content.markdown],
    )
    st.session_state["history" + current_chat].append(
        {"role": "user", "content": st.session_state["pre_user_input_content"]}
    )
    write_data()
    show_spin_message(area_gpt_svg.markdown)
    # 调用接口
    with area_gpt_content.container():
        with st.spinner("🤔Thinking..."):
            try:
                max_try = 3
                try_cnt = 0
                while try_cnt < max_try:
                    r = requests.post("http://127.0.0.1:5000/query",
                                      headers={"Content-Type": "application/json"},
                                      data=json.dumps({"query": st.session_state["pre_user_input_content"]}),
                                      stream=True)
                    if r.status_code == 200:
                        break
                    try_cnt += 1
                if try_cnt == max_try:
                    r = "Sorry, due to internal error, this question is beyond my capability."
                # print(r.choices[0].message.model_dump_json())
            except (FileNotFoundError, KeyError):
                area_error.error(
                    "Timeout"
                )
            else:
                st.session_state["chat_of_r"] = current_chat
                st.session_state["r"] = r
                st.rerun()

if ("r" in st.session_state) and (current_chat == st.session_state["chat_of_r"]):
    if current_chat + "report" not in st.session_state:
        st.session_state[current_chat + "report"] = ""
    try:
        if type(st.session_state["r"]) == str:
            st.session_state[current_chat + "report"] = st.session_state["r"]
            show_each_message(
                st.session_state[current_chat + "report"],
                "assistant",
                "tem",
                [area_gpt_svg.markdown, area_gpt_content.markdown]
            )
        else:
            for chunk in st.session_state["r"].iter_lines(decode_unicode=True):
                if chunk:
                    st.session_state[current_chat + "report"] += chunk
                    show_each_message(
                        st.session_state[current_chat + "report"],
                        "assistant",
                        "tem",
                        [area_gpt_svg.markdown, area_gpt_content.markdown],
                        st.session_state["option_nodes"]                
                    )
    except ChunkedEncodingError:
        area_error.error("网络状况不佳，请刷新页面重试。")
    # 应对stop情形
    except Exception as e:
        area_error.error("ERROR")
        print(e)
    else:
        # 保存内容
        # st.session_state["history" + current_chat].append(
        #     {"role": "user", "content": st.session_state["pre_user_input_content"]}
        # )
        st.session_state["history" + current_chat].append(
            {"role": "assistant", "content": st.session_state[current_chat + "report"]}
        )
        write_data()
    # 用户在网页点击stop时，ss某些情形下会暂时为空
    if current_chat + "report" in st.session_state:
        st.session_state.pop(current_chat + "report")
    if "r" in st.session_state:
        st.session_state.pop("r")
        st.rerun()

if st.session_state["user_query_from_button"] and st.session_state["button_response"]:
    show_each_message(
        st.session_state["user_query_from_button"],
        "user",
        "tem",
        [area_user_svg.markdown, area_user_content.markdown]
    )
    candidate_options = requests.get(LOCAL_HOST + "/get-options")
    candidate_options = ast.literal_eval(candidate_options.text)
    show_each_message(
        st.session_state["button_response"],
        "assistant",
        "tem",
        [area_gpt_svg.markdown, area_gpt_content.markdown],
        candidate_options
    )
    st.session_state["history" + current_chat].append(
        {"role": "user", "content": st.session_state["user_query_from_button"]}
    )
    st.session_state["history" + current_chat].append(
        {"role": "assistant", "content": st.session_state["button_response"], "button": candidate_options}
    )
    write_data()
    st.session_state["user_query_from_button"] = None
    st.session_state["button_response"] = None
    

v1.html(js_code, height=0)
