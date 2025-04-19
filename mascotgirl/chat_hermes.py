#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import threading
from huggingface_hub import hf_hub_download
from gpt_stream_parser import force_parse_json
import torch
from contextlib import redirect_stderr

from langchain.prompts import StringPromptTemplate
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.schema import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.messages.tool import ToolMessage
from langchain_community.llms import LlamaCpp

#from langchain_core.pydantic_v1 import BaseModel, Field
from pydantic import BaseModel, Field

class TemplateMessagesPrompt(StringPromptTemplate):
    history_name: str = 'history'

    def format(self, **kwargs: any) -> str:
        input_mes_list = kwargs[self.history_name]
        messages = ''
        for mes in input_mes_list:
            messages += '<|im_start|>'
            if type(mes) is tuple:
                messages += mes[0] + '\n' + mes[1] + '<|im_end|>\n'
            else:
                if type(mes) is HumanMessage:
                    messages += 'user'
                elif type(mes) is AIMessage:
                    messages += 'assistant'
                elif type(mes) is SystemMessage:
                    messages += 'system'
                else:
                    messages += 'tool'
                messages += '\n' + mes.content + '<|im_end|>\n'
        messages += '<|im_start|>assistant\n'
        return messages

class ChatHermesJsonResult(BaseModel):
    eyebrow: str = Field(description='表示されるあなたの眉 normal/troubled/angry/happy/serious のどれか')
    eyes: str = Field(description='表示されるあなたの目 normal/closed/happy_closed/relaxed_closed/surprized/wink のどれか')
    message: str = Field(description='メッセージ（返答） 日本語でお願いします')

class ChatHermes:
    schema_message = "You are a helpful assistant that answers in JSON. Here's the json schema you must adhere to:\n<schema>\n{schema}\n</schema>"
    is_running = False

    def __init__(self, model_path, file_name, n_gpu_layers, n_batch, n_ctx):
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

        llm = LlamaCpp(
            model_path=download_path,
            n_gpu_layers=n_gpu_layers,
            n_batch=n_batch,
            n_ctx=n_ctx,
            streaming=True,
            stop=['<|im_end|>', ],
            max_tokens=1500,
            temperature=0.8,
            #repetition_penalty=1.1,
        )

        prompt = TemplateMessagesPrompt(
            input_variables=['history', ],
        )

        self.chain = prompt | llm

    def run_infer(self, prompt):
        if self.is_running:
            return False

        history = ChatMessageHistory()
        for mes in prompt:
            if mes['role'] == 'user':
                history.add_user_message(mes['content'])
            elif mes['role'] == 'assistant':
                history.add_ai_message(mes['content'])
            elif mes['role'] == 'system':
                history.add_message(SystemMessage(mes['content'] + '\n\n' + self.schema_message.replace('{schema}', ChatHermesJsonResult.schema_json())))
            else:
                history.add_message(ToolMessage(mes['content'], tool_call_id=''))

        def invoke():
            self.is_running = True

            self.recieved_message = ''
            for chunk in self.chain.stream({"history": history.messages}):
                self.recieved_message += chunk
                if '{' in self.recieved_message and self.recieved_message.count('{') <= self.recieved_message.count('}'):
                    break

            self.is_running = False

        invoke_thread = threading.Thread(target=invoke)
        invoke_thread.start()

        return True

    def get_recieved_message(self):
        recieved_message = self.recieved_message.replace('”', '"').replace("´", "'")
        if '{' in recieved_message:
            recieved_message = '{' + recieved_message.split('{', 1)[1]
            rsplit_size = recieved_message.count('}') - recieved_message.count('{') + 1
            if rsplit_size > 0:
                recieved_message = recieved_message.rsplit('}', rsplit_size)[0] + '}'
            return not self.is_running, force_parse_json(recieved_message), [{'role': 'assistant', 'content': recieved_message}]
        return not self.is_running, {}, []