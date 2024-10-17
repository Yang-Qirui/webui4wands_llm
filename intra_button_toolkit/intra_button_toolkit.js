
function sendMessageToStreamlitClient(type, data) {
    const outData = Object.assign({
        isStreamlitMessage: true,
        type: type,
    }, data);
    window.parent.postMessage(outData, "*");
}

function init() {
    sendMessageToStreamlitClient("streamlit:componentReady", {apiVersion: 1});
}

function setFrameHeight(height) {
    sendMessageToStreamlitClient("streamlit:setFrameHeight", {height: height});
}

function sendDataToPython(data) {
    sendMessageToStreamlitClient("streamlit:setComponentValue", data);
}

function onDataFromPython(event){
    const button_names = event?.data?.args?.button_names;
    if(button_names) {
        // Add Buttons to Main Div
        let main_div = document.querySelector('.main');
        let existing_buttons = main_div.querySelectorAll('.intra-button');
        let buttons_name = []
        existing_buttons.forEach(btn => {
            buttons_name.push(btn.getAttribute('node_name'));
        });
        button_names.forEach(item => {
            if(buttons_name.indexOf(item) === -1) {
                let new_button = document.createElement('button');
                new_button.innerText = item;
                new_button.className = "intra-button";
                new_button.setAttribute('node_name', item);
                new_button.style.display = "inline-box";
                new_button.addEventListener('click', () => {
                    sendDataOnClick(new_button);
                })
                main_div.appendChild(new_button);
            }
        });
    }
}

window.addEventListener("message", onDataFromPython, false);

function sendData(query) {
    const dataToSend = { "query":  "[BUTTON]" + query}; // 要发送的字符串
    console.log("click")
    fetch('http://127.0.0.1:5000/query', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(dataToSend), // 将数据转化为JSON字符串发送
    })
    .then(response => {
        return response.text()   
    })
    .then(response => {
        sendDataToPython({
            "value":
            {
                "user_query_from_button": query,
                "button_response": response
            }
        })
    })
}

init()
function sendDataOnClick(button){
    const param = button.getAttribute('node_name');
    sendData(param);
    // TODO Hide all buttons
}

window.addEventListener("DOMContentLoaded", function () {
    setFrameHeight(40);
});
