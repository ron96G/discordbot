import json
import logging
from typing import Any, List, Dict
import atexit

defaultConfig = {
    'languageCode': 'en-US',
    'voiceId': 'Bianca',
    'wikiLanguage': 'en'
}

default_configfile_name = 'discordbot_config.json'

class ConfigMap():
    def __init__(self, configs: List[Dict[str, Any]], configfile_name: str = None):
        self.log = logging.getLogger('config')
        self._configs = dict()
        self.configfile_name = default_configfile_name or configfile_name

        for cfg in configs:
            id = cfg['id']
            del cfg['id']
            self._configs[id] = cfg

        atexit.register(self.persist)

    def exists(self, id: str):
        return id in self._configs

    def get_config_for(self, id: str, key: str = '', default: Any = None):
        if self.exists(id):
            return self._configs[id] if key == '' else self._configs[id][key] if key in self._configs[id] else default

    def add_config_for(self, id: str, config: Dict[str, Any]):
        self._configs[id] = config
    
    def update_config_for(self, id: str, key: str, val: str):
        if self.exists(id):
            self._configs[id][key] = val

    def remove_config_for(self, id: str):
        if self.exists(id):
            del self._configs[id]

    def set_defaults_for(self, id: str):
        if not self.exists(id):
            self.log.info('Setting default config')
            self.add_config_for(id, defaultConfig)
        pass

    @staticmethod
    def from_file(configfile_name: str = default_configfile_name):
        try:
            with open(configfile_name, 'r') as f:
                data = json.load(f)
                return ConfigMap(data, configfile_name=configfile_name)
        except IOError:
            logging.warn('failed to restore config from file')
            return ConfigMap([], configfile_name=configfile_name) 

    def persist(self):
        self.log.info('Persisting current config state...')
        with open(self.configfile_name, 'w') as f:
            out = []
            for id in self._configs:
                out.append({**self._configs[id], 'id': id})
            json.dump(out, f)