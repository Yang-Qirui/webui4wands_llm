//// init.js
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

// The `data` argument can be any JSON-serializable value.
function sendDataToPython(data) {
    sendMessageToStreamlitClient("streamlit:setComponentValue", data);
}

init()

//// text_toolkit.js
const playBtn = document.getElementById("play-btn");
const toggleBtn = document.getElementById("toggle-btn");
const stopBtn = document.getElementById("stop-btn");
const speedSelect = document.getElementById('speed');
const copyButton = document.getElementById('copy-btn');
const deleteButton = document.getElementById('delete-btn');
const synth = window.parent.speechSynthesis;
let utterance = new SpeechSynthesisUtterance()
let TIMEOUT_KEEP_SYNTHESIS_WORKING = null;
let speechStatus
let IGNORE_CODE_BLOCKS = true;
let iframes = window.parent.document.querySelectorAll('iframe');
window.parent.textSound = []
iframes.forEach(iframe => {
    let btn = iframe.contentDocument.querySelector('.sound')
    let recordBtn = iframe.contentDocument.querySelector('button#record-btn')
    if (btn) {
        window.parent.textSound.push(btn)
    }
    if (recordBtn) {
        window.parent.recordBtn = recordBtn;
    }
})


// 接收来自Python的参数
function onDataFromPython(event) {
    playBtn.setAttribute("data-idr", event.data.args.data_idr);
    if (event.data.args.data_idr.includes('assistant')) {
        deleteButton.style.display = 'inline-block';
    }

    // 处理评分数据
    if (event.data.args.ratings) {
        const ratings = event.data.args.ratings;
        setRatings(ratings);
    }
}

// 设置评分
function setRatings(ratings) {
    for (const [type, value] of Object.entries(ratings)) {
        const ratingContainer = document.querySelector(`.star-rating[data-rating-type="${type}"]`);
        if (ratingContainer) {
            updateStars(ratingContainer, value);
            currentRatings[type] = value;
        }
    }
}

window.addEventListener("message", onDataFromPython, false);

function btnDisplay(value) {
    if (value === "inline-block") {
        playBtn.style.display = "inline-block";
        toggleBtn.style.display = "none";
        stopBtn.style.display = "none";

    } else {
        playBtn.style.display = "none";
        toggleBtn.style.display = "inline-block";
        stopBtn.style.display = "inline-block";
    }
}

function btnClass(value) {
    if (value === 'fa-pause') {
        toggleBtn.querySelector('.fas').classList.add('fa-pause');
        toggleBtn.querySelector('.fas').classList.remove('fa-play');
    } else {
        toggleBtn.querySelector('.fas').classList.add('fa-play');
        toggleBtn.querySelector('.fas').classList.remove('fa-pause');

    }
}

function skipCode(divElement, excludeSelector) {
    let excludeElements = Array.from(divElement.querySelectorAll(excludeSelector));

    return Array.from(divElement.childNodes)
        .filter(node => node.nodeType === Node.TEXT_NODE && node.textContent.trim() !== '' || node.nodeType === Node.ELEMENT_NODE && !excludeElements.includes(node))
        .map(node => node.textContent)
        .join('')
}

function KeepSpeechSynthesisActive() {
    synth.pause();
    synth.resume();
    TIMEOUT_KEEP_SYNTHESIS_WORKING = setTimeout(KeepSpeechSynthesisActive, 3500);
}

playBtn.addEventListener("click", () => {
    // 关闭录音
    if (window.parent.recordBtn) {
        if (window.parent.recordBtn.classList.contains("recording")) {
            window.parent.recordBtn.click()
        }
    }
    // 关闭现有播放
    synth.cancel();
    window.parent.current_idr = playBtn.getAttribute("data-idr")
    // 全部重置为喇叭图标
    window.parent.textSound.forEach(value => {
        {
            value.querySelector('#play-btn').style.display = "inline-block";
            value.querySelector('#toggle-btn').style.display = "none";
            value.querySelector('#stop-btn').style.display = "none";
        }
    })

    let textElement = window.parent.document.querySelector(`div[data-idr="${window.parent.current_idr}"]`)
    let sayOutText = "";
    if (IGNORE_CODE_BLOCKS) {
        sayOutText = skipCode(textElement, 'div.stCodeBlock')
    } else {
        sayOutText = textElement.textContent
    }

    if (sayOutText !== '') {
        utterance.text = sayOutText;
        utterance.rate = speedSelect.value;
        if (window.parent.selectedVoiceName) {
            utterance.voice = window.parent.voices.find(function (v) {
                return v.name === window.parent.selectedVoiceName;
            });
            utterance.lang = utterance.voice.lang
        }
        utterance.onstart = () => {
            clearTimeout(TIMEOUT_KEEP_SYNTHESIS_WORKING);
            TIMEOUT_KEEP_SYNTHESIS_WORKING = setTimeout(KeepSpeechSynthesisActive, 3500);
        }
        btnClass('fa-pause')
        btnDisplay('none');
        synth.speak(utterance)
        speechStatus = 'speaking';


    }
});

function toggleSpeech() {
    if (speechStatus === 'speaking') {
        synth.pause();
        btnClass('fa-play')
        speechStatus = "paused"

    } else {
        synth.resume();
        btnClass('fa-pause')
        speechStatus = "speaking";
    }
}

toggleBtn.addEventListener('click', toggleSpeech);

stopBtn.addEventListener("click", () => {
    synth.cancel();
    speechStatus = "stop"
    btnDisplay('inline-block');
    clearTimeout(TIMEOUT_KEEP_SYNTHESIS_WORKING);
});

utterance.onend = function () {
    btnDisplay('inline-block');
    speechStatus = "stop"
    clearTimeout(TIMEOUT_KEEP_SYNTHESIS_WORKING);
};

speedSelect.addEventListener('change', () => {
    if (window.parent.current_idr === playBtn.getAttribute("data-idr")) {
        synth.cancel();
        utterance.rate = parseFloat(speedSelect.value);
        if (speechStatus === "speaking") {
            synth.speak(utterance);
        }
    }
});

// 监听页面切换chat
function checkChatRadioBlock() {
    const stChatRadioBlock = window.parent.document.querySelector('section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"]:has(div[role="radiogroup"])');
    if (stChatRadioBlock) {
        const config = {
            attributes: true,
            subtree: true
        };
        // 创建MutationObserver实例
        const observer = new MutationObserver((mutationsList, observer) => {
            // 监控到变化时的回调函数
            for (let mutation of mutationsList) {
                if (mutation.type === 'attributes' && mutation.attributeName === 'tabindex') {
                    clearTimeout(TIMEOUT_KEEP_SYNTHESIS_WORKING);
                }
            }
        });
        // 启动MutationObserver
        observer.observe(stChatRadioBlock, config);
    } else {
        setTimeout(checkChatRadioBlock, 500);
    }
}

checkChatRadioBlock()

// 监控页面增删chat
function checkChatButton() {
    let stChatButtonAll = window.parent.document.querySelectorAll('section[data-testid="stSidebar"] button[kind="secondary"]');
    if (stChatButtonAll.length === 2) {
        stChatButtonAll.forEach(stChatButton => {
            stChatButton.addEventListener('click', function () {
                clearTimeout(TIMEOUT_KEEP_SYNTHESIS_WORKING);
            })

        })
    } else {
        setTimeout(checkChatButton, 500);
    }
}

checkChatButton()

//// copy.js
copyButton.addEventListener('click', () => {
    let data_idr = playBtn.getAttribute("data-idr")
    let text = window.parent.document.querySelector(`div[data-idr="${data_idr}"]`).innerText
    navigator.clipboard.writeText(text)
        // .then(() => {
        //     // copyTips.classList.add('copy-success');
        //     // copyTips.innerText = '复制成功';
        //     setTimeout(() => {
        //         // copyTips.classList.remove('copy-success');
        //         // copyTips.innerText = '点击复制';
        //     }, 1500);
        // })
        .catch((err) => {
            console.error('无法复制到剪贴板：', err);
        });
});


//// delete.js
if (!("deleteCount" in window.parent)) {
    window.parent.deleteCount = 0
}

deleteButton.addEventListener('click', () => {
    sendDataToPython({
        "value":
            {
                'deleteCount': window.parent.deleteCount
            }
    })
    window.parent.deleteCount += 1
})

// 设置组件高度
window.addEventListener("DOMContentLoaded", function () {
    setFrameHeight(21)
});

// 监控双击事件
document.body.addEventListener("dblclick", function () {
    window.parent.document.dispatchEvent(new Event('dblclick'));
});


// 评分功能
const rateBtn = document.getElementById('rate-btn');
const starRatings = document.querySelectorAll('.star-rating');
let currentRatings = {
    fluency: 0,
    usefulness: 0,
    safety: 0
};

// 为每个评分类型创建星星
starRatings.forEach(ratingContainer => {
    for (let i = 1; i <= 5; i++) {  // 改为 5 颗星以节省空间
        const star = document.createElement('span');
        star.innerHTML = '&#9733;'; // Unicode 星形字符
        star.classList.add('star');
        star.dataset.value = i;
        ratingContainer.appendChild(star);
    }
});

// 处理星级评分
starRatings.forEach(ratingContainer => {
    ratingContainer.addEventListener('click', (e) => {
        if (e.target.classList.contains('star')) {
            const clickedValue = parseInt(e.target.dataset.value);
            const ratingType = ratingContainer.dataset.ratingType;
            currentRatings[ratingType] = clickedValue;
            updateStars(ratingContainer, clickedValue);
            sendRating();
        }
    });

    // 添加鼠标悬停效果
    ratingContainer.addEventListener('mouseover', (e) => {
        if (e.target.classList.contains('star')) {
            const hoverValue = parseInt(e.target.dataset.value);
            updateStars(ratingContainer, hoverValue);
        }
    });

    ratingContainer.addEventListener('mouseout', () => {
        const ratingType = ratingContainer.dataset.ratingType;
        updateStars(ratingContainer, currentRatings[ratingType]);
    });
});

function updateStars(container, value) {
    const stars = container.querySelectorAll('.star');
    stars.forEach((star, index) => {
        star.classList.toggle('active', index < value);
    });
}

function sendRating() {
    sendDataToPython({
        "value":
        {
            "ratings": currentRatings,
        }
    });
}

// 评分按钮点击事件（可选：用于重置或提交）
rateBtn.addEventListener('click', () => {
    // 重置所有评分
    // console.log("Click")
    sendDataToPython({
        "value":
        {
            "clicked": true
        }
    })
    // currentRatings = { fluency: 0, usefulness: 0, safety: 0 };
    // starRatings.forEach(container => updateStars(container, 0));
});
