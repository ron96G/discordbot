# Discordbot

## Supported Features

| Feature | Supported |
| :--------------- | :------ |
| !Help command | ✅ |
| Play music from Youtube | ✅ |
| Play music from Spotify | ✅ |
| Play music by query | ✅ |
| Play music from local filesystem | ❌ |
| Queueing of audio sources | ✅ |
| General handling (skipping, ...) of audio sources | ✅ |
| Text2Speech from string (using AWS Polly) | ✅ |
| Text2Speech from file (using AWS Polly) | ❌ |
| Wikipedia API integration with Text2Speech | ✅ |
| Persisted configuration managed per connected guild | ✅ |
| Logging | ✅ |
| Installation script for e. g. AWS EC2 | ✅ |

## Known Limitations

- Many exceptions are not handled properly (possible fix by implementin exception handler)
- Bot does not disconnect automatically after a certain duration of inactivity