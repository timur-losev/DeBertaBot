"""Hand rows for decoder v66 (hand_v66.json): what the owner said on 2026-10-25 22:04 .. 2026-10-27 01:20 that decoder v65
read wrong, with the English the game reads right (TODO_v66.md has the talk). Each row: lang, before (the player's older
lines, oldest first), scene ("" or the game's scene line), text (as heard), en (the English, one order per line), was (what
v65 made of it), label (the order meant). Russian lines the multilingual recognizer wrote in Latin letters are rows as heard
("Ka mnie." is «ко мне»).

    python make_hand_v66.py"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
HOLD = "holding a cardboard box; no car near; last thing: cardboard box, 0 m"
R = [
    # what is that (the owner, 2026-10-26: "what is that/this/it - не понимает")
    ("ru", [], "", "Что это?", ["what is that"], "say again (HOLD_ANGLE 0.61)", "WHAT_IS_IT"),
    ("ru", [], "", "Что это такое?", ["what is that"], "say again (HOLD_ANGLE 0.61)", "WHAT_IS_IT"),
    ("ru", [], "", "Это что такое?", ["what is that"], "-", "WHAT_IS_IT"),
    ("ru", [], "", "Что это было?", ["what was that"], "-", "SMALL_TALK"),
    # getting out of a room ("не понимает как выйти")
    ("ru", [], "", "Выходи из комнаты.", ["go outside"], "Get out of the room. (say again, FALL_BACK 0.51)", "MOVE_TO"),
    ("ru", [], "", "Выходи отсюда.", ["go outside"], "Get out of here. (FALL_BACK at the player)", "MOVE_TO"),
    ("ru", [], "", "Выйди отсюда.", ["go outside"], "Get out of here. (FALL_BACK)", "MOVE_TO"),
    ("ru", [], "", "Выходи отсюда, иди направо.", ["go outside", "go right"], "Get out of here. (FALL_BACK)", "MOVE_TO"),
    ("ru", [], "", "Выйди на улицу.", ["go outside"], "-", "MOVE_TO"),
    # out of the way (GIVE_WAY)
    ("ru", [], "", "Дай пройти.", ["let me through"], "let them through (HELP_INTERACTION)", "GIVE_WAY"),
    ("ru", [], "", "Дай мне пройти.", ["let me through"], "Let me through. (HELP_INTERACTION)", "GIVE_WAY"),
    ("ru", [], "", "Отойди.", ["move away"], "-", "GIVE_WAY"),
    ("ru", [], "", "Уйди с дороги.", ["get out of the way"], "-", "GIVE_WAY"),
    ("en", [], "", "Move away.", ["Move away."], "say again (MOVE_TO 0.43)", "GIVE_WAY"),
    ("en", [], "", "Go away.", ["Go away."], "say again (KILL_YOURSELF 0.33)", "GIVE_WAY"),
    # holding a thing and a negation: keep holding it
    ("ru", [], HOLD, "Не отдавай мне её.", ["keep holding it"], "don't give it to me (WAIT)", "COLLECT"),
    ("ru", [], HOLD, "Не кидай коробку.", ["keep holding the box"], "don't throw the box (WAIT)", "COLLECT"),
    ("ru", [], HOLD, "Не спускай коробку.", ["keep holding the box"], "Don't drop the box. (WAIT)", "COLLECT"),
    # the answer yes, the brother
    ("ru", [], "", "Прямо перед тобой, да.", ["yes that one"], "(DROP)", "YES"),
    ("ru", [], "", "Ты мой брат.", ["you're my brother"], "You're my brother. (say again, SMALL_TALK 0.65)", "SMALL_TALK"),
    # the recognizer's slips of 2026-10-26 15:00 (Parakeet v3, Russian)
    ("ru", [], "", "С меня оружие.", ["put your weapon away"], "get the weapon off me (HOLSTER 0.36)", "HOLSTER"),
    ("ru", [], "", "Залья на коробочку дает.", ["climb on the box"], "-", "JUMP"),
    ("ru", [], "", "Catti.", ["roll it"], "say again (CROUCH 0.60)", "ROLL"),
    # «ко мне», «сюда» heard in Latin letters (2026-10-25 22:07 .. 2026-10-27 01:04)
    ("ru", [], "", "Ka mnie.", ["come to me"], "say again (HELP 0.63)", "FOLLOW_ME"),
    ("ru", [], "", "Kom nie.", ["come to me"], "CROUCH 0.75", "FOLLOW_ME"),
    ("ru", [], "", "Knie.", ["come to me"], "CROUCH", "FOLLOW_ME"),
    ("ru", [], "", "Idzi ka mnie soda.", ["come here"], "FOLLOW_ME (3 order lines)", "FOLLOW_ME"),
    ("ru", [], "", "Girls ka mnie.", ["come to me"], "say again (HELP 0.27)", "FOLLOW_ME"),
    ("ru", [], "", "Wierniz ka mnie.", ["come back to me"], "say again (COVER_ME 0.37)", "COME_BACK"),
    ("ru", [], "", "Zaprywnij ka mnie.", ["jump up to me"], "ask OPEN 0.75", "JUMP"),
    ("ru", [], "", "Okay, that I suda.", ["come here"], "say again (YES 0.28)", "FOLLOW_ME"),
    ("ru", [], "", "E suda.", ["come here"], "NONE", "FOLLOW_ME"),
    ("ru", [], "", "Soda.", ["come here"], "say again (FOLLOW_ME 0.40)", "FOLLOW_ME"),
    ("ru", [], "", "Zabrygnę jeszcze raz.", ["jump on it again"], "REPEAT 0.94", "JUMP"),
    ("ru", [], "", "Climb yellow", ["climb on the yellow table"], "say again (MOVE_TO 0.61)", "JUMP"),
    # glass is a window (2026-10-27 00:05); «разбей стекло» is a butt strike (the owner: «удар прикладом»)
    ("ru", [], "", "Разбей стекло.", ["break the glass"], "break the glass (BREACH 0.87, no place)", "MELEE"),
    ("ru", ["Разбей стекло."], "", "Просто прострели его.", ["just shoot the glass"], "OPEN_FIRE, aim on the bot", "OPEN_FIRE"),
    ("ru", [], "", "Прострелит о стекло.", ["shoot that glass"], "OPEN_FIRE at the crosshair, no object", "OPEN_FIRE"),
    ("ru", [], "", "Ударь окно прикладом.", ["hit the window with your rifle butt"], "MELEE 0.59, say again; 'rifle' a place", "MELEE"),
    # a correction keeps the thing (the owner's question, 2026-10-27)
    ("ru", ["Разбей стекло."], "", "Нет, оружием.", ["shoot the glass"], "Use your weapon. (SWITCH_WEAPON)", "OPEN_FIRE"),
    ("ru", ["Разбей стекло."], "", "Нет, из оружия.", ["shoot the glass"], "Use your gun. (SWITCH_WEAPON)", "OPEN_FIRE"),
    ("ru", ["Разбей стекло."], "", "Нет, стреляй.", ["shoot the glass"], "Shoot. (OPEN_FIRE at the crosshair)", "OPEN_FIRE"),
    ("ru", ["Ударь окно прикладом."], "", "Нет, оружием.", ["shoot the window"], "Use your weapon. (SWITCH_WEAPON)", "OPEN_FIRE"),
    ("ru", ["Ударь окно прикладом."], "", "Нет, стреляй в него.", ["shoot the window"], "shoot him (OPEN_FIRE, no place)", "OPEN_FIRE"),
    # left from round v65: getting back on after getting off
    ("ru", ["Слезь."], "no car near; last thing: cardboard box, 1 m", "Запрыгни.", ["jump up on it"], "jump on it again (the way down)", "JUMP"),
    ("ru", ["Слезь с коробки."], "no car near; last thing: cardboard box, 1 m", "Запрыгни обратно.", ["jump back on it"], "-", "JUMP"),
    ("en", [], "standing on a cable spool; no car near; last thing: cable spool, 0 m", "Get down, get down!", ["climb down"],
     "written back (cover)", "JUMP"),
    ("en", [], "a car 5 m away", "Get in, get in!", ["get in the car"], "MOVE_TO", "GET_IN"),
    ("en", [], "", "How we doing bro?", ["How we doing bro?"], "say again", "STATUS_REPORT"),
    ("en", [], "", "Press it forward.", ["push it forward"], "SUPPRESS", "PUSH"),
]


def main():
    items = [{"lang": l, "before": b, "scene": s, "text": t, "en": e, "was": w, "label": lab} for l, b, s, t, e, w, lab in R]
    note = ("Hand rows for decoder v66, written 2026-10-27 from the owner's games of 2026-10-25 22:04 .. 2026-10-27 01:20 (TODO_v66.md) "
            "and decoder v65's answers replayed through the deployed chain (make_hand_v66.py). The English uses the words bot v66 reads "
            "as meant: glass is a window, «разбей» is a butt strike (MELEE), going outside is 'go outside', a correction gives the other "
            "way on the thing of the line before without the 'no'.")
    json.dump({"_note": note, "items": items}, io.open(os.path.join(HERE, "hand_v66.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(items), "hand rows")


if __name__ == "__main__":
    main()
