#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import shutil
import glob
import tempfile
import subprocess
import time
import requests
import cv2
import numpy as np
import uvicorn
from pathlib import Path
from faster_whisper import WhisperModel
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse, JSONResponse
from pydantic import BaseModel
from conda3rdparty.common import CondaEnv, gather_license_info, CondaPackageFileNotFound, base_license_renderer

from mascotgirl.make_images.make_images import make_images
from mascotgirl.chat_hermes import ChatHermes

def main():
    td = tempfile.TemporaryDirectory()

    chat_hermes = ChatHermes('NousResearch/Hermes-3-Llama-3.1-8B-GGUF', 'Hermes-3-Llama-3.1-8B.Q6_K.gguf', 999, 128, 2048)

    os.chdir('fish_speech')
    voice_process = subprocess.Popen(['start.bat'])
    os.chdir('..')

    app = FastAPI()

    @app.get("/health")
    async def health():
        return {'is_success': True}

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
        if not os.path.isdir('settings/images'):
            return JSONResponse(content={'is_success': False}, status_code=404)
        if os.path.isdir(request.path):
            shutil.rmtree(request.path)
        shutil.copytree('settings/images', request.path)
        return {'is_success': True}

    @app.post("/upload_background_image")
    async def upload_background_image(file: UploadFile = File(...)):
        try:
            del_paths = glob.glob('settings/background.*')
            for del_path in del_paths:
                os.remove(del_path)

            file_path = 'settings/background' + os.path.splitext(file.filename)[1]
            with open(file_path, mode='wb') as f:
                shutil.copyfileobj(file.file, f)

            return {'is_success': True}
        finally:
            file.file.close()

    @app.get("/get_background_image")
    async def get_background_image():
        result_path = glob.glob('settings/background.*')
        if result_path is None or len(result_path) <= 0:
            return JSONResponse(content={'is_success': False}, status_code=404)
        return FileResponse(path=result_path[0])

    class SetSystemMessageRequest(BaseModel):
        message: str
    
    @app.post("/set_system_message")
    async def set_system_message(request: SetSystemMessageRequest):
        with open('settings/system_message.txt', mode='w') as f:
            f.write(request.message)
        return {'is_success': True}

    @app.get("/get_system_message")
    async def get_system_message():
        if not os.path.isfile('settings/system_message.txt'):
            return JSONResponse(content={'is_success': False}, status_code=404)
        with open('settings/system_message.txt', mode='r') as f:
            message = f.read()
        return {'message': message}

    @app.post("/upload_reference_voice")
    async def upload_reference_voice(file: UploadFile = File(...)):
        try:
            del_paths = glob.glob('settings/reference_voice.*')
            for del_path in del_paths:
                os.remove(del_path)

            file_path = 'settings/reference_voice' + os.path.splitext(file.filename)[1]
            with open(file_path, mode='wb') as f:
                shutil.copyfileobj(file.file, f)

            model = WhisperModel(
                "large-v3",
                device="cuda",
                compute_type="float16",
            )
            segments, _ = model.transcribe(
                file_path,
                beam_size=5,
                language="ja",
                initial_prompt="こんにちは。元気、ですかー？私は…ちゃんと元気だよ！",
            )
            reference_text = ''
            for segment in segments:
                reference_text += segment.text
            
            with open('settings/reference_text.txt', mode='w') as f:
                f.write(reference_text)

            return {'reference_text': reference_text}
        finally:
            file.file.close()

    class ChatHermesInferRequest(BaseModel):
        messages: list[dict]

    @app.post("/chat_hermes_infer")
    async def chat_hermes_infer(request: ChatHermesInferRequest):
        ret = chat_hermes.run_infer(request.messages)
        return {'is_success': ret}

    @app.get("/get_chat_hermes_infer")
    async def get_chat_hermes_infer():
        is_finished, ret = chat_hermes.get_recieved_message()
        if ret is None:
            ret = {}
        ret['is_finished'] = is_finished
        return ret

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

        with open('settings/reference_text.txt', mode='r') as f:
            reference_text = f.read()

        subprocess.run(['python', '-m', 'fish_speech.tools.post_api',
            '--text', request.text,
            '--reference_audio', reference_path,
            '--reference_text', reference_text,
            '--output', result_path,
            '--format', request.format_ext,
            '--play', '',
        ])

        return {'is_success': True}

    @app.get("/get_voice_infer")
    async def get_voice_infer():
        result_path = glob.glob(os.path.join(td.name, 'result.*'))[0]
        return FileResponse(path=result_path)

    @app.get("/license", response_class=PlainTextResponse)
    async def license():
        out = []
        env = CondaEnv("mascotgirl_ver2")
        for package in env.package_list:
            try:
                out.append(gather_license_info(package))
            except CondaPackageFileNotFound:
                pass
        ret = base_license_renderer(out, Path('license_template.txt'))
        return ret

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
        subprocess.Popen(["client\\MascotGirl_Client_ver2\\MascotGirl_Client_ver2.exe", "-start_local"])
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
