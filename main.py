
import os
from pathlib import Path

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE = Path(__file__).resolve().parent

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


def coerce(key, value):
    if key in ("port", "workers"):
        return int(value)
    if key == "debug":
        return str(value).lower() in ("true", "1", "yes", "on")
    return str(value)


def apply_layer(config, values):
    for raw_key, value in values.items():
        if value is None:
            continue
        key = raw_key.lower()
        if key.startswith("app_"):
            key = key[4:]
        if key == "num_workers":
            key = "workers"
        if key in DEFAULTS:
            config[key] = coerce(key, value)


@app.get("/effective-config")
def effective_config(request: Request, set: list[str] = Query(default=[])):
    config = DEFAULTS.copy()

    env_name = os.getenv("APP_ENV", "development")
    yaml_path = BASE / f"config.{env_name}.yaml"
    if yaml_path.exists():
        with yaml_path.open(encoding="utf-8") as f:
            apply_layer(config, yaml.safe_load(f) or {})

    apply_layer(config, dotenv_values(BASE / ".env"))
    apply_layer(config, {k:v for k, v in os.environ.items() if k.startswith("APP_")})

    # Repeated ?set=key=value parameters override all other layers.
    for item in set:
        if "=" in item:
            key, value = item.split("=", 1)
            key = key.lower()
            if key in DEFAULTS:
                config[key] = coerce(key, value)

    config["api_key"] = "****"
    return config
