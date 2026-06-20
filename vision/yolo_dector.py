import os
import cv2
import numpy as np
import onnxruntime as ort

class KioskDetector:

    # YOLOv5 ONNX 모델 초기화 및 가중치 로드
    def __init__(self, model_path="yolov5_kiosk.onnx", img_size=640, conf_thresh=0.25, iou_thresh=0.45):
        self.img_size = img_size
        self.conf_thresh = conf_thresh
        self.iou_thresh = iou_thresh
        
        # 데이터 라벨링 클래스
        self.class_names = [
            "cancel_button",
            "category_tab",
            "dine_option",
            "membership_button",
            "menu_item",
            "nav_arrow",
            "option_button",
            "pay_button",
            "payment_method"
        ]
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"가중치 파일({model_path})을 찾을 수 없습니다. 경로를 확인해주세요.")
            
        self.session = ort.InferenceSession(
            model_path,
            providers=["CPUExecutionProvider"]
        )
        self.input_name = self.session.get_inputs()[0].name

    # BGR 이미지 → YOLOv5 입력 텐서 (Letterbox 적용)
    def _preprocess(self, img_bgr):
        h, w = img_bgr.shape[:2]
        scale = min(self.img_size / w, self.img_size / h)
        nw, nh = int(w * scale), int(h * scale)

        img_resized = cv2.resize(img_bgr, (nw, nh))
        canvas = np.full((self.img_size, self.img_size, 3), 114, dtype=np.uint8)
        pad_x = (self.img_size - nw) // 2
        pad_y = (self.img_size - nh) // 2
        canvas[pad_y:pad_y+nh, pad_x:pad_x+nw] = img_resized

        img_rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        tensor = img_rgb.transpose(2, 0, 1)[np.newaxis].astype(np.float32) / 255.0
        return tensor, scale, pad_x, pad_y

    # [center_x, center_y, width, height] → [x1, y1, x2, y2] 변환
    def _xywh2xyxy(self, x):
        out = x.copy()
        out[..., 0] = x[..., 0] - x[..., 2] / 2  # x1
        out[..., 1] = x[..., 1] - x[..., 3] / 2  # y1
        out[..., 2] = x[..., 0] + x[..., 2] / 2  # x2
        out[..., 3] = x[..., 1] + x[..., 3] / 2  # y2
        return out

    # 중복 바운딩 박스 제거
    def _nms(self, boxes, scores):
        x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
        areas = (x2 - x1) * (y2 - y1)
        order = scores.argsort()[::-1]
        keep = []
        
        while order.size > 0:
            i = order[0]
            keep.append(i)
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            
            inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
            iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
            order = order[np.where(iou <= self.iou_thresh)[0] + 1]
            
        return keep

    # YOLOv5 raw output → 필터링된 결과 리스트 반환
    def _postprocess(self, raw_output, scale, pad_x, pad_y, orig_w, orig_h):
        pred = np.squeeze(raw_output[0])
        nc = len(self.class_names)
        
        boxes_xywh = pred[:, :4]    
        obj_conf = pred[:, 4]      
        class_probs = pred[:, 5:5+nc]
        
        class_ids = class_probs.argmax(axis=1)
        scores = class_probs.max(axis=1) * obj_conf
        
        mask = scores > self.conf_thresh
        boxes_xywh, scores, class_ids = boxes_xywh[mask], scores[mask], class_ids[mask]
        
        if len(scores) == 0:
            return []
        
        boxes_xyxy = self._xywh2xyxy(boxes_xywh)
        boxes_xyxy[:, [0, 2]] = (boxes_xyxy[:, [0, 2]] - pad_x) / scale
        boxes_xyxy[:, [1, 3]] = (boxes_xyxy[:, [1, 3]] - pad_y) / scale
        boxes_xyxy[:, 0] = np.clip(boxes_xyxy[:, 0], 0, orig_w)
        boxes_xyxy[:, 1] = np.clip(boxes_xyxy[:, 1], 0, orig_h)
        boxes_xyxy[:, 2] = np.clip(boxes_xyxy[:, 2], 0, orig_w)
        boxes_xyxy[:, 3] = np.clip(boxes_xyxy[:, 3], 0, orig_h)
        
        # 클래스가 다르면 서로 지우지 않도록 offset 추가
        max_wh = 4096
        c = class_ids * max_wh
        boxes_for_nms = boxes_xyxy + c[:, np.newaxis] # 각 클래스별로 박스 좌표를 멀리 떨어뜨림
        
        keep = self._nms(boxes_for_nms, scores)
        
        return [
            {
                "box"     : [int(coord) for coord in boxes_xyxy[i]], 
                "score"   : float(scores[i]),
                "class_id": int(class_ids[i]),
                "label"   : self.class_names[int(class_ids[i])],
            }
            for i in keep
        ]

    # 이미지를 넣어주면 탐지 결과 리스트를 리턴
    def detect(self, img_bgr):
        h, w = img_bgr.shape[:2]
        tensor, scale, pad_x, pad_y = self._preprocess(img_bgr)
        raw = self.session.run(None, {self.input_name: tensor})
        return self._postprocess(raw, scale, pad_x, pad_y, w, h)