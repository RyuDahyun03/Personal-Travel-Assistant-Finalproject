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

def generate_collage(images, text):
    num_images = len(images)

    grid_map = {2: 2, 3: 3, 4: 4}
    grid_size = grid_map[num_images]

    collage = Image.new("RGB", (FINAL_WIDTH, FINAL_HEIGHT), "white")

    text_space = 300
    image_area_height = FINAL_HEIGHT - text_space

    cell_width = FINAL_WIDTH // grid_size
    cell_height = image_area_height // grid_size

    idx = 0
    for row in range(grid_size):
        for col in range(grid_size):
            if idx < num_images:
                img = images[idx]
            else:
                img = images[-1]

            resized = img.resize((cell_width, cell_height))

            x = col * cell_width
            y = row * cell_height
            collage.paste(resized, (x, y))
            idx += 1

    draw = ImageDraw.Draw(collage)
    font_size = 80
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    text_x = FINAL_WIDTH // 2
    text_y = FINAL_HEIGHT - (text_space // 2)

    draw.text((text_x, text_y), text, fill="black", anchor="mm", font=font)

    return collage


def run_mode_collage():
    st.subheader("📸 인생네컷 세로 콜라주 생성기")

    uploaded_files = st.file_uploader(
        "사진을 업로드하세요 (2~4장)",
        type=["jpg", "png"],
        accept_multiple_files=True
    )

    user_text = st.text_input("사진 하단에 들어갈 문구", "")

    if uploaded_files:
        if not (2 <= len(uploaded_files) <= 4):
            st.error("사진은 2~4장까지만 업로드할 수 있습니다.")
            return

        images = [Image.open(f).convert("RGB") for f in uploaded_files]

        if st.button("📷 콜라주 생성"):
            collage = generate_collage(images, user_text)
            st.image(collage, caption="생성된 인생네컷", use_column_width=True)

            img_bytes = io.BytesIO()
            collage.save(img_bytes, format="JPEG")
            img_bytes.seek(0)

            st.download_button(
                label="📥 다운로드 (JPEG)",
                data=img_bytes,
                file_name="collage.jpg",
                mime="image/jpeg"
            )


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
