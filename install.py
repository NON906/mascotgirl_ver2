#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import subprocess
import sys
import requests

def wget(url: str, save_path: str):
    if os.path.dirname(save_path) != "":
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
    subprocess.run(['bin\\wget', '-O', save_path, url])

def make_empty_file(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as o:
        o.write('')

if __name__ == "__main__":
    while not os.path.isfile('.installed/.wget'):
        urlData = requests.get('https://eternallybored.org/misc/wget/1.21.4/64/wget.exe').content
        os.makedirs('bin', exist_ok=True)
        with open('bin/wget.exe', mode='wb') as f:
            f.write(urlData)
        make_empty_file('.installed/.wget')

    subprocess.run(['conda', 'env', 'update', '-f', 'environment.yml'], shell=True)

    while not os.path.isfile('.installed/.fish_speech'):
        os.chdir("./fish_speech")
        subprocess.run(['python', '-m', 'pip', 'install', '-e', '.'])
        os.chdir("..")
        make_empty_file('.installed/.fish_speech')

    subprocess.run(['python', '-m', 'pip', 'install', '-r', 'requirements.txt'])

    subprocess.run(['conda', 'clean', '-y', '--all'], shell=True)

    while not os.path.isfile('.installed/.tha3'):
        wget('https://www.dropbox.com/s/zp3e5ox57sdws3y/editor.pt?dl=0', 'talking_head_anime_3_demo/data/models/standard_float/editor.pt')
        wget('https://www.dropbox.com/s/bcp42knbrk7egk8/eyebrow_decomposer.pt?dl=0', 'talking_head_anime_3_demo/data/models/standard_float/eyebrow_decomposer.pt')
        wget('https://www.dropbox.com/s/oywaiio2s53lc57/eyebrow_morphing_combiner.pt?dl=0', 'talking_head_anime_3_demo/data/models/standard_float/eyebrow_morphing_combiner.pt')
        wget('https://www.dropbox.com/s/8qvo0u5lw7hqvtq/face_morpher.pt?dl=0', 'talking_head_anime_3_demo/data/models/standard_float/face_morpher.pt')
        wget('https://www.dropbox.com/s/qmq1dnxrmzsxb4h/two_algo_face_body_rotator.pt?dl=0', 'talking_head_anime_3_demo/data/models/standard_float/two_algo_face_body_rotator.pt')
        make_empty_file('.installed/.tha3')