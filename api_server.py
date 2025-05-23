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
import threading
import json
import uuid
import asyncio
from pathlib import Path
from faster_whisper import WhisperModel
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse, JSONResponse
from pydantic import BaseModel
from conda3rdparty.common import CondaEnv, gather_license_info, CondaPackageFileNotFound, base_license_renderer
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from google.generativeai.types.safety_types import HarmBlockThreshold, HarmCategory
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp import MCPToolkit

from mascotgirl.make_images.make_images import make_images
from mascotgirl.chat_hermes import ChatHermes
from mascotgirl.chat_hermes_agent import ChatHermesAgent
from mascotgirl.chat_langchain import ChatLangchain
from mascotgirl import bert_vits2
from mascotgirl.mcp_manager import McpManager

def main(args):
    global chat_hermes

    td = tempfile.TemporaryDirectory()

    voice_process = None

    chat_hermes = None
    mcp_manager = McpManager()

    app = FastAPI()

    @app.get("/health")
    async def health():
        return {'is_success': True}

    @app.get("/get_settings")
    async def get_settings():
        if os.path.isfile('settings/detail_settings.json'):
            return FileResponse(path='settings/detail_settings.json')
        return {}

    class SetSettingRequest(BaseModel):
        name: str
        value: str | float | int | bool

    @app.post("/set_setting")
    async def set_setting(request: SetSettingRequest):
        new_dict = {}
        if os.path.isfile('settings/detail_settings.json'):
            with open('settings/detail_settings.json', mode='r', encoding='utf-8') as f:
                new_dict = json.load(f)
        new_dict[request.name] = request.value

        if request.name == 'llm_api' or request.name == 'llm_repo_name' or request.name == 'llm_file_name' or request.name == 'llm_api_key' or request.name == 'llm_model_name' or request.name == 'llm_harm_block':
            global chat_hermes
            if chat_hermes is not None:
                del chat_hermes
            chat_hermes = None

        with open('settings/detail_settings.json', mode='w', encoding='utf-8') as f:
            json.dump(new_dict, f)
        return {'is_success': True}

    @app.post("/upload_base_image")
    async def upload_base_image(file: bytes = File(...)):
        arr = np.frombuffer(file, dtype=np.uint8)
        img = cv2.imdecode(arr, flags=cv2.IMREAD_UNCHANGED)
        make_images(img, 'settings/images')
        if os.path.isfile('settings/settings.json'):
            with open('settings/settings.json', mode='r', encoding='utf-8') as f:
                json_dict = json.load(f)
        else:
            json_dict = {}
        json_dict['images_hash'] = str(uuid.uuid4())
        with open('settings/settings.json', mode='w', encoding='utf-8') as f:
            json.dump(json_dict, f)
        return {'is_success': True}

    @app.get("/get_images_hash")
    async def get_images_hash():
        if not os.path.isfile('settings/settings.json'):
            return JSONResponse(content={'is_success': False}, status_code=404)
        with open('settings/settings.json', mode='r', encoding='utf-8') as f:
            ret_hash = json.load(f)['images_hash']
        return {'hash': ret_hash}

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

    @app.get("/get_image")
    async def get_image(id: str):
        path = f'settings/images/{id}.png'
        if not os.path.isfile(path):
            return JSONResponse(content={'is_success': False}, status_code=404)
        return FileResponse(path=path)

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
        with open('settings/system_message.txt', mode='w', encoding='utf-8') as f:
            f.write(request.message)
        return {'is_success': True}

    @app.get("/get_system_message")
    async def get_system_message():
        if not os.path.isfile('settings/system_message.txt'):
            return JSONResponse(content={'is_success': False}, status_code=404)
        with open('settings/system_message.txt', mode='r', encoding='utf-8') as f:
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
            
            with open('settings/reference_text.txt', mode='w', encoding='utf-8') as f:
                f.write(reference_text)

            return {'reference_text': reference_text}
        finally:
            file.file.close()

    class ChatHermesInferRequest(BaseModel):
        messages: list[dict]

    @app.post("/chat_hermes_infer")
    async def chat_hermes_infer(request: ChatHermesInferRequest):
        global chat_hermes
        await mcp_manager.load()
        if chat_hermes is None:
            if os.path.isfile('settings/detail_settings.json'):
                with open('settings/detail_settings.json', mode='r', encoding='utf-8') as f:
                    settings_dict = json.load(f)
            else:
                settings_dict = {}
            if not 'llm_api' in settings_dict or settings_dict['llm_api'] == 0:
                if not 'llm_repo_name' in settings_dict or settings_dict['llm_repo_name'] == '':
                    settings_dict['llm_repo_name'] = 'NousResearch/Hermes-3-Llama-3.1-8B-GGUF'
                if not 'llm_file_name' in settings_dict or settings_dict['llm_file_name'] == '':
                    settings_dict['llm_file_name'] = 'Hermes-3-Llama-3.1-8B.Q6_K.gguf'
                if len(mcp_manager.get_tools()) > 0:
                    chat_hermes = ChatHermesAgent(settings_dict['llm_repo_name'], settings_dict['llm_file_name'], 'auto', 128, 65536, mcp_manager.get_tools())
                else:
                    chat_hermes = ChatHermes(settings_dict['llm_repo_name'], settings_dict['llm_file_name'], 'auto', 128, 65536)
            elif settings_dict['llm_api'] == 1:
                chat_hermes = ChatLangchain(
                    ChatOpenAI(
                        api_key=settings_dict['llm_api_key'],
                        model=settings_dict['llm_model_name']
                    ),
                    mcp_manager.get_tools()
                )
            elif settings_dict['llm_api'] == 2:
                if not 'llm_harm_block' in settings_dict or settings_dict['llm_harm_block'] == 0:
                    harm_block = HarmBlockThreshold.BLOCK_NONE
                elif settings_dict['llm_harm_block'] == 1:
                    harm_block = HarmBlockThreshold.LOW_AND_ABOVE
                elif settings_dict['llm_harm_block'] == 2:
                    harm_block = HarmBlockThreshold.MEDIUM_AND_ABOVE
                elif settings_dict['llm_harm_block'] == 3:
                    harm_block = HarmBlockThreshold.ONLY_HIGH
                safety_settings = {
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: harm_block,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: harm_block,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: harm_block,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: harm_block,
                }
                chat_hermes = ChatLangchain(
                    ChatGoogleGenerativeAI(
                        model=settings_dict['llm_model_name'],
                        safety_settings=safety_settings,
                        google_api_key=settings_dict['llm_api_key']
                    ),
                    mcp_manager.get_tools(),
                    True
                )
            elif settings_dict['llm_api'] == 3:
                chat_hermes = ChatLangchain(
                    ChatOllama(
                        model=settings_dict['llm_model_name']
                    ),
                    mcp_manager.get_tools()
                )
        ret = chat_hermes.run_infer(request.messages)
        return {'is_success': ret}

    @app.get("/get_chat_hermes_infer")
    async def get_chat_hermes_infer():
        is_finished, ret, history = chat_hermes.get_recieved_message()
        if ret is None:
            ret = {}
        ret['history'] = history
        ret['is_finished'] = is_finished
        return ret

    class VoiceInferRequest(BaseModel):
        text: str
        format_ext: str

    @app.post("/voice_infer")
    async def voice_infer(request: VoiceInferRequest):
        nonlocal voice_process

        del_paths = glob.glob(os.path.join(td.name, 'result.*'))
        for del_path in del_paths:
            os.remove(del_path)

        if os.path.isfile('settings/detail_settings.json'):
            with open('settings/detail_settings.json', mode='r', encoding='utf-8') as f:
                settings_dict = json.load(f)
        else:
            settings_dict = {}

        if not 'voice_api' in settings_dict or settings_dict['voice_api'] == 0:
            run_flag = True
            if voice_process is None:
                os.chdir('fish_speech')
                voice_process = subprocess.Popen(['start.bat'])
                os.chdir('..')

                loop_flag = True
                while loop_flag:
                    await asyncio.sleep(0.1)
                    try:
                        res = requests.post('http://localhost:8080/v1/health')
                        loop_flag = res.json()['status'] != 'ok'
                    except requests.exceptions.ConnectionError:
                        loop_flag = True
                    except:
                        loop_flag = False
                        run_flag = False

            if not run_flag:
                return {'is_success': False }

            reference_path = glob.glob('settings/reference_voice.*')[0]
            result_path = os.path.join(td.name, 'result')

            with open('settings/reference_text.txt', mode='r', encoding='utf-8') as f:
                reference_text = f.read()

            subprocess.run(['python', '-m', 'fish_speech.tools.post_api',
                '--text', request.text,
                '--reference_audio', reference_path,
                '--reference_text', reference_text,
                '--output', result_path,
                '--format', request.format_ext,
                '--temperature', '0.5',
                '--play', '',
            ])

            return {'is_success': os.path.isfile(result_path + '.' + request.format_ext)}
        elif settings_dict['voice_api'] == 1:
            bert_vits2.change_dirs([settings_dict['voice_model_dir'], ])
            write_path = os.path.join(td.name, 'result.' + request.format_ext)
            await bert_vits2.voice(request.text, encoding='utf-8', write_path=write_path)
            return {'is_success': os.path.isfile(write_path)}

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

    if args.net_mode == 'none':
        subprocess.Popen(["client\\MascotGirl_Client_ver2\\MascotGirl_Client_ver2.exe", "-start_local"])
        uvicorn.run(app, host='127.0.0.1', port=55007)
    elif args.net_mode == 'debug':
        uvicorn.run(app, host='127.0.0.1', port=55007)
    else:
        if args.net_mode == 'local_net':
            if os.name == 'nt':
                import socket
                host = socket.gethostname()
                ipaddress = socket.gethostbyname(host)
                http_url = 'http://' + ipaddress + ':' + str(55007)
        elif args.net_mode == 'cloudflare':
            from pycloudflared import try_cloudflare
            cloudflare_result = try_cloudflare(port=55007)
            http_url = cloudflare_result.tunnel

        import qrcode
        open_qrcode = True
        qrcode_pil = qrcode.make('mascotgirl2://' + http_url)
        qrcode_cv2 = np.array(qrcode_pil, dtype=np.uint8) * 255
        def qrcode_thread_func():
            cv2.imshow('Please scan.', qrcode_cv2)
            while open_qrcode:
                cv2.waitKey(1)
        qrcode_thread = threading.Thread(target=qrcode_thread_func)
        qrcode_thread.start()

        uvicorn.run(app, host='0.0.0.0', port=55007)

        open_qrcode = False
        cv2.destroyWindow('Please scan.')

    if voice_process is not None:
        voice_process.kill()
    if chat_hermes is not None:
        del chat_hermes

    return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--net_mode', choices=['none', 'local_net', 'cloudflare', 'debug'], default='none')
    args = parser.parse_args()

    try:
        loop_flag = True
        while loop_flag:
            loop_flag = main(args)
    except KeyboardInterrupt:
        pass
