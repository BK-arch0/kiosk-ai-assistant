# -*- coding: utf-8 -*-
"""
키오스크 안내 음성(TTS) 로직
"""

# 음성 출력
import os
try:
    from gtts import gTTS
except ImportError:
    gTTS = None

# 확신도가 이 값보다 낮은 탐지는 무시한다 (오탐 방지)
CONF_THRESHOLD = 0.4
# 음성(TTS) 여부
USE_TTS = True
_last_screen = None


# 모델이 준 박스 좌표를 보고 사람이 알아듣는 위치 표현으로 바꿔준다.

def box_center(box):
    """박스의 중심점 (cx, cy)을 계산한다."""
    x1, y1, x2, y2 = box
    return (x1 + x2) / 2, (y1 + y2) / 2

def vertical_position(box, H):
    """박스가 화면의 위/가운데/아래 중 어디에 있는지 글자로 돌려준다."""
    _, cy = box_center(box)
    if cy < H * 0.33: return "상단"
    elif cy > H * 0.66: return "하단"
    else: return "가운데"

def horizontal_position(box, W):
    """박스가 화면의 왼쪽/가운데/오른쪽 중 어디에 있는지 글자로 돌려준다."""
    cx, _ = box_center(box)
    if cx < W * 0.33: return "왼쪽"
    elif cx > W * 0.66: return "오른쪽"
    else: return "가운데"


# 탐지 결과에서 원하는 클래스만 골라낸다.

def filter_by_conf(detections):
    """확신도가 기준 이상인 것만 남긴다."""
    return [d for d in detections if d.get("conf", 1.0) >= CONF_THRESHOLD]

def get_by_class(detections, class_name):
    """특정 클래스의 탐지들만 리스트로 돌려준다. (없으면 빈 리스트)"""
    return [d for d in detections if d["class"] == class_name]

def has_class(detections, class_name):
    """특정 클래스가 화면에 있는지 True/False로 돌려준다."""
    return len(get_by_class(detections, class_name)) > 0


# 안내 멘트를 생성한다.

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
        if avg_cy < H * 0.3: msg += "카테고리는 화면 상단에 있어요."
        elif avg_cy > H * 0.7: msg += "카테고리는 화면 하단에 있어요."
    return msg

def guide_nav_arrow(detections, W, H):
    """2-2. 화면 넘기기 화살표 안내. (카테고리/메뉴 화면에서 호출됨)"""
    arrows = get_by_class(detections, "nav_arrow")
    if not arrows: return ""
    cx, cy = box_center(arrows[0]["box"])
    if cx < W * 0.15: return "화면 왼쪽의 화살표를 누르면 이전 메뉴로 갈 수 있어요. "
    elif cx > W * 0.85: return "화면 오른쪽의 화살표를 누르면 다음 메뉴로 갈 수 있어요. "
    elif cy > H * 0.8: return "화면 아래쪽의 화살표를 누르면 메뉴를 더 볼 수 있어요. "
    else: return "화살표를 누르면 다음 화면으로 넘어갈 수 있어요. "

def guide_option(detections, W, H):
    """2-3. 옵션(사이즈/온도) 선택 화면"""
    return ("사이즈와 온도를 선택해주세요. 차갑게 드시려면 아이스, 따뜻하게 드시려면 핫을 눌러주세요.")

def guide_pay(detections, W, H):
    """결제 버튼 안내"""
    pays = get_by_class(detections, "pay_button")
    if not pays: return ""
    pos = vertical_position(pays[0]["box"], H)
    return f"이대로 결제하시려면 화면 {pos}의 주문하기 버튼을 눌러주세요."

def guide_cancel(detections, W, H):
    """삭제(취소) 버튼 안내"""
    cancels = get_by_class(detections, "cancel_button")
    if not cancels: return ""
    pos = vertical_position(cancels[0]["box"], H)
    return (f"메뉴를 삭제하시려면 담은 메뉴 옆의 X 버튼을 누르시거나, "
            f"화면 {pos}의 전체 삭제 버튼을 눌러주세요.")

def guide_membership(detections, W, H):
    """3. 멤버십 적립 화면"""
    return ("멤버십을 적립하시려면 전화번호를 입력해주세요. 적립하지 않으시려면 적립 안 함을 눌러주세요.")

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


# TTS(음성 출력) 

def speak(text):
    print(f"[음성출력] {text}")
    if not USE_TTS or not text or not text.strip(): return
    tts = gTTS(text=text, lang="ko")
    tts.save("guide.mp3")
    os.system("start guide.mp3") # Mac은 afplay, Linux는 mpg123 사용


# =====================================================================
# 5-2. 반복 방지 
# 화면이 바뀌었을 때만 새로 안내한다.

def guide_once(detections, W, H):
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
