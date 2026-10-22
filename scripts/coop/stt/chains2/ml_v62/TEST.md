# Test lines in Russian or Spanish (round v62, blind test sets)

## The game

A tactical co-op shooter: a player gives voice orders in their own language to an AI teammate (the bot). We test whether
the bot understands Russian and Spanish players.

## Your job

You are a native speaker of `lang` (`ru` or `es`) who plays these games. For each English line, say the same thing **as
you would say it in voice chat**: spoken, natural, in your own words. You may rephrase freely, use game slang, be short
or chatty. You must keep:
- **the same orders, in the same order;**
- **the same places:** which door, window, stairs, floor, colour, compass side, "my pin / marker";
- **the same conditions:** "on my go", "once it pops", "first… then…";
- **the same negations.**

In `ctx` files:
- translate the player's earlier lines (`before`) and the line now (`en`) as one person talking;
- `bot` is the bot's line, for understanding only: do **not** translate it;
- keep pronouns that point back ("on it", "that one", "again").

## Output

A JSON file with the same name in `../test_out/`:

    {"lang": "...", "set": "...", "items": [{"id": "...", "text": "..."}]}

For `ctx` items, add `"before": [...]`. Include every id exactly once. Write only your lines, and change no other file.
