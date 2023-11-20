# GuessTheBot

A Python Discord bot for a small server I'm a member of. It collects the emoji strings commonly used to share results from [Wordle](https://www.nytimes.com/games/wordle/index.html) like games. It extracts the scores and saves them in a database. For the moment it only extracts scores from [GuessThe.Game](https://guessthe.game/), as that's what we are mostly playing.

The bot is built on the foundation of [hikari](https://github.com/hikari-py/hikari) and [hikari-crescent](https://github.com/hikari-crescent/hikari-crescent). It uses [PonyORM](https://ponyorm.org/) for database access.
