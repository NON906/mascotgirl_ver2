import soundfile
import tempfile
from typing import Optional, List
import json
from urllib.parse import unquote
from pathlib import Path
import os
import glob

import torch

from style_bert_vits2.tts_model import TTSModel, TTSModelHolder
from style_bert_vits2.nlp import bert_models
from style_bert_vits2.constants import Languages

loaded_models: list[TTSModel] = []

is_loaded = False

def change_dirs(dir_paths_list: list[str]):
    global is_loaded, loaded_models
    if not is_loaded:
        bert_models.load_model(Languages.JP, "ku-nlp/deberta-v2-large-japanese-char-wwm")
        bert_models.load_tokenizer(Languages.JP, "ku-nlp/deberta-v2-large-japanese-char-wwm")
        is_loaded = True

    for dir_path in dir_paths_list:
        model = TTSModel(
            model_path=glob.glob(dir_path + "/*.safetensors")[0],
            config_path=os.path.join(dir_path, "config.json"),
            style_vec_path=os.path.join(dir_path, "style_vectors.npy"),
            device="cuda" if torch.cuda.is_available() else "cpu",
        )
        loaded_models.append(model)

async def voice(
    text: str,
    write_path: str,
    encoding: str = None,
    model_id: int = 0,
    speaker_id: int = 0,
):
    model = loaded_models[model_id]
    if encoding is not None:
        text = unquote(text, encoding=encoding)

    sr, audio = model.infer(
        text=text,
        speaker_id=speaker_id)

    soundfile.write(file=write_path, data=audio, samplerate=sr)