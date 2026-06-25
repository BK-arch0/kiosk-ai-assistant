# -*- coding: utf-8 -*-
import cv2, numpy as np, onnxruntime as ort

# ====== 설정 ======
ONNX_FILE = "yolov5_kiosk.onnx"
INPUT_SIZE = 640

from dataset.classes import CLASS_NAMES
CONF_TH, IOU_TH = 0.4, 0.45
# ==================

sess = ort.InferenceSession(ONNX_FILE, providers=["CPUExecutionProvider"])
inp = sess.get_inputs()[0].name

def detect(img):
    h0, w0 = img.shape[:2]
    blob = cv2.resize(img, (INPUT_SIZE, INPUT_SIZE))[:, :, ::-1].transpose(2,0,1)
    blob = np.ascontiguousarray(blob, np.float32)[None] / 255.0
    pred = sess.run(None, {inp: blob})[0][0]   # (25200, 14)

    obj = pred[:,4]; cls = pred[:,5:]
    cid = cls.argmax(1); conf = obj * cls[np.arange(len(cls)), cid]
    m = conf > CONF_TH
    pred, conf, cid = pred[m], conf[m], cid[m]
    if len(pred) == 0: return []

    cx,cy,w,h = pred[:,0],pred[:,1],pred[:,2],pred[:,3]
    x1=(cx-w/2)/INPUT_SIZE*w0; y1=(cy-h/2)/INPUT_SIZE*h0
    x2=(cx+w/2)/INPUT_SIZE*w0; y2=(cy+h/2)/INPUT_SIZE*h0

    idx = cv2.dnn.NMSBoxes(
        np.stack([x1,y1,x2-x1,y2-y1],1).tolist(), conf.tolist(), CONF_TH, IOU_TH)
    out = []
    for i in np.array(idx).flatten():
        out.append({"class": CLASS_NAMES[cid[i]],
                    "box": [float(x1[i]),float(y1[i]),float(x2[i]),float(y2[i])],
                    "conf": float(conf[i])})
    return out

if __name__ == "__main__":
    img = cv2.imread("test.png")   # 키오스크 사진 한 장을 aid 폴더에 넣고
    if img is None:
        print("test.jpg 를 aid 폴더에 넣어주세요.")
    else:
        H, W = img.shape[:2]
        dets = detect(img)
        print("탐지 결과:", dets)
        from voice.kiosk_guide_1 import reset_guide, guide_once
        reset_guide()
        guide_once(dets, W, H)
