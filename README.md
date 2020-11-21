# Predictor

Fetches matches from RethinkDB previously filled by [Betrievor](https://github.com/belbet/betrievor)

## Example return

```
{
    "draw": {
        "adjusted_drawrate": 0.08711586180568776,
        "good_odds": 14.922655565293663,
        "great_odds": 16.070552147239326,
        "min_odds": 11.478965819456663,
        "ok_odds": 13.774758983347995,
        "warn_odds": 17.218448729184995
    },
    "monaco": {
        "adjusted_winrate": 0.19515174651651,
        "avg_drawrate": 0.13968253968253969,
        "ext": {
            "draw": 19,
            "drawrate": 0.30158730158730157,
            "loss": 26,
            "played": 63,
            "win": 18,
            "winrate": 0.2857142857142857
        },
        "good_odds": 6.661482785602532,
        "great_odds": 7.173904538341187,
        "home": {
            "draw": 13,
            "drawrate": 0.20634920634920634,
            "loss": 20,
            "played": 63,
            "win": 30,
            "winrate": 0.47619047619047616
        },
        "min_odds": 5.124217527386563,
        "ok_odds": 6.149061032863875,
        "paris-saint-germain": {
            "draw": 0,
            "drawrate": 0.0,
            "loss": 3,
            "played": 3,
            "win": 0,
            "winrate": 0.0
        },
        "warn_odds": 7.686326291079844
    },
    "paris-saint-germain": {
        "adjusted_winrate": 0.7177323916777981,
        "avg_drawrate": 0.06438631790744467,
        "ext": {
            "draw": 10,
            "drawrate": 0.14084507042253522,
            "loss": 15,
            "played": 71,
            "win": 46,
            "winrate": 0.647887323943662
        },
        "good_odds": 1.811260039359616,
        "great_odds": 1.950587734694971,
        "home": {
            "draw": 5,
            "drawrate": 0.07042253521126761,
            "loss": 7,
            "played": 71,
            "win": 59,
            "winrate": 0.8309859154929577
        },
        "min_odds": 1.3932769533535507,
        "monaco": {
            "draw": 0,
            "drawrate": 0.0,
            "loss": 0,
            "played": 3,
            "win": 3,
            "winrate": 1.0
        },
        "ok_odds": 1.6719323440242608,
        "warn_odds": 2.089915430030326
    }
}

```
