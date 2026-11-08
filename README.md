# Han Tiles dictionary data

The Chinese–English dictionary behind Han Tiles, an iPad app by Andrej Balas
for learning to write Chinese characters. It covers 9,574 characters and about 75,000
words, with pinyin, English meanings, HSK levels and frequency ranks, in both
simplified and traditional characters.

It is built from these open sources (see [SOURCES.md](SOURCES.md)):

- [CC-CEDICT](https://cc-cedict.org/wiki/), by MDBG and the CC-CEDICT contributors (CC BY-SA 4.0)
- [Make Me a Hanzi](https://github.com/skishore/makemeahanzi) `dictionary.txt`, by Shaunak Kishore, derived from Unihan and CJKlib (LGPL 3.0 or later)
- [Complete HSK Vocabulary](https://github.com/drkameleon/complete-hsk-vocabulary), by Yanis Zafirópulos (MIT)

Thank you to their authors and contributors.

## Files

| File | Contents |
| --- | --- |
| `search_index.json` | The dictionary, as used by the app |
| `build_search_index.py` | The script that builds it from the sources |
| `SOURCES.md` | Where each part comes from, and how to rebuild it |
| `LICENSE` | License of the data |
| `LGPL-3.0.txt`, `GPL-3.0.txt` | Full license texts for the Make Me a Hanzi parts |

## Format

One JSON object, with short keys to keep the file small:

```json
{
  "c":   [{"h": "字", "p": "zì", "r": ["zi4", "zi5"], "g": ["letter", "symbol", "character", "word"], "f": 829}],
  "w":   [{"h": "学习", "t": "學習", "p": "xué xí", "n": "xue2 xi2", "g": ["learn", "study"], "f": 789}],
  "s2t": {"学": "學"},
  "t2s": {"學": "学"}
}
```

- `c`: characters. `h` character, `p` pinyin with tone marks, `r` readings with tone numbers, `g` meanings, `f` frequency rank (lower is more common).
- `w`: words. `h` simplified, `t` traditional, `p` pinyin with tone marks, `n` pinyin with tone numbers, `g` meanings, `f` frequency rank.
- `s2t` / `t2s`: simplified-to-traditional and traditional-to-simplified character maps.

Meanings may start with a marker: `^` a meaning followed by a usage note, such as
"you (informal)"; `~` a qualified or secondary meaning, such as "(coll.) what".

## License

The data is licensed under
[Creative Commons Attribution-ShareAlike 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
The parts derived from Make Me a Hanzi's `dictionary.txt` are also available under the
GNU LGPL 3.0 or later. See [LICENSE](LICENSE).

The Han Tiles app itself is not open source; this repository contains only its
dictionary data.

Found a wrong meaning or reading? Please open an issue.
