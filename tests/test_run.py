# vision\yolo_detector.py 작동 확인 코드
# 실행 시 필요한 설치 파일: pip install opencv-python numpy onnxruntime

import os
import sys
import cv2

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vision.yolo_detector import KioskDetector

def test_yolo():
    onnx_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "yolov5_kiosk.onnx")
    
    print("모델을 불러오는 중...")
    try:
        detector = KioskDetector(onnx_path)
    except Exception as e:
        print(f"모델 로딩 실패: {e}")
        return

    # tests 폴더 안에 있는 test.png 로드
    current_dir = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(current_dir, "test.png")
    img = cv2.imread(img_path)
    
    if img is None:
        print(f"에러: '{img_path}' 파일을 찾을 수 없습니다.")
        return

    print("탐지 시작...")
    results = detector.detect(img)
    
    if not results:
        print("탐지된 객체가 없습니다.")
    else:
        print(f"총 {len(results)}개의 객체가 탐지되었습니다!")
        for res in results:
            print(f" - {res['label']} (정확도: {res['score']:.2f})")

    # 결과 시각화
    for res in results:
        x1, y1, x2, y2 = res["box"]
        label_text = f"{res['label']} {res['score']:.2f}"
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(img, label_text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    cv2.imshow("YOLOv5 Test Result", img)
    print("결과 창이 떴습니다. 창을 닫으려면 아무 키나 누르세요.")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    test_yolo()