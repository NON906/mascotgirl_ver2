import soundfile
import tempfile
from typing import Optional, List
import json
from urllib.parse import unquote
from pathlib import Path

import torch

import uvicorn
from fastapi import FastAPI, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from style_bert_vits2.tts_model import TTSModel, TTSModelHolder
from style_bert_vits2.nlp import bert_models
from style_bert_vits2.constants import Languages

loaded_models: list[TTSModel] = []

bert_models.load_model(Languages.JP, "ku-nlp/deberta-v2-large-japanese-char-wwm")
bert_models.load_tokenizer(Languages.JP, "ku-nlp/deberta-v2-large-japanese-char-wwm")

def load_models(model_holder: TTSModelHolder):
    global loaded_models
    for model_name, model_paths in model_holder.model_files_dict.items():
        model = TTSModel(
            model_path=model_paths[0],
            config_path=model_holder.root_dir / model_name / "config.json",
            style_vec_path=model_holder.root_dir / model_name / "style_vectors.npy",
            device=model_holder.device,
        )
        loaded_models.append(model)

if __name__ == "__main__":
    device = "cuda" if torch.cuda.is_available() else "cpu"

    app = FastAPI()
    #app.add_middleware(
    #    CORSMiddleware,
    #    allow_origin=["*"],
    #    allow_credentials=True,
    #    allow_methods=["*"],
    #    allow_headers=["*"],
    #)

    model_holders: list[TTSModelHolder] = []

    @app.get("/models/info")
    def get_loaded_models_info():
        result: list[dict[str, Any]] = []
        for model in loaded_models:
            spk_names = []
            spk_id = 0
            while spk_id in model.id2spk:
                spk_names.append(model.id2spk[spk_id])
                spk_id += 1

            style_names = []
            style_id = 0
            break_flag = False
            while not break_flag:
                break_flag = True
                for item_name, item_id in model.style2id.items():
                    if item_id == style_id:
                        style_names.append(item_name)
                        break_flag = False
                        break
                style_id += 1

            result.append({
                "config_path": model.config_path,
                "model_path": model.model_path,
                "device": model.device,
                "speaker_names": spk_names,
                "style_names": style_names,
            })
        return { "models": result }

    @app.post("/models/refresh")
    def refresh():
        global loaded_models
        loaded_models = []
        for model_holder in model_holders:
            model_holder.refresh()
            load_models(model_holder)
        return get_loaded_models_info()

    @app.post("/models/change_dirs")
    def change_dirs(request: Request, dir_paths: str):
        dir_paths_list = json.loads(dir_paths)
        for dir_path in dir_paths_list:
            model_dir = Path(dir_path)
            model_holder = TTSModelHolder(model_dir, device)
            model_holders.append(model_holder)
        return refresh()

    td = tempfile.TemporaryDirectory()

    @app.api_route("/voice", methods=["GET", "POST"])
    async def voice(
        request: Request,
        text: str = Query(..., min_length=1),
        encoding: str = Query(None),
        model_id: int = Query(0),
        speaker_id: int = Query(0),
        write_path: str = Query(None),
    ):
        model = loaded_models[model_id]
        if encoding is not None:
            text = unquote(text, encoding=encoding)

        sr, audio = model.infer(
            text=text,
            speaker_id=speaker_id)

        if write_path is None:
            soundfile.write(file=f"{td.name}/temp.ogg", data=audio, samplerate=sr)
            return FileResponse(f"{td.name}/temp.ogg", media_type="audio/ogg", filename="voice.ogg")
        else:
            soundfile.write(file=write_path, data=audio, samplerate=sr)
            return { "path": write_path }

    uvicorn.run(
        app, port="50501", host="0.0.0.0", log_level="warning"
    )

    del td