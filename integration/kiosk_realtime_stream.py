# -*- coding: utf-8 -*-
# 노트북 웹캠용 작동 코드
import sys
import os
import cv2
import time
import threading

# 프로젝트 루트 경로 맞추기
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())

from vision.kiosk_run import detect
from voice.kiosk_guide_1 import reset_guide, guide_once

CAMERA_SOURCE = 0  # 내장 웹캠 혹은 스마트폰 앱 인덱스
WINDOW_TITLE = "AI Kiosk Realtime Stream"

# 스레드 간 데이터 공유를 위한 전역 변수
latest_dets = []
latest_W = 0
latest_H = 0
is_running = True

# 인식된 박스와 FPS를 화면에 그립니다.
def draw_visuals(frame, detections, fps):
    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    for d in detections:
        x1, y1, x2, y2 = map(int, d['box'])
        cls_name = d['class']
        conf = d['conf']
        
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = f"{cls_name} {conf:.2f}"
        cv2.putText(frame, label, (x1, max(y1 - 10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
    return frame

# 메인 카메라 영상이 멈추지 않도록 음성 처리만 전담하는 백그라운드 스레드입니다.
def voice_worker():
    global latest_dets, latest_W, latest_H, is_running
    
    while is_running:
        if latest_W > 0 and latest_H > 0:
            guide_once(latest_dets, latest_W, latest_H)
            
        time.sleep(0.1)  # CPU 과부하 방지용 짧은 휴식

def run_realtime_assistant():
    global latest_dets, latest_W, latest_H, is_running
    
    reset_guide()
    
    # 윈도우 환경 검은 화면 방지용 DSHOW 옵션 및 해상도 세팅
    cap = cv2.VideoCapture(CAMERA_SOURCE, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    if not cap.isOpened():
        print(f"[오류] 카메라({CAMERA_SOURCE}) 연결 실패.")
        return

    print("\n" + "-" * 50)
    print("실시간 AI 키오스크 안내 시작 (음성 비동기 최적화 적용)")
    print("종료 방법: 'q' 키 입력 또는 창의 'X' 버튼 누르기")
    print("-" * 50 + "\n")
    
    v_thread = threading.Thread(target=voice_worker, daemon=True)
    v_thread.start()

    prev_time = time.time()
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        H, W = frame.shape[:2]

        # 1. 비전 인식 (메인 스레드는 여기만 집중)
        dets = detect(frame)
        
        # 2. 인식 결과를 조수 스레드가 가져갈 수 있게 전역 변수에 업데이트
        latest_dets = dets
        latest_W = W
        latest_H = H

        # 3. FPS 연산 및 화면 그리기
        curr_time = time.time()
        fps = 1 / (curr_time - prev_time) if (curr_time - prev_time) > 0 else 0.0
        prev_time = curr_time
        
        frame = draw_visuals(frame, dets, fps)

        # 4. 화면 띄우기
        target_h = 720
        scale = target_h / H
        show_frame = cv2.resize(frame, (int(W * scale), target_h))
        cv2.imshow(WINDOW_TITLE, show_frame)

        # 5. 안전 종료 감지 (q키 또는 X버튼)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        if cv2.getWindowProperty(WINDOW_TITLE, cv2.WND_PROP_VISIBLE) < 1:
            break

    # 루프 탈출 시 정리 작업
    is_running = False  # 조수 스레드도 함께 종료
    cap.release()
    cv2.destroyAllWindows()
    print("\n시스템이 안전하게 종료되었습니다.")

if __name__ == "__main__":
    run_realtime_assistant()