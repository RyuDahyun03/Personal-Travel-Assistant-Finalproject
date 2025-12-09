import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
import json
import random
import base64
import time
import io

st.set_page_config(page_title="AI 여행 플래너", page_icon="✈️", layout="wide")

############################################
# 0. 공통 함수들
############################################

# GPT API 호출 함수
def ask_gpt(system_prompt, user_prompt, model="gpt-4o-mini"):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"
    }
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()["choices"][0]["message"]["content"]


############################################
# 1. 단기 여행 플래너
############################################
def run_mode_single():
    st.subheader("🌍 개인 맞춤형 단기 여행 플래너")

    destination = st.text_input("여행지")
    days = st.number_input("여행 기간 (일)", min_value=1, max_value=30, step=1)
    preference = st.text_input("여행 스타일 (예: 맛집, 관광 등)")

    if st.button("여행 계획 생성"):
        system_prompt = "너는 여행 플래너 AI이다."
        user_prompt = f"목적지: {destination}, 기간: {days}일, 스타일: {preference}로 여행 일정을 만들어줘."
        result = ask_gpt(system_prompt, user_prompt)
        st.write(result)


############################################
# 2. 장기 여행 플래너
############################################
def run_mode_longterm():
    st.subheader("🧳 장기 여행 플래너")

    country = st.text_input("국가")
    budget = st.number_input("예산", min_value=0)
    months = st.number_input("여행 기간 (개월)", min_value=1, max_value=24)

    if st.button("계획 생성"):
        system_prompt = "너는 장기 여행 전문 플래너이다."
        user_prompt = f"국가: {country}, 예산: {budget}, 기간: {months}개월. 현실적 장기 여행 계획 작성."
        st.write(ask_gpt(system_prompt, user_prompt))


############################################
# 3. AI 상담소 (Chat)
############################################
def run_mode_chat():
    st.subheader("💬 AI 여행 상담소")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    user_msg = st.text_input("질문하기")

    if st.button("전송"):
        st.session_state.chat_history.append(("user", user_msg))
        answer = ask_gpt("너는 친절한 여행 상담사이다.", user_msg)
        st.session_state.chat_history.append(("assistant", answer))

    for role, msg in st.session_state.chat_history:
        if role == "user":
            st.markdown(f"**🧑‍💼 질문:** {msg}")
        else:
            st.markdown(f"**🤖 답변:** {msg}")


############################################
# 4. 인생네컷 기능 (새로 추가된 기능)
############################################

FINAL_WIDTH = 1080
FINAL_HEIGHT = 1920

def generate_collage(images, layout="1x4", caption_text="My Travel Cut"):
    from PIL import Image, ImageDraw, ImageFont

    # --- 1. 레이아웃 파싱 (예: "2x2" → rows=2, cols=2) ---
    rows, cols = map(int, layout.lower().split("x"))

    # --- 2. 이미지 리사이즈 설정 ---
    cell_w, cell_h = 500, 500
    margin = 20   # 그리드 여백
    border = 40   # 전체 흰색 테두리

    # --- 3. 캔버스 크기 계산 ---
    collage_w = cols * cell_w + (cols + 1) * margin
    collage_h = rows * cell_h + (rows + 1) * margin + 200  # 아래 텍스트 공간 포함

    # --- 4. 흰 배경 캔버스 ---
    collage = Image.new("RGB", (collage_w + border*2, collage_h + border*2), "white")
    draw = ImageDraw.Draw(collage)

    # --- 5. 각 이미지 채우기 ---
    for idx, img in enumerate(images[:rows*cols]):
        img = img.resize((cell_w, cell_h))
        r = idx // cols
        c = idx % cols

        x = border + margin + c * (cell_w + margin)
        y = border + margin + r * (cell_h + margin)
        collage.paste(img, (x, y))

    # --- 6. 캡션 텍스트 (굵게 + 크게) ---
    try:
        font = ImageFont.truetype("arial.ttf", 80)
    except:
        font = ImageFont.load_default()

    text_w, text_h = draw.textsize(caption_text, font=font)
    text_x = (collage.width - text_w) // 2
    text_y = collage.height - border - text_h - 30

    draw.text((text_x, text_y), caption_text, font=font, fill="black")

    return collage

############################################
# 5. 메인 (AI 화가 기능 완전 삭제됨)
############################################

def main():
    st.title("✨ AI 여행 올인원 플래너")

    app_mode = st.sidebar.radio(
        "모드 선택",
        [
            "개인 맞춤형 (Single)",
            "장기 여행 (Long-term)",
            "AI 상담소 (Chat)",
            "인생네컷 생성기 (Photo Strip)"
        ]
    )

    if app_mode == "개인 맞춤형 (Single)":
        run_mode_single()

    elif app_mode == "장기 여행 (Long-term)":
        run_mode_longterm()

    elif app_mode == "AI 상담소 (Chat)":
        run_mode_chat()

    elif app_mode == "인생네컷 생성기 (Photo Strip)":
        run_mode_collage()


if __name__ == "__main__":
    main()
