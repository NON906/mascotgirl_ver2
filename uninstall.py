#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess

if __name__ == "__main__":
    output_str = subprocess.run(['conda', 'env', 'list'], capture_output=True, text=True, shell=True).stdout
    env_count = output_str.count('miniconda3')
    if env_count == 2:
        with open('../.miniconda_uninstall', 'w') as o:
            o.write('')
