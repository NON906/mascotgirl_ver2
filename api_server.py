#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
import glob
import tempfile
import subprocess
import time
import requests
import cv2
import numpy as np
import uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from mascotgirl.make_images.make_images import make_images

def main():
    td = tempfile.TemporaryDirectory()

    os.chdir('fish_speech')
    voice_process = subprocess.Popen(['start.bat'])
    os.chdir('..')

    app = FastAPI()

    @app.post("/upload_base_image")
    async def upload_base_image(file: bytes = File(...)):
        arr = np.frombuffer(file, dtype=np.uint8)
        img = cv2.imdecode(arr, flags=cv2.IMREAD_UNCHANGED)
        make_images(img, 'settings/images')
        return {'is_success': True}

    class CopyImagesRequest(BaseModel):
        path: str

    @app.post("/copy_images")
    async def copy_images(request: CopyImagesRequest):
        shutil.copytree('settings/images', request.path)
        return {'is_success': True}

    @app.post("/upload_reference_voice")
    async def upload_reference_voice(file: UploadFile = File(...)):
        try:
            del_paths = glob.glob('settings/reference_voice.*')
            for del_path in del_paths:
                os.remove(del_path)

            with open('settings/reference_voice' + os.path.splitext(file.filename)[1], mode='wb') as f:
                shutil.copyfileobj(file.file, f)
            return {'is_success': True}
        finally:
            file.file.close()

    class VoiceInferRequest(BaseModel):
        text: str
        format_ext: str

    @app.post("/voice_infer")
    async def voice_infer(request: VoiceInferRequest):
        del_paths = glob.glob(os.path.join(td.name, 'result.*'))
        for del_path in del_paths:
            os.remove(del_path)

        reference_path = glob.glob('settings/reference_voice.*')[0]
        result_path = os.path.join(td.name, 'result')

        subprocess.run(['python', '-m', 'fish_speech.tools.post_api',
            '--text', request.text,
            '--reference_audio', reference_path,
            '--reference_text', '',
            '--output', result_path,
            '--format', request.format_ext,
            '--play', '',
        ])

        return {'is_success': True}

    @app.get("/get_voice_infer")
    async def get_voice_infer():
        result_path = glob.glob(os.path.join(td.name, 'result.*'))[0]
        return FileResponse(path=result_path)

    loop_flag = True
    run_flag = True
    while loop_flag:
        time.sleep(0.1)
        try:
            res = requests.post('http://localhost:8080/v1/health')
            loop_flag = res.json()['status'] != 'ok'
        except requests.exceptions.ConnectionError:
            loop_flag = True
        except:
            loop_flag = False
            run_flag = False

    if run_flag:
        uvicorn.run(app, host='0.0.0.0', port=55007)

    voice_process.kill()

    return False

if __name__ == "__main__":
    try:
        loop_flag = True
        while loop_flag:
            loop_flag = main()
    except KeyboardInterrupt:
        pass
