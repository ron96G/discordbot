import spotipy, logging, re

SPOTIFY_MARKET = "DE"

class Spotify():
    def __init__(self, service: spotipy.Spotify):
        self.service = service
        self.log = logging.getLogger('svc')
        self.id_re = re.compile(r'^[A-Za-z0-9]{22}$')

    def __del__(self):
        pass
    
    def is_spotify_url_or_id(self, url_or_id: str) -> bool:
        is_url = 'spotify' in url_or_id
        is_id =  bool(self.id_re.match(url_or_id))
        return is_url | is_id

    async def get_info(self, id_or_url: str):
        self.log.info(f'Searching spotify for "{id_or_url}"')
        track = self.service.track(id_or_url, market=SPOTIFY_MARKET)

        self.log.debug(track)

        return {
            'artist': track['artists'][0]['name'],
            'name': track['name']
        }