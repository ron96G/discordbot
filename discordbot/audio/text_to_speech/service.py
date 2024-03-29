import logging
import os
from contextlib import closing

from botocore.exceptions import BotoCoreError, ClientError, ValidationError

from ..track import TrackInfo

ENGINE = "standard"  # 'standard'|'neural'
OUTPUT_FORMAT = "mp3"  # 'json'|'mp3'|'ogg_vorbis'|'pcm'
SAMPLE_RATE = "16000"


class TextToSpeechError(Exception):
    def __init__(self, msg, thrown=None):
        super().__init__(msg)
        self.thrown = thrown


class TextToSpeechService:

    log = logging.getLogger("text2speech")

    def __init__(
        self,
        polly_client,
        dir="./polly/",
    ):
        self.polly = polly_client
        self.dir = dir

        if not os.path.exists(self.dir):
            os.makedirs(self.dir)

    def synthesize_speech(
        self, id: str, message: str, lang_code: str, voice_id: str
    ) -> TrackInfo:
        try:
            self.log.info(
                f"{id}: Trying to synthesize speech with length {len(message)}"
            )
            response = self.polly.synthesize_speech(
                Engine=ENGINE,
                OutputFormat=OUTPUT_FORMAT,
                SampleRate=SAMPLE_RATE,
                LanguageCode=lang_code,
                Text=message,
                VoiceId=voice_id,
            )

            output = os.path.join(self.dir, f"{id}.mp3")
            if "AudioStream" in response:
                with closing(response["AudioStream"]) as stream:

                    with closing(open(output, "wb")) as file:
                        file.write(stream.read())
            else:
                raise TextToSpeechError("no audiostream found in the polly response")

        except ClientError as e:
            raise TextToSpeechError("failed to synthesize speech", e)
        except (BotoCoreError, ValidationError) as e:
            raise TextToSpeechError(f"failed to synthesize speech: {e.fmt}")

        return TrackInfo("", "SynthesizeSpeech", None, output)
