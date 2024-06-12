These files are each cahpter of the Bible stored as JSON objects. Each element of these objects is a verse, indexed by its number, which in turn holds each individual word (or token) of the original text. Each word is represented as a JSON object with the following properties:
- `strongs`: the Strong's number and description of the word
- `transliteration`: the transliteration of the word
- `native`: the original word in its native script
- `eng`: the English translation of the word
- `grammar`: the grammar of the word

This information is the same can be found at [https://biblehub.com/interlinear/](https://biblehub.com/interlinear/).
