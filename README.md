# Discordbot


## Known Limitations

- Race condition in queue when multiple songs are added at the (nearly) same time (possible fix by using a lock?!)
- Many exceptions are not handled properly (possible fix by implementin exception handler)
- Queue is lost when the bot connects again
- Queue is lost when the voice client of the bot reconnects
- Voice client in tasks is not updated when the voice client changes (thus queue is completely useless until it is removed after 1m)
- Bot does not disconnect automatically after a certain duration of inactivity