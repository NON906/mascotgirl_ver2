#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import threading
import asyncio
import json

from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.schema import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.messages.tool import ToolMessage
from langgraph.prebuilt import create_react_agent
from langchain.schema import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.messages.tool import ToolMessage

from pydantic import BaseModel, Field

class ChatHermesJsonResult(BaseModel):
    eyebrow: str = Field(description='表示されるあなたの眉 normal/troubled/angry/happy/serious のどれか')
    eyes: str = Field(description='表示されるあなたの目 normal/closed/happy_closed/relaxed_closed/surprized/wink のどれか')
    message: str = Field(description='メッセージ（返答） 日本語でお願いします')

class ChatLangchain:
    is_running = False

    def __init__(self, chat_llm, tools, convert_system=False):
        if tools is not None and len(tools) > 0:
            self.agent_llm = create_react_agent(chat_llm, tools)
        else:
            self.agent_llm = None
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
                if not self.convert_system and 'tool_calls' in mes and mes['tool_calls'] is not None and mes['tool_calls'] != '':
                    add_message = AIMessage(mes['content'])
                    add_message.tool_calls = json.loads(mes['tool_calls'])
                    history.add_message(add_message)
                else:
                    history.add_ai_message(mes['content'])
            elif mes['role'] == 'system':
                if self.convert_system:
                    system_to_user_message = mes['content'] + '\n---\n'
                else:
                    history.add_message(SystemMessage(mes['content']))
            else:
                if self.convert_system:
                    history.add_user_message('実行結果:\n' + mes['content'])
                else:
                    history.add_message(ToolMessage(mes['content'], tool_call_id=mes['tool_calls']))

        output_history = ChatMessageHistory()

        async def invoke():
            self.is_running = True

            self.recieved_message = None
            self.recieved_history = []

            if self.agent_llm is not None:
                agent_result = await self.agent_llm.ainvoke({"messages": history.messages})
                history.add_messages(agent_result["messages"])
                #import sys
                #print(agent_result["messages"][-1].content, file=sys.stderr)
                history.add_user_message('Please print out the last reply as is (if the content is not in Japanese, please translate it into Japanese).')
                output_history.add_messages(agent_result["messages"])

            async for chunk in self.respond_llm.astream(history.messages):
                self.recieved_message = chunk
            output_history.add_ai_message(self.recieved_message.json())
            
            for mes in await output_history.aget_messages():
                if type(mes) is tuple:
                    self.recieved_history.append(mes)
                else:
                    if type(mes) is HumanMessage:
                        self.recieved_history.append({'role': 'user', 'content': mes.content})
                    elif type(mes) is AIMessage:
                        self.recieved_history.append({'role': 'assistant', 'content': mes.content, 'tool_calls': json.dumps(mes.tool_calls)})
                    elif type(mes) is SystemMessage:
                        self.recieved_history.append({'role': 'system', 'content': mes.content})
                    else:
                        self.recieved_history.append({'role': 'tool', 'content': mes.content, 'tool_calls': mes.tool_call_id})

            self.is_running = False

        invoke_thread = asyncio.create_task(invoke())

        return True

    def get_recieved_message(self):
        if self.recieved_message is None:
            return not self.is_running, {}, []
        return not self.is_running, self.recieved_message.dict(), self.recieved_history
