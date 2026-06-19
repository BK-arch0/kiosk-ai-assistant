# -*- coding: utf-8 -*-
"""
키오스크 안내 음성(TTS) 로직 - 가짜 데이터 버전
======================================================
A.I.D 팀 / 키오스크 이용 보조 서비스

[이 파일이 하는 일]
- YOLO 모델이 화면에서 버튼을 찾아 결과를 주면(아직 모델이 없으니 '가짜 데이터'로 흉내),
  그 결과를 보고 "지금 어느 화면인지" 판단하고, 상황에 맞는 안내 멘트를 만든다.
- 멘트는 우선 print로 확인하고, 맨 아래에서 TTS(음성)로 내보내는 부분을 켜면 실제로 소리가 난다.

[나중에 할 일]
- 아래 MOCK_RESULTS(가짜 데이터) 자리에 박보경 님 YOLO 모델의 진짜 출력을 끼우면 그대로 작동한다.
- 즉, 모델 없이 지금 로직을 완성해두고, 모델이 나오면 데이터만 바꿔치기한다.
"""


# =====================================================================
# 0. 모델 출력 형식
# ---------------------------------------------------------------------
# YOLO 모델은 화면에서 찾은 버튼들을 아래와 같은 형식의 리스트로 준다고 약속한다.
#
#   detections = [
#       {"class": "pay_button", "box": [x1, y1, x2, y2], "conf": 0.92},
#       {"class": "cancel_button", "box": [x1, y1, x2, y2], "conf": 0.88},
#       ...
#   ]
#
#   - class : 버튼 종류 (우리가 정한 클래스 8개 중 하나)
#   - box   : [좌상단 x, 좌상단 y, 우하단 x, 우하단 y]  (픽셀 좌표)
#   - conf  : 모델의 확신도 (0~1). 낮으면 잘못 찾았을 수 있음.
#
# 화면 크기(W, H)도 함께 받는다. (스마트폰 카메라 해상도)
# =====================================================================

# 우리가 라벨링하는 클래스 8개 (명세 기준)
CLASSES = [
    "dine_option",       # 포장/매장 선택
    "category_tab",      # 카테고리 탭 (커피/논커피/스무디 등) - 개별
    "nav_arrow",         # 화면 넘기기 화살표
    "option_button",     # 옵션 (사이즈/온도/샷추가 등) - 묶음
    "pay_button",        # 결제 버튼
    "cancel_button",     # 삭제 버튼 (개별X/전체삭제 묶음)
    "membership_button", # 멤버십 적립
    "payment_method",    # 결제 방법 (카드/페이 등) - 묶음
]

# 확신도가 이 값보다 낮은 탐지는 무시한다 (오탐 방지). 나중에 조정 가능.
CONF_THRESHOLD = 0.4

# 음성(TTS)을 실제로 켤지 여부.
#  - False : 글자만 출력 (조용함, 여러 상황 한꺼번에 확인할 때 좋음)
#  - True  : 실제 음성 재생 (gTTS 필요, 인터넷 필요)
USE_TTS = False


# =====================================================================
# 1. 좌표 → 위치 표현 도우미 함수
# ---------------------------------------------------------------------
# 모델이 준 박스 좌표를 보고 "상단/하단", "왼쪽/오른쪽" 같은
# 사람이 알아듣는 위치 표현으로 바꿔준다.
# =====================================================================

def box_center(box):
    """박스의 중심점 (cx, cy)을 계산한다."""
    x1, y1, x2, y2 = box
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    return cx, cy


def vertical_position(box, H):
    """박스가 화면의 위/가운데/아래 중 어디에 있는지 글자로 돌려준다."""
    _, cy = box_center(box)
    if cy < H * 0.33:
        return "상단"
    elif cy > H * 0.66:
        return "하단"
    else:
        return "가운데"


def horizontal_position(box, W):
    """박스가 화면의 왼쪽/가운데/오른쪽 중 어디에 있는지 글자로 돌려준다."""
    cx, _ = box_center(box)
    if cx < W * 0.33:
        return "왼쪽"
    elif cx > W * 0.66:
        return "오른쪽"
    else:
        return "가운데"


# =====================================================================
# 2. 탐지 결과에서 원하는 클래스만 골라내는 도우미
# =====================================================================

def filter_by_conf(detections):
    """확신도가 기준 이상인 것만 남긴다."""
    return [d for d in detections if d.get("conf", 1.0) >= CONF_THRESHOLD]


def get_by_class(detections, class_name):
    """특정 클래스의 탐지들만 리스트로 돌려준다. (없으면 빈 리스트)"""
    return [d for d in detections if d["class"] == class_name]


def has_class(detections, class_name):
    """특정 클래스가 화면에 있는지 True/False로 돌려준다."""
    return len(get_by_class(detections, class_name)) > 0


# =====================================================================
# 3. 화면 단계 판단
# =====================================================================
# 4. 화면별 안내 멘트 생성
# ---------------------------------------------------------------------
# 각 버튼 종류마다 멘트를 만든다. detections와 화면크기(W,H)를 받는다.
# =====================================================================

def guide_dine(detections, W, H):
    """1. 포장/매장 선택 화면"""
    return "가져가실 거면 포장, 카페에서 드실 거면 매장을 눌러주세요."


def guide_category(detections, W, H):
    """카테고리 선택 안내 (화살표는 make_guidance에서 따로 처리)"""
    msg = "마시고 싶은 종류를 선택해주세요. 예를 들어 아메리카노, 라떼 종류는 커피를 눌러주세요. "

    # 카테고리 탭이 화면 위/아래 어디에 있는지 안내
    tabs = get_by_class(detections, "category_tab")
    if tabs:
        # 여러 탭의 평균 위치로 상단/하단 판단
        avg_cy = sum(box_center(t["box"])[1] for t in tabs) / len(tabs)
        if avg_cy < H * 0.3:
            msg += "카테고리는 화면 상단에 있어요."
        elif avg_cy > H * 0.7:
            msg += "카테고리는 화면 하단에 있어요."

    return msg


def guide_nav_arrow(detections, W, H):
    """2-2. 화면 넘기기 화살표 안내. (카테고리/메뉴 화면에서 호출됨)"""
    arrows = get_by_class(detections, "nav_arrow")

    # 화살표가 없으면 아무 안내도 하지 않음 (다음 화면이 없을 수도 있으므로)
    if not arrows:
        return ""

    # 화살표가 있으면 첫 번째 화살표 위치로 안내
    box = arrows[0]["box"]
    cx, cy = box_center(box)

    if cx < W * 0.15:
        return "화면 왼쪽의 화살표를 누르면 이전 메뉴로 갈 수 있어요. "
    elif cx > W * 0.85:
        return "화면 오른쪽의 화살표를 누르면 다음 메뉴로 갈 수 있어요. "
    elif cy > H * 0.8:
        return "화면 아래쪽의 화살표를 누르면 메뉴를 더 볼 수 있어요. "
    else:
        return "화살표를 누르면 다음 화면으로 넘어갈 수 있어요. "


def guide_option(detections, W, H):
    """2-3. 옵션(사이즈/온도) 선택 화면"""
    return ("사이즈와 온도를 선택해주세요. "
            "차갑게 드시려면 아이스, 따뜻하게 드시려면 핫을 눌러주세요.")


def guide_pay(detections, W, H):
    """결제 버튼 안내"""
    pays = get_by_class(detections, "pay_button")
    if not pays:
        return ""
    pos = vertical_position(pays[0]["box"], H)
    return f"이대로 결제하시려면 화면 {pos}의 주문하기 버튼을 눌러주세요."


def guide_cancel(detections, W, H):
    """삭제(취소) 버튼 안내"""
    cancels = get_by_class(detections, "cancel_button")
    if not cancels:
        return ""
    pos = vertical_position(cancels[0]["box"], H)
    return (f"메뉴를 삭제하시려면 담은 메뉴 옆의 X 버튼을 누르시거나, "
            f"화면 {pos}의 전체 삭제 버튼을 눌러주세요.")


def guide_membership(detections, W, H):
    """3. 멤버십 적립 화면"""
    return ("멤버십을 적립하시려면 전화번호를 입력해주세요. "
            "적립하지 않으시려면 적립 안 함을 눌러주세요.")


def guide_payment(detections, W, H):
    """4. 결제 방법 선택 화면"""
    return "결제 방법을 선택해주세요. 카드 또는 간편결제 중에서 고르시면 됩니다."


def make_guidance(detections, W, H):
    """
    전체 흐름: 탐지 결과 -> 보이는 버튼마다 안내를 이어붙임

    한 화면에 카테고리/화살표/결제/삭제가 같이 떠 있어도,
    보이는 것마다 해당 안내를 모두 만들어서 이어붙인다.

    돌려주는 값:
      - signature : 지금 화면에 무엇이 보이는지 요약한 문자열 (반복 방지용)
      - text      : 이어붙인 최종 안내 멘트
    """
    # 1) 확신도 낮은 탐지 제거
    detections = filter_by_conf(detections)

    parts = []  # 안내 조각들을 순서대로 모은다

    # --- 안내 우선순위(말하는 순서) ---
    # 먼저 "지금 뭘 골라야 하는지"(메인 동작)부터,
    # 그 다음 "결제/삭제 같은 마무리 동작"을 안내한다.

    # 1) 포장/매장 (첫 화면)
    if has_class(detections, "dine_option"):
        parts.append(guide_dine(detections, W, H))

    # 2) 멤버십 (적립 화면)
    if has_class(detections, "membership_button"):
        parts.append(guide_membership(detections, W, H))

    # 3) 결제 방법 선택 화면
    if has_class(detections, "payment_method"):
        parts.append(guide_payment(detections, W, H))

    # 4) 옵션 (사이즈/온도) — 메뉴 담을 때 뜨는 칸
    if has_class(detections, "option_button"):
        parts.append(guide_option(detections, W, H))

    # 5) 카테고리 — 메뉴 고르는 화면
    if has_class(detections, "category_tab"):
        parts.append(guide_category(detections, W, H))

    # 6) 화살표 — 다음/이전 페이지 (있을 때만 멘트가 채워짐)
    arrow_msg = guide_nav_arrow(detections, W, H)
    if arrow_msg:
        parts.append(arrow_msg)

    # 7) 결제 버튼 — 마무리 동작
    if has_class(detections, "pay_button"):
        parts.append(guide_pay(detections, W, H))

    # 8) 삭제 버튼 — 마무리 동작
    if has_class(detections, "cancel_button"):
        parts.append(guide_cancel(detections, W, H))

    # 멘트 합치기
    text = " ".join(p for p in parts if p)

    # 아무것도 못 찾았으면 안내
    if not text:
        text = "화면을 인식하지 못했어요. 카메라를 키오스크 화면에 맞춰주세요."

    # 반복 방지용 서명: 지금 화면에 보이는 클래스 종류를 정렬해 합친 것
    # (같은 버튼 조합이 계속 보이면 같은 서명 → 반복 안 함)
    found = sorted(set(d["class"] for d in detections))
    signature = ",".join(found) if found else "none"

    return signature, text


# =====================================================================
# 5. TTS(음성 출력) - 지금은 꺼두고, 준비되면 켠다
# ---------------------------------------------------------------------
# 멘트(문자열)를 실제 음성으로 내보내는 부분.
# 두 가지 방법 중 하나를 쓰면 된다. (자세한 설치법은 파일 맨 아래 주석 참고)
# =====================================================================

def speak(text):
    """
    멘트를 음성으로 내보낸다.
    지금은 print만 한다. 아래 주석을 풀면 실제로 소리가 난다.
    """
    print(f"[음성출력] {text}")

    # USE_TTS 가 True 이면 실제 음성을 내보낸다. (테스트 중엔 False 로 두면 조용함)
    if not USE_TTS:
        return
    
    # 텍스트가 비어 있으면 음성 생성을 건너뛴다 (gTTS는 빈 텍스트에서 에러남)
    if not text or not text.strip():
        return

    # --- 방법 A: gTTS (구글, 한국어 자연스러움, 인터넷 필요) ---
    from gtts import gTTS
    import os
    tts = gTTS(text=text, lang="ko")
    tts.save("guide.mp3")
    os.system("start guide.mp3")     # 윈도우 (기본 플레이어로 mp3 재생)
    # os.system("afplay guide.mp3")  # 맥
    # os.system("mpg123 guide.mp3")  # 리눅스

    # --- 방법 B: pyttsx3 (오프라인, 인터넷 불필요) ---
    # 위 gTTS 대신 이걸 쓰려면 위 gTTS 부분을 주석 처리하고 아래 주석을 풀면 됨.
    # import pyttsx3
    # engine = pyttsx3.init()
    # engine.say(text)
    # engine.runAndWait()


# =====================================================================
# 5-2. 반복 방지 
# ---------------------------------------------------------------------
# 카메라는 1초에도 같은 화면을 수십 번 비추므로
# "화면이 바뀌었을 때만" 새로 안내하도록 한다.
# =====================================================================

# 직전에 안내했던 화면 단계를 기억해 둔다. (처음엔 아무것도 없음)
_last_screen = None


def guide_once(detections, W, H):
    """
    화면이 직전과 '달라졌을 때만' 음성으로 안내한다.
    같은 화면이 계속 들어오면 조용히 넘어간다.

    실전에서는 카메라 프레임마다 이 함수를 계속 호출하면 된다.
    그러면 사용자가 다음 화면으로 넘어갈 때만 새 멘트가 나간다.
    """
    global _last_screen

    screen, text = make_guidance(detections, W, H)

    # 화면이 직전과 같으면 → 아무 말도 하지 않음
    if screen == _last_screen:
        return None

    # 화면이 바뀌었으면 → 안내하고, 현재 화면을 기억
    _last_screen = screen
    speak(text)
    return text


def reset_guide():
    """안내 기록을 초기화한다. (처음부터 다시 시작할 때)"""
    global _last_screen
    _last_screen = None


# =====================================================================
# 6. 가짜 데이터로 테스트 (★ 모델 없이 지금 확인하는 부분 ★)
# ---------------------------------------------------------------------
# 실제 모델 출력을 흉내낸 여러 상황을 만들어서, 멘트가 잘 나오는지 본다.
# 스마트폰 화면을 세로 1080 x 1920 이라고 가정한다.
# =====================================================================

if __name__ == "__main__":
    W, H = 1080, 1920  # 가정한 화면 크기 (가로, 세로)

    # 여러 가짜 상황들. 실제 모델이 줄 결과를 흉내낸 것.
    test_cases = {
        "① 포장/매장 화면": [
            {"class": "dine_option", "box": [150, 1500, 500, 1700], "conf": 0.95},
            {"class": "dine_option", "box": [600, 1500, 950, 1700], "conf": 0.93},
        ],
        "② 카테고리 화면 (탭 상단 + 오른쪽 화살표)": [
            {"class": "category_tab", "box": [100, 300, 300, 400], "conf": 0.9},
            {"class": "category_tab", "box": [350, 300, 550, 400], "conf": 0.88},
            {"class": "category_tab", "box": [600, 300, 800, 400], "conf": 0.91},
            {"class": "nav_arrow",    "box": [980, 850, 1060, 1050], "conf": 0.85},
        ],
        "③ 카테고리 화면 (화살표 없음 → 끌어내리기)": [
            {"class": "category_tab", "box": [100, 300, 300, 400], "conf": 0.9},
            {"class": "category_tab", "box": [350, 300, 550, 400], "conf": 0.87},
        ],
        "④ 옵션 화면": [
            {"class": "option_button", "box": [200, 800, 500, 950], "conf": 0.9},
            {"class": "option_button", "box": [600, 800, 900, 950], "conf": 0.89},
        ],
        "⑤ 장바구니 화면 (결제+취소, 둘 다 하단)": [
            {"class": "pay_button",    "box": [700, 1700, 1000, 1850], "conf": 0.95},
            {"class": "cancel_button", "box": [400, 1700, 650, 1850], "conf": 0.8},
        ],
        "⑥ 멤버십 화면": [
            {"class": "membership_button", "box": [300, 1200, 800, 1400], "conf": 0.92},
        ],
        "⑦ 결제 방법 화면": [
            {"class": "payment_method", "box": [200, 900, 500, 1100], "conf": 0.9},
            {"class": "payment_method", "box": [600, 900, 900, 1100], "conf": 0.88},
        ],
        "⑧ 아무것도 못 찾음": [],
        "⑨ 확신도 낮은 오탐 (무시되어야 함)": [
            {"class": "pay_button", "box": [700, 100, 900, 200], "conf": 0.2},
        ],
        "⑩ 공차형 한 화면 (카테고리+화살표+삭제+결제 동시)": [
            # 상단 카테고리 탭들
            {"class": "category_tab", "box": [80, 540, 250, 620], "conf": 0.9},
            {"class": "category_tab", "box": [280, 540, 420, 620], "conf": 0.88},
            {"class": "category_tab", "box": [450, 540, 650, 620], "conf": 0.9},
            # 하단 '다음' 화살표 (오른쪽)
            {"class": "nav_arrow",    "box": [950, 1750, 1050, 1820], "conf": 0.85},
            # 오른쪽 '전체삭제' 버튼
            {"class": "cancel_button","box": [880, 800, 1040, 870], "conf": 0.8},
            # 우하단 '주문하기' 결제 버튼
            {"class": "pay_button",   "box": [880, 1750, 1060, 1880], "conf": 0.92},
        ],
    }

    # 모든 상황을 돌려본다. (글자만 출력)
    print("\n##### [테스트 1] 각 화면별 멘트 확인 #####\n")
    for name, detections in test_cases.items():
        screen, text = make_guidance(detections, W, H)
        print("=" * 60)
        print(f"[상황] {name}")
        print(f"[판단된 화면] {screen}")
        speak(text)
        print()

    # -----------------------------------------------------------------
    # [테스트 2] 반복 방지 확인 (★ 실전 흐름 흉내 ★)
    # -----------------------------------------------------------------
    # 실전에서 카메라는 같은 화면을 계속 비춘다.
    # 아래 stream 은 그 상황을 흉내낸 것:
    #   포장화면 × 3번 → 카테고리화면 × 3번 → 옵션화면 × 2번
    # guide_once 를 쓰면 '화면이 바뀐 순간'에만 멘트가 나가야 한다.
    print("\n##### [테스트 2] 반복 방지 (화면 바뀔 때만 안내) #####\n")

    reset_guide()  # 기록 초기화

    # 같은 화면이 여러 번 연속으로 들어오는 상황 (실전 카메라처럼)
    stream = [
        ("프레임1: 포장화면",   test_cases["① 포장/매장 화면"]),
        ("프레임2: 포장화면",   test_cases["① 포장/매장 화면"]),
        ("프레임3: 포장화면",   test_cases["① 포장/매장 화면"]),
        ("프레임4: 카테고리",   test_cases["② 카테고리 화면 (탭 상단 + 오른쪽 화살표)"]),
        ("프레임5: 카테고리",   test_cases["② 카테고리 화면 (탭 상단 + 오른쪽 화살표)"]),
        ("프레임6: 카테고리",   test_cases["② 카테고리 화면 (탭 상단 + 오른쪽 화살표)"]),
        ("프레임7: 옵션화면",   test_cases["④ 옵션 화면"]),
        ("프레임8: 옵션화면",   test_cases["④ 옵션 화면"]),
    ]

    for name, detections in stream:
        result = guide_once(detections, W, H)
        if result is None:
            print(f"  {name} → (같은 화면, 조용)")
        else:
            print(f"  {name} → 🔊 새 안내 나감!")
    print("\n→ 화면이 바뀐 프레임1·4·7 에서만 안내가 나가면 정상!")

    # -----------------------------------------------------------------
    # 음성으로 들어보고 싶을 때:
    #   1) 위쪽 USE_TTS = True 로 바꾸고
    #   2) 아래 한 상황만 골라서 speak 하면 됨 (한꺼번에 다 틀면 소리가 겹침)
    #
    # 예시) ① 포장/매장 화면만 음성으로 듣기:
    #
    #   _, text = make_guidance(test_cases["① 포장/매장 화면"], W, H)
    #   speak(text)
    # -----------------------------------------------------------------
