#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client, get_default_environment
from langchain_mcp import MCPToolkit

class McpManager:
    json_mtime = 0.0
    mcp_tools = []
    tasks = []
    is_exit = False
    loaded_tasks = 0

    async def load(self, settings_file_path='settings/mcp_config.json'):
        if os.path.isfile(settings_file_path) and self.json_mtime != os.path.getmtime(settings_file_path):
            self.is_exit = True
            await asyncio.gather(*self.tasks)
            self.tasks = []
            self.mcp_tools = []
            self.is_exit = False
            self.json_mtime = os.path.getmtime(settings_file_path)
            with open(settings_file_path, mode='r', encoding='UTF-8') as f:
                mcp_dict_all = json.load(f)
            self.loaded_tasks = 0
            for target in mcp_dict_all['mcpServers'].values():
                self.tasks.append(asyncio.create_task(self.add_server(target)))
            while self.loaded_tasks < len(self.tasks) and not self.is_exit:
                await asyncio.sleep(0.1)
            return True
        return False

    async def add_server(self, target):
        if os.name == 'nt' and target['command'] != 'cmd':
            server_params = StdioServerParameters( 
                command='cmd',
                args=['/c', target['command'], *target['args']],
                env=(get_default_environment() | target['env']) if 'env' in target else None,
            )
        else:
            server_params = StdioServerParameters( 
                command=target['command'],
                args=target['args'],
                env=(get_default_environment() | target['env']) if 'env' in target else None,
            )
        async with stdio_client(server_params) as (read, write): 
            async with ClientSession(read, write) as session: 
                toolkit = MCPToolkit(session=session) 
                await toolkit.initialize() 
                self.mcp_tools += toolkit.get_tools()
                self.loaded_tasks += 1
                while not self.is_exit:
                    await asyncio.sleep(0.1)

    def get_tools(self):
        return self.mcp_tools

    def stop_servers(self):
        self.is_exit = True

    def __del__(self):
        self.is_exit = True