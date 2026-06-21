# -*- coding: utf-8 -*-
# 여러 키오스크 사진을 순서대로 보여주며 안내 (시연용)
import cv2, time
import kiosk_guide_1
from kiosk_run import detect   # 기존 detect() 재활용

# 시연할 사진
DEMO_IMAGES = [
    "demo1.png",   # 포장/매장 화면
    "demo2.png",   # 카테고리 화면
    "demo3.png",   # 옵션 화면
    "demo4.png",   # 결제 화면
]

kiosk_guide_1.reset_guide()

for path in DEMO_IMAGES:
    img = cv2.imread(path)
    if img is None:
        print(f"[건너뜀] {path} 없음")
        continue

    H, W = img.shape[:2]
    dets = detect(img)
    print("\n" + "=" * 50)
    print(f"[화면] {path}")
    kiosk_guide_1.guide_once(dets, W, H)   # 음성 안내

    # 화면도 같이 띄워서 보여주기 (아무 키나 누르면 다음 사진)
    target_h = 600
    scale = target_h/H
    show = cv2.resize(img, (int(W*scale), target_h))
    cv2.imshow("kiosk demo", show)
    cv2.waitKey(0)        # 키 누를 때까지 대기 (음성 들을 시간)

cv2.destroyAllWindows()
print("\n시연 종료")
