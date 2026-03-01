"""Time-formatting utilities for playback displays."""


def format_ms(ms: int) -> str:
    """Convert milliseconds to a human-readable string.

    Returns ``H:MM:SS`` when hours > 0, otherwise ``M:SS``.
    Returns ``"–:––"`` for negative values (unknown / not yet available).

    Examples::

        format_ms(0)        # '0:00'
        format_ms(65_000)   # '1:05'
        format_ms(3_723_000) # '1:02:03'
        format_ms(-1)       # '–:––'
    """
    if ms < 0:
        return "–:––"
    total_secs = ms // 1000
    hours, remainder = divmod(total_secs, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"
