#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import sys
import time
import rembg
import os

rembg_session = None
cascade_path_default = os.path.join(os.getcwd(), 'lbpcascade_animeface.xml')
cascade = None

def image_setting(image, cascade_path=None, model_name='isnet-anime', skip_reshape=False):
    global rembg_session
    global cascade_path_default
    global cascade

    if not skip_reshape:
        if cascade_path is None:
            cascade_path = cascade_path_default
        if cascade is None:
            cascade = cv2.CascadeClassifier(cascade_path)

        if image.shape[2] == 4:
            image_gray = cv2.cvtColor(image, cv2.COLOR_RGBA2GRAY)
        elif image.shape[2] == 3:
            image_gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        image_gray = cv2.equalizeHist(image_gray)

        for min_neighbors in range(2, 6):
            faces = cascade.detectMultiScale(image_gray, minNeighbors=min_neighbors)
            if len(faces) == 1:
                break
        if len(faces) != 1:
            print('Error: Detect faces: ' + str(len(faces)), file=sys.stderr)
            return None
        
        x, y, w, h = faces[0]
        src_pts = np.float32([[x, y - h * 0.15], [x + w, y - h * 0.15], [x + w, y + h * 0.85]])
        DST_PADDING = 16
        dst_pts = np.float32([[192 + DST_PADDING, 64 + DST_PADDING], [320 - DST_PADDING, 64 + DST_PADDING], [320 - DST_PADDING, 192 - DST_PADDING]])

        mat = cv2.getAffineTransform(src_pts, dst_pts)
        dst = cv2.warpAffine(image, mat, (512, 512))

        crop_src_pts = np.float32([[[0.0, 0.0]], [[image.shape[1], image.shape[0]]]])
        result_box = cv2.transform(crop_src_pts, mat)
        crop_pts = [int(result_box[0, 0, 0]) + 1, int(result_box[0, 0, 1]) + 1, int(result_box[1, 0, 0]), int(result_box[1, 0, 1])]

        if 256 - crop_pts[0] > crop_pts[2] - 256:
            crop_pts[2] += (256 - crop_pts[0]) - (crop_pts[2] - 256)
        else:
            crop_pts[0] -= (crop_pts[2] - 256) - (256 - crop_pts[0])

        if crop_pts[0] < 0:
            crop_pts[0] = 0
        if crop_pts[1] < 0:
            crop_pts[1] = 0
        if crop_pts[2] > 512:
            crop_pts[2] = 512
        if crop_pts[3] > 512:
            crop_pts[3] = 512
    else:
        dst = image
        crop_pts = [0, 0, 512, 512]

    if image.shape[2] != 4 or image[0, 0, 3] >= 255:
        if rembg_session is None:
            rembg_session = rembg.new_session(model_name)
        dst = rembg.remove(dst, session=rembg_session)

    return dst, crop_pts

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', '-i')
    parser.add_argument('--output', '-o')
    parser.add_argument('--cascade', '-c', default='./lbpcascade_animeface.xml')
    args = parser.parse_args()

    image = cv2.imread(args.input, -1)

    result, _ = image_setting(image, args.cascade)

    if result is not None:
        cv2.imwrite(args.output, result)