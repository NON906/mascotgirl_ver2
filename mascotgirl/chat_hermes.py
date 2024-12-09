#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import threading
from huggingface_hub import hf_hub_download
import torch
from contextlib import redirect_stderr
import asyncio

from langchain.tools import tool

#from langchain_core.pydantic_v1 import BaseModel, Field
from pydantic import BaseModel, Field

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Hermes_Function_Calling'))
from functioncall_gguf import ModelInferenceGguf
sys.path = sys.path[:-1]

class ChatHermesJsonResult(BaseModel):
    eyebrow: str = Field(description='表示されるあなたの眉 normal/troubled/angry/happy/serious のどれか')
    eyes: str = Field(description='表示されるあなたの目 normal/closed/happy_closed/relaxed_closed/surprized/wink のどれか')
    message: str = Field(description='メッセージ（返答）')

@tool("respond", args_schema=ChatHermesJsonResult)
def respond(eyebrow: str, eyes: str, message: str) -> str:
    """ユーザーへのメッセージの返答と表情の指定"""
    return "<完了>"

class ChatHermes:
    is_running = False
    result = None

    def __init__(self, model_path, file_name, n_gpu_layers, n_batch, n_ctx, tools):
        if model_path is not None and os.path.exists(model_path):
            download_path = model_path
        elif file_name is not None and os.path.exists(file_name):
            download_path = file_name
        else:
            download_path = hf_hub_download(repo_id=model_path, filename=file_name)

        if n_gpu_layers == 'auto':
            if not torch.cuda.is_available():
                n_gpu_layers = 0
            else:
                from llama_cpp import Llama
                with redirect_stderr(open(os.devnull, 'w')):
                    device = torch.device('cuda')
                    total_memory = torch.cuda.get_device_properties(device).total_memory
                    allocated_memory = torch.cuda.memory_allocated(device)
                    free_memory = total_memory - allocated_memory

                    model_size = os.path.getsize(download_path) * 1.3
                    llm_pre = Llama(model_path=download_path, n_gpu_layers=0)
                    layers_count = int(llm_pre.metadata['llama.block_count'])

                    n_gpu_layers = int(free_memory * layers_count / model_size)

                    del llm_pre

                print('Auto setting n_gpu_layers is ' + str(n_gpu_layers) + '.')

        self.inference = ModelInferenceGguf(model_path, file_name, n_gpu_layers, n_batch, n_ctx)
        self.tools = tools

    def __del__(self):
        del self.inference

    def run_infer(self, prompt):
        if self.is_running:
            return False

        self.result = None

        async def invoke():
            self.is_running = True

            self.result = await self.inference.generate_function_call_async(prompt[-1]['content'], "chatml", None, 5, [respond, ] + self.tools, prompt[:-1], "respond")

            self.is_running = False

        invoke_thread = asyncio.create_task(invoke())

        return True

    def get_recieved_message(self):
        if self.result is None:
            return not self.is_running, self.inference.get_streaming_args(), ""
        return not self.is_running, self.inference.get_streaming_args(), self.result[-1]['content']