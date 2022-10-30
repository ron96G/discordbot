from typing import List

import discord
from audio.track import Track
from common.context import Context

MAX_FIELDS = 25


async def reply_track_list(ctx: Context, tracks: List[Track]) -> discord.Message:
    """Returns the given tacks in a formatted format to the context channel."""
    embed = discord.Embed(
        title="Current Queue",
        description="The items currently in the queue.",
        color=discord.Color.dark_gold(),
    )

    fields = 1
    for track in tracks:
        i = track.current
        for info in track.get_remaining_tracks():
            i += 1

            if fields >= MAX_FIELDS:
                embed.add_field(
                    name="Too many tracks...",
                    value=f"There are more tracks that could not be listed.",
                    inline=False,
                )
                break
            else:
                fields += 1
                embed.add_field(
                    name=f"Track ({i}/{track.max_len()}):",
                    value=info.pretty_print(),
                    inline=False,
                )

    return await ctx.send(embed=embed)
