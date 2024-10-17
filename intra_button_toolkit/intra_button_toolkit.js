
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

function sendDataToPython(data) {
    sendMessageToStreamlitClient("streamlit:setComponentValue", data);
}

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

let intra_buttons = window.parent.document.querySelectorAll('.intra-button');
intra_buttons.forEach(button => {
    button.addEventListener('click', () => {
        const param = button.getAttribute('node_name');
        sendData(param);
        intra_buttons.forEach(btn => {
            btn.style.display = 'none';  // This hides the button
        });
    });
});
