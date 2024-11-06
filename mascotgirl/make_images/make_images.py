#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

import cv2

from mascot_image import MascotImage

def make_images(numpy_content, save_dir_path):
    os.makedirs(save_dir_path, exist_ok=True)

    mascot_image = MascotImage()
    mascot_image.upload_image(numpy_content, False)

    eyebrow_options = ["normal", "troubled", "angry", "happy", "serious"]
    eye_options = ["normal", "closed", "happy_closed", "relaxed_closed", "surprized", "wink"]
    eye_values = [None, [0, 1.0, 1.0], [1, 1.0, 1.0], [3, 1.0, 1.0], [2, 1.0, 1.0], [1, 1.0, 0.0]]
    mouth_options = ["normal", "aaa", "iii", "uuu", "eee", "ooo"]

    for eyebrow in eyebrow_options:
        for other_eyebrow in eyebrow_options:
            if eyebrow != other_eyebrow and other_eyebrow != 'normal':
                mascot_image.set_eyebrow(other_eyebrow, 0.0, 0.0)
        if eyebrow != 'normal':
            mascot_image.set_eyebrow(eyebrow, 1.0, 1.0)

        for eye_idx, eye in enumerate(eye_options):
            for other_eye_idx, _ in enumerate(eye_options):
                if eye_idx != other_eye_idx and other_eye_idx != 0:
                    mascot_image.set_eye(*eye_values[other_eye_idx])
            if eye_idx != 0:
                mascot_image.set_eye(*eye_values[eye_idx])

            for mouth in mouth_options:
                for other_mouth in mouth_options:
                    if mouth != other_mouth and other_mouth != 'normal':
                        mascot_image.set_mouth(other_mouth, 0.0, 0.0)
                if mouth != 'normal':
                    mascot_image.set_mouth(mouth, 1.0, 1.0)

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