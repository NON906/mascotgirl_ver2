#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

import cv2

from .mascot_image import MascotImage

def make_images(numpy_content, save_dir_path):
    os.makedirs(save_dir_path, exist_ok=True)

    mascot_image = MascotImage()
    mascot_image.upload_image(numpy_content, False)

    eyebrow_options = ["normal", "troubled", "angry", "happy", "serious"]
    eye_options = ["normal", "half", "closed", "happy_closed", "relaxed_closed", "surprized", "wink"]
    eye_values = [[0, 0.0, 0.0], [0, 0.5, 0.5], [0, 1.0, 1.0], [1, 1.0, 1.0], [3, 1.0, 1.0], [2, 1.0, 1.0], [1, 1.0, 0.0]]
    mouth_options = ["normal", "aaa", "iii", "uuu", "eee", "ooo"]

    for eyebrow in eyebrow_options:
        if eyebrow != 'normal':
            mascot_image.set_eyebrow(eyebrow, 1.0, 1.0)
        else:
            mascot_image.set_eyebrow(0, 0.0, 0.0)

        for eye_idx, eye in enumerate(eye_options):
            mascot_image.set_eye(*eye_values[eye_idx])

            for mouth in mouth_options:
                if mouth != 'normal':
                    mascot_image.set_mouth(mouth, 1.0, 1.0)
                else:
                    mascot_image.set_mouth(0, 0.0, 0.0)

                mascot_image.update()
                image = mascot_image.get_numpy_image()

                cv2.imwrite(os.path.join(save_dir_path, f'{eyebrow}_{eye}_{mouth}.png'), image)
            
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', '-i')
    parser.add_argument('--output', '-o')
    args = parser.parse_args()

    image = cv2.imread(args.input, -1)

    result = make_images(image, args.output)