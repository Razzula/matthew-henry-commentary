# public-domain-bible-resources

This repository contains a collection of public domain Bible resources. The resources are stored in various formats. They are all each formatted specifically to work in [this Bible app](https://github.com/Razzula/bible-app). The resources include the following:

Public domain texts. No rights reserved. May be distributed freely.

## Matthew Henry's Complete Commentary on the Bible (MHC)
Originally written in 1706, Matthew Henry's six volume Complete Commentary provides an exhaustive look at every verse in the Bible.

## Challoner's Douay-Rheims Bible Version (CDRV1752)
Originally published in 1752, this version of the Douay-Rheims Bible was revised by Bishop Richard Challoner. The contents taken from this are only the 'Duterocanonical' books, in this repo.

## World English Bible British Edition (WEBBE)
The World English Bible is a public domain translation of the Bible that is based on the American Standard Version of the Bible. The British Edition is a revision of the WEB that uses British English spelling and grammar.

The USFM used to generate the format provided here is available at [http://ebible.org/details.php?id=engwebpb](http://ebible.org/details.php?id=engwebpb).

## Interlinear Bible with Strongs Numbers
These files are each chapter of the Bible stored as JSON objects. Each element of these objects is a verse, indexed by its number, which in turn holds each individual word (or token) of the original text. Each word is represented as a JSON object with the following properties:
- `strongs`: the Strong's number and description of the word
- `transliteration`: the transliteration of the word
- `native`: the original word in its native script
- `eng`: the English translation of the word
- `grammar`: the grammar of the word

This information is the same can be found at [https://biblehub.com/interlinear/](https://biblehub.com/interlinear/).
