#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import threading
import asyncio

from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.schema import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.messages.tool import ToolMessage
from langgraph.prebuilt import create_react_agent

from pydantic import BaseModel, Field

class ChatHermesJsonResult(BaseModel):
    eyebrow: str = Field(description='表示されるあなたの眉 normal/troubled/angry/happy/serious のどれか')
    eyes: str = Field(description='表示されるあなたの目 normal/closed/happy_closed/relaxed_closed/surprized/wink のどれか')
    message: str = Field(description='メッセージ（返答） 日本語でお願いします')

class ChatLangchain:
    is_running = False

    def __init__(self, chat_llm, tools, convert_system=False):
        self.agent_llm = create_react_agent(chat_llm, tools)
        self.respond_llm = chat_llm.with_structured_output(ChatHermesJsonResult)
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
                if self.convert_system:
                    history.add_user_message('Execution result:\n' + mes['content'])
                else:
                    history.add_message(ToolMessage(mes['content'], tool_call_id=''))

        async def invoke():
            self.is_running = True

            self.recieved_message = None

            agent_result = await self.agent_llm.ainvoke({"messages": history.messages})
            history.add_messages(agent_result["messages"])

            async for chunk in self.respond_llm.astream(history.messages):
                self.recieved_message = chunk

            self.is_running = False

        invoke_thread = asyncio.create_task(invoke())

        return True

    def get_recieved_message(self):
        if self.recieved_message is None:
            return not self.is_running, {}, ""
        return not self.is_running, self.recieved_message.dict(), self.recieved_message.json()
