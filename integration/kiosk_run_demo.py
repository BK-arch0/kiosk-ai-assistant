# -*- coding: utf-8 -*-
# 여러 키오스크 사진을 순서대로 보여주며 안내 (시연용)
import sys, os
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())

import cv2, time
from voice.kiosk_guide_1 import reset_guide, guide_once
from vision.kiosk_run import detect

# 시연할 사진
DEMO_IMAGES = [
    "images/demo1.jpg",   # 포장/매장 화면
    "images/demo2.jpg",   # 카테고리 화면
    "images/demo3.jpeg",   # 옵션 화면
    "images/demo4.jpeg",   # 결제 화면
]

reset_guide()

for path in DEMO_IMAGES:
    img = cv2.imread(path)
    if img is None:
        print(f"[건너뜀] {path} 없음")
        continue

    H, W = img.shape[:2]
    dets = detect(img)
    print("\n" + "=" * 50)
    print(f"[화면] {path}")
    guide_once(dets, W, H)

    # 화면도 같이 띄워서 보여주기 (아무 키나 누르면 다음 사진)
    target_h = 600
    scale = target_h/H
    show = cv2.resize(img, (int(W*scale), target_h))
    cv2.imshow("kiosk demo", show)
    cv2.waitKey(0)        # 키 누를 때까지 대기 (음성 들을 시간)

cv2.destroyAllWindows()
print("\n시연 종료")
