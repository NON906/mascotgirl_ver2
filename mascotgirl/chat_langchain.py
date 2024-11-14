#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import threading

from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.schema import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.messages.tool import ToolMessage

from .chat_hermes import ChatHermesJsonResult

class ChatLangchain:
    is_running = False

    def __init__(self, chat_llm, convert_system=False):
        self.chat_llm = chat_llm.with_structured_output(ChatHermesJsonResult)
        self.convert_system = convert_system

    def run_infer(self, prompt):
        if self.is_running:
            return False

        history = ChatMessageHistory()
        system_to_user_message = None
        for mes in prompt:
            if mes['role'] == 'user':
                if system_to_user_message is None:
                    history.add_user_message(mes['content'])
                else:
                    history.add_user_message(system_to_user_message + mes['content'])
                    system_to_user_message = None
            elif mes['role'] == 'assistant':
                history.add_ai_message(mes['content'])
            elif mes['role'] == 'system':
                if self.convert_system:
                    system_to_user_message = mes['content'] + '\n---\n'
                else:
                    history.add_message(SystemMessage(mes['content']))
            else:
                history.add_message(ToolMessage(mes['content'], tool_call_id=''))

        def invoke():
            self.is_running = True

            self.recieved_message = None
            for chunk in self.chat_llm.stream(history.messages):
                self.recieved_message = chunk

            self.is_running = False

        invoke_thread = threading.Thread(target=invoke)
        invoke_thread.start()

        return True

    def get_recieved_message(self):
        if self.recieved_message is None:
            return not self.is_running, {}, ""
        return not self.is_running, self.recieved_message.dict(), self.recieved_message.json()
