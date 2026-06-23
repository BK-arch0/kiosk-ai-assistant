# Voice Guidance Module (음성 안내 모듈)

키오스크 화면에서 인식된 버튼 정보를 받아, 
사용자에게 어떤 버튼을 눌러야 하는지 음성(TTS)으로 안내하는 모듈.
학습된 YOLOv5 모델(.onnx)을 연결해 돌리는 데모 실행 코드가 함께 들어 있음


A.I.D 팀 - 디지털 취약계층을 위한 키오스크 이용 보조 서비스

## 동작 흐름

1. YOLO 모델이 화면에서 버튼을 찾아 위치(좌표)와 종류를 알려줌
2. 이 모듈이 "어떤 버튼이 보이는지"에 따라 안내 멘트를 생성
3. 생성된 멘트를 gTTS로 음성 출력
4. 화면이 바뀌었을 때만 새로 안내 (같은 화면 반복 안 함)


## 파일 구성

├── kiosk_run_demo.py         # ★ 데모 실행 파일 (저장된 데모 사진으로 동작 시연)

├── kiosk_run.py              # 실시간 실행 파일 (카메라/실제 입력 연결용)

├── kiosk_guide_1.py          # 음성 안내 모듈 본체 (멘트 생성 + gTTS)

├── yolov5_kiosk.onnx         # 학습된 YOLOv5 버튼 탐지 모델

└── demo1.png, demo2.png ...  # 시연용 키오스크 화면 사진

위 5종(코드 3 + 모델 1 + 데모 사진)을 한 폴더에 함께 두고 kiosk_run_demo.py를 실행.

## 실행 방법

1) 전체 데모 실행 (모델 + 음성 안내)

-bash-

pip install onnxruntime opencv-python numpy gTTS

python kiosk_run_demo.py

데모 사진(demo1.png...)을 차례로 모델에 넣어 버튼을 탐지하고, 그 결과로 음성 안내를 출력.


2) 음성 모듈만 단독 테스트 (모델 없이)

-bash-

pip install gTTS

python kiosk_guide_1.py

가상의 버튼 데이터(test_cases)로 안내 멘트 생성과 음성 출력만 빠르게 확인.

※ 위 패키지 목록은 코드의 실제 import에 맞춰 조정해야함.

※ gTTS는 인터넷 연결이 필요합니다.

## 모델 출력 형식

이 모듈은 YOLO 모델이 아래 형식으로 결과를 준다고 가정.

​```python
detections = [

    {"class": "pay_button", "box": [x1, y1, x2, y2], "conf": 0.92},
    
    ...
    
]

- class : 버튼 종류 (아래 9개 중 하나)
- box   : [좌상단 x, 좌상단 y, 우하단 x, 우하단 y] 픽셀 좌표
- conf  : 확신도 (0~1)

## 클래스 목록 (9개)

| 클래스 | 의미 |
|---|---|
| dine_option | 포장/매장 선택 |
| category_tab | 카테고리 탭 (커피/논커피 등) |
| nav_arrow | 화면 넘기기 화살표 |
| menu_item | 메뉴
| option_button | 옵션 (사이즈/온도 등) |
| pay_button | 결제 버튼 |
| cancel_button | 삭제 버튼 |
| membership_button | 멤버십 적립 |
| payment_method | 결제 방법 선택 |


## 현재 상태

- [x] 화면별 안내 멘트 생성
- [x] 여러 버튼 동시 안내 (한 화면에 카테고리 + 결제 등 같이 있을 때)
- [x] 반복 방지 (화면 바뀔 때만 안내)
- [x] gTTS 음성 출력
- [x] 학습된 YOLOv5(.onnx) 모델과 연결한 데모 실행
