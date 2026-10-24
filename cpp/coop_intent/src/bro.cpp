#include "coop_intent/bro.h"

#include <vector>

#include "coop_intent/unicode.h"

namespace coop {

namespace {

// lower case for the three languages' letters (ASCII, Cyrillic with ё, the Spanish accents stay as they are)
std::u32string Lower(const std::string& line) {
    std::u32string u = DecodeUtf8(line);
    for (char32_t& c : u) {
        if (c >= U'A' && c <= U'Z') c = c - U'A' + U'a';
        else if (c >= U'А' && c <= U'Я') c = c - U'А' + U'а';
        else if (c == U'Ё') c = U'ё';
        else if (c == U'Ñ') c = U'ñ';
    }
    return u;
}

bool Letter(char32_t c) {
    return (c >= U'a' && c <= U'z') || (c >= U'а' && c <= U'я') || c == U'ё' || c == U'ñ' || c == U'á' || c == U'é' ||
           c == U'í' || c == U'ó' || c == U'ú' || c == U'ü' || (c >= U'0' && c <= U'9') || c == U'\'';
}

// the line's words, lower case
std::vector<std::u32string> Words(const std::string& line) {
    std::vector<std::u32string> out;
    std::u32string w;
    for (char32_t c : Lower(line)) {
        if (Letter(c)) {
            w += c;
        } else if (!w.empty()) {
            out.push_back(w);
            w.clear();
        }
    }
    if (!w.empty()) out.push_back(w);
    return out;
}

// a word for "brother" as one calls a friend: брат in every case and its diminutives (братан, братишка, братуха, братец,
// братик, братва), бро; bro, brother, bruh, bruv, brah; hermano, hermanito, mano
bool BroWord(const std::u32string& w) {
    static const std::vector<std::u32string> exact = {U"бро", U"bro", U"broh", U"bruh", U"bruv", U"brah", U"brother", U"brotha",
                                                      U"bros", U"brothers", U"hermano", U"hermanos", U"hermanito", U"mano", U"manito"};
    for (const auto& e : exact)
        if (w == e) return true;
    return w.rfind(U"брат", 0) == 0 && w.rfind(U"братств", 0) != 0;   // брат, брата, братан, братишка; not братство
}

// the words around it that forbid it: "stop calling me ...", "не называй меня ...", "no me llames ..."
bool Forbids(const std::vector<std::u32string>& words) {
    auto has = [&](const std::u32string& w) {
        for (const auto& x : words)
            if (x == w) return true;
        return false;
    };
    auto starts = [&](const std::u32string& prefix) {
        for (const auto& x : words)
            if (x.rfind(prefix, 0) == 0) return true;
        return false;
    };
    // "the bro" / "без брата" right after a stop word: "drop the bro", "enough with the bro", "давай без брата"
    auto bro_after = [&](const std::u32string& w) {
        for (size_t i = 0; i + 1 < words.size(); ++i)
            if (words[i] == w && BroWord(words[i + 1])) return true;
        return false;
    };
    // Russian: "не называй / не зови / не говори", "хватит / перестань / прекрати называть / говорить", "без брата";
    // "я тебе не брат", "какой я тебе брат"
    const bool ru_stop = has(U"не") || starts(U"хват") || starts(U"перестан") || starts(U"прекрат") || starts(U"завяз") ||
                         has(U"запрещаю") || has(U"хорош");
    const bool ru_say = starts(U"назыв") || starts(U"назов") || has(U"зови") || has(U"зовите") || starts(U"говор") ||
                        starts(U"скаж") || starts(U"обращ");
    if ((ru_stop && ru_say) || bro_after(U"без")) return true;
    if (has(U"я") && has(U"тебе") && (has(U"не") || has(U"какой"))) return true;
    // English: stop / don't / quit / no more / enough with call / say, "drop the bro", "I'm not your bro"
    const bool en_stop = has(U"stop") || has(U"don't") || has(U"dont") || has(U"quit") || has(U"enough") || (has(U"no") && has(U"more")) ||
                         has(U"cut") || has(U"drop");
    const bool en_say = has(U"call") || has(U"calling") || has(U"say") || has(U"saying");
    if ((en_stop && en_say) || (en_stop && bro_after(U"the")) || (has(U"no") && bro_after(U"more"))) return true;
    if ((has(U"not") || has(U"ain't")) && has(U"your")) return true;
    // Spanish: no me llames, deja de llamarme / decir, basta de, para de, no soy tu hermano
    const bool es_stop = has(U"no") || has(U"deja") || has(U"basta") || has(U"para") || has(U"dejá");
    const bool es_say = starts(U"llam") || starts(U"dec") || starts(U"dig");
    if (es_stop && es_say) return true;
    if (has(U"no") && has(U"soy") && has(U"tu")) return true;
    return false;
}

}  // namespace

BroHabit::Heard BroHabit::Read(const std::string& line) {
    const std::vector<std::u32string> words = Words(line);
    bool bro = false;
    for (const auto& w : words) bro = bro || BroWord(w);
    if (!bro) return Heard::None;
    return Forbids(words) ? Heard::Off : Heard::On;
}

BroHabit::Heard BroHabit::Hear(const std::string& line, double now) {
    const Heard h = Read(line);
    if (h == Heard::On) {
        on_ = true;
        back_at_ = -1;
    } else if (h == Heard::Off) {
        on_ = false;
        back_at_ = relapse_s_ > 0 ? now + relapse_s_ : -1;
    }
    return h;
}

bool BroHabit::Active(double now) {
    if (!on_ && back_at_ >= 0 && now >= back_at_) {
        on_ = true;
        back_at_ = -1;
        relapsed_ = true;
    }
    return on_;
}

}  // namespace coop
