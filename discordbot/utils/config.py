import atexit
import json
import logging
import re
from typing import Any, Dict, List

DEFAULT_CONFIG = {"languageCode": "en-US", "voiceId": "Amy", "wikiLanguage": "en"}

DEFAULT_CONFIGFILE_NAME = "discordbot_config.json"


# See https://docs.aws.amazon.com/de_de/polly/latest/dg/voicelist.html
VALID_T2S_LANGUGAGE_CODES = [
    "arb",
    "cmn-CN",
    "cy-GB",
    "da-DK",
    "de-DE",
    "en-AU",
    "en-GB",
    "en-GB-WLS",
    "en-IN",
    "en-US",
    "es-ES",
    "es-MX",
    "es-US",
    "fr-CA",
    "fr-FR",
    "is-IS",
    "it-IT",
    "ja-JP",
    "hi-IN",
    "ko-KR",
    "nb-NO",
    "nl-NL",
    "pl-PL",
    "pt-BR",
    "pt-PT",
    "ro-RO",
    "ru-RU",
    "sv-SE",
    "tr-TR",
    "en-NZ",
    "en-ZA",
]
VALID_T2S_VOICE_IDS = [
    "Aditi",
    "Amy",
    "Astrid",
    "Bianca",
    "Brian",
    "Camila",
    "Carla",
    "Carmen",
    "Celine",
    "Chantal",
    "Conchita",
    "Cristiano",
    "Dora",
    "Emma",
    "Enrique",
    "Ewa",
    "Filiz",
    "Gabrielle",
    "Geraint",
    "Giorgio",
    "Gwyneth",
    "Hans",
    "Ines",
    "Ivy",
    "Jacek",
    "Jan",
    "Joanna",
    "Joey",
    "Justin",
    "Karl",
    "Kendra",
    "Kevin",
    "Kimberly",
    "Lea",
    "Liv",
    "Lotte",
    "Lucia",
    "Lupe",
    "Mads",
    "Maja",
    "Marlene",
    "Mathieu",
    "Matthew",
    "Maxim",
    "Mia",
    "Miguel",
    "Mizuki",
    "Naja",
    "Nicole",
    "Olivia",
    "Penelope",
    "Raveena",
    "Ricardo",
    "Ruben",
    "Russell",
    "Salli",
    "Seoyeon",
    "Takumi",
    "Tatyana",
    "Vicki",
    "Vitoria",
    "Zeina",
    "Zhiyu",
    "Aria",
    "Ayanda",
]

INPUT_VALIDATION_RAW_RE = r"^[a-zA-Z]{2}$"
INPUT_VALIDATION_STR = re.compile(INPUT_VALIDATION_RAW_RE)

VALID_CONFIG_PARAM_KEYS = {
    "languageCode": {
        "description": "The language code to use for the Polly API. See https://docs.aws.amazon.com/de_de/polly/latest/dg/voicelist.html",
        "valid_inputs": lambda val: val in VALID_T2S_LANGUGAGE_CODES,
    },
    "voiceId": {
        "description": "The voice ID to use for the Polly API. See https://docs.aws.amazon.com/de_de/polly/latest/dg/voicelist.html",
        "valid_inputs": lambda val: val in VALID_T2S_VOICE_IDS,
    },
    "wikiLanguage": {
        "description": f"The language code to use for the Wikipedia API. Must match '{INPUT_VALIDATION_RAW_RE}'",
        "valid_inputs": lambda val: INPUT_VALIDATION_STR.match(val),
    },
}


class ConfigError(Exception):
    pass


class ConfigValidationError(ConfigError):
    pass


class ConfigMap:
    def __init__(self, configs: List[Dict[str, Any]], configfile_name: str = None):
        self.log = logging.getLogger("config")
        self._configs = dict()
        self.configfile_name = configfile_name or DEFAULT_CONFIGFILE_NAME

        for cfg in configs:
            id = cfg["id"]
            del cfg["id"]
            self._configs[id] = cfg

        atexit.register(self.persist)

    def exists(self, id: str):
        return id in self._configs

    def get_config_for(self, id: str, key: str = "", default: Any = None):
        if self.exists(id):
            return (
                self._configs[id]
                if key == ""
                else self._configs[id][key]
                if key in self._configs[id]
                else default
            )

    def add_config_for(self, id: str, config: Dict[str, Any]):
        for key in config:
            self.is_valid_config_parameter(key, config[key])
        self._configs[id] = config

    def update_config_for(self, id: str, key: str, val: str):
        if self.exists(id) and self.is_valid_config_parameter(key, val):
            self._configs[id][key] = val

    def remove_config_for(self, id: str):
        if self.exists(id):
            del self._configs[id]

    def set_defaults_for(self, id: str):
        if not self.exists(id):
            self.log.info("Setting default config")
            self.add_config_for(id, DEFAULT_CONFIG)
        self.log.info(f"Config for {id} already exists. Cannot set defaults...")

    def is_valid_config_parameter(self, key: str, val: str) -> bool:
        if not key in VALID_CONFIG_PARAM_KEYS.keys():
            raise ConfigValidationError(
                f"'{key}' is not a valid config parameter. Try one of {VALID_CONFIG_PARAM_KEYS}"
            )
        else:
            val_info = VALID_CONFIG_PARAM_KEYS[key]
            if not val_info["valid_inputs"](val):
                raise ConfigValidationError(
                    f"'{val}' is not a valid value for '{key}': {val_info['description']}"
                )
        return True

    @classmethod
    def from_file(cls, configfile_name: str = DEFAULT_CONFIGFILE_NAME):
        try:
            with open(configfile_name, "r") as f:
                data = json.load(f)
                return cls(data, configfile_name=configfile_name)
        except IOError:
            logging.warn("failed to restore config from file")
            return cls([], configfile_name=configfile_name)

    def persist(self):
        self.log.info(f"Persisting current config state to {self.configfile_name}...")
        with open(self.configfile_name, "w") as f:
            out = []
            for id in self._configs:
                out.append({**self._configs[id], "id": id})
            json.dump(out, f)
