# clean_links_mapper High-Similarity Failures

These are cases where status matches the reference, normalized text does not exactly match, and SequenceMatcher similarity >= 0.98.

Total cases: 40

## Case 1: instance `2c58dd0ff3af6190`, variant `0`

- source line: `44`
- prompt style: `analyst_handoff`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `5606` / `5553` / `5606`
- similarity pred-vs-ref: `0.9953`
- instruction: strip out http, https, ftp, www, and other link-like addresses from these text samples

Input around first ref/pred diff:
```text
rsity]], whose lettermark resembles "ATM"
* [[ATM (method)]] ({{langx|id|amati, tiru, modifikasi|lit=observe, imitate, modify|links=no}}), a widely used approach in Indonesia's business sector

==See also==
{{Self-reference tool}}
* [[ATMS (disambiguation)]]
{{Disambiguation}}
{{DEFAULTSORT:Atm}}
[[Category:Bangladeshi masculine given names]]
[[Category:Masculine given names]]
```
Reference around first diff:
```text
rsity]], whose lettermark resembles "ATM"
* [[ATM (method)]] ({{langx|id|amati, tiru, modifikasi|lit=observe, imitate, modify|links=no}}), a widely used approach in Indonesia's business sector

==See also==
{{Self-reference tool}}
* [[ATMS (disambiguation)]]
{{Disambiguation}}
{{}}
[[ masculine given names]]
[[ given names]]
```
Prediction around first diff:
```text
rsity]], whose lettermark resembles "ATM"
* [[ATM (method)]] ({{langx|id|amati, tiru, modifikasi|lit=observe, imitate, modify|links=no}}), a widely used approach in Indonesia's business sector

==See also==
{{Self-reference tool}}
* [[ATMS (disambiguation)]]
{{Disambiguation}}
{{DEFAULTSORT:Atm}}
[[Category:Bangladeshi masculine given names]]
[[Category:Masculine given names]]
```

## Case 2: instance `2c58dd0ff3af6190`, variant `2`

- source line: `44`
- prompt style: `concise_brief`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `5606` / `5553` / `5606`
- similarity pred-vs-ref: `0.9953`
- instruction: Remove all URLs and web links from the text

Input around first ref/pred diff:
```text
rsity]], whose lettermark resembles "ATM"
* [[ATM (method)]] ({{langx|id|amati, tiru, modifikasi|lit=observe, imitate, modify|links=no}}), a widely used approach in Indonesia's business sector

==See also==
{{Self-reference tool}}
* [[ATMS (disambiguation)]]
{{Disambiguation}}
{{DEFAULTSORT:Atm}}
[[Category:Bangladeshi masculine given names]]
[[Category:Masculine given names]]
```
Reference around first diff:
```text
rsity]], whose lettermark resembles "ATM"
* [[ATM (method)]] ({{langx|id|amati, tiru, modifikasi|lit=observe, imitate, modify|links=no}}), a widely used approach in Indonesia's business sector

==See also==
{{Self-reference tool}}
* [[ATMS (disambiguation)]]
{{Disambiguation}}
{{}}
[[ masculine given names]]
[[ given names]]
```
Prediction around first diff:
```text
rsity]], whose lettermark resembles "ATM"
* [[ATM (method)]] ({{langx|id|amati, tiru, modifikasi|lit=observe, imitate, modify|links=no}}), a widely used approach in Indonesia's business sector

==See also==
{{Self-reference tool}}
* [[ATMS (disambiguation)]]
{{Disambiguation}}
{{DEFAULTSORT:Atm}}
[[Category:Bangladeshi masculine given names]]
[[Category:Masculine given names]]
```

## Case 3: instance `2c58dd0ff3af6190`, variant `3`

- source line: `44`
- prompt style: `conversational_cooperative`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `5606` / `5553` / `5606`
- similarity pred-vs-ref: `0.9953`
- instruction: remove any web links from it, including normal URLs and similar online addresses.

Input around first ref/pred diff:
```text
rsity]], whose lettermark resembles "ATM"
* [[ATM (method)]] ({{langx|id|amati, tiru, modifikasi|lit=observe, imitate, modify|links=no}}), a widely used approach in Indonesia's business sector

==See also==
{{Self-reference tool}}
* [[ATMS (disambiguation)]]
{{Disambiguation}}
{{DEFAULTSORT:Atm}}
[[Category:Bangladeshi masculine given names]]
[[Category:Masculine given names]]
```
Reference around first diff:
```text
rsity]], whose lettermark resembles "ATM"
* [[ATM (method)]] ({{langx|id|amati, tiru, modifikasi|lit=observe, imitate, modify|links=no}}), a widely used approach in Indonesia's business sector

==See also==
{{Self-reference tool}}
* [[ATMS (disambiguation)]]
{{Disambiguation}}
{{}}
[[ masculine given names]]
[[ given names]]
```
Prediction around first diff:
```text
rsity]], whose lettermark resembles "ATM"
* [[ATM (method)]] ({{langx|id|amati, tiru, modifikasi|lit=observe, imitate, modify|links=no}}), a widely used approach in Indonesia's business sector

==See also==
{{Self-reference tool}}
* [[ATMS (disambiguation)]]
{{Disambiguation}}
{{DEFAULTSORT:Atm}}
[[Category:Bangladeshi masculine given names]]
[[Category:Masculine given names]]
```

## Case 4: instance `2c58dd0ff3af6190`, variant `4`

- source line: `44`
- prompt style: `end_weighted_instruction`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `5606` / `5553` / `5606`
- similarity pred-vs-ref: `0.9953`
- instruction: delete any embedded URLs or other recognizable web links so the remaining content is link-free.

Input around first ref/pred diff:
```text
rsity]], whose lettermark resembles "ATM"
* [[ATM (method)]] ({{langx|id|amati, tiru, modifikasi|lit=observe, imitate, modify|links=no}}), a widely used approach in Indonesia's business sector

==See also==
{{Self-reference tool}}
* [[ATMS (disambiguation)]]
{{Disambiguation}}
{{DEFAULTSORT:Atm}}
[[Category:Bangladeshi masculine given names]]
[[Category:Masculine given names]]
```
Reference around first diff:
```text
rsity]], whose lettermark resembles "ATM"
* [[ATM (method)]] ({{langx|id|amati, tiru, modifikasi|lit=observe, imitate, modify|links=no}}), a widely used approach in Indonesia's business sector

==See also==
{{Self-reference tool}}
* [[ATMS (disambiguation)]]
{{Disambiguation}}
{{}}
[[ masculine given names]]
[[ given names]]
```
Prediction around first diff:
```text
rsity]], whose lettermark resembles "ATM"
* [[ATM (method)]] ({{langx|id|amati, tiru, modifikasi|lit=observe, imitate, modify|links=no}}), a widely used approach in Indonesia's business sector

==See also==
{{Self-reference tool}}
* [[ATMS (disambiguation)]]
{{Disambiguation}}
{{DEFAULTSORT:Atm}}
[[Category:Bangladeshi masculine given names]]
[[Category:Masculine given names]]
```

## Case 5: instance `2c58dd0ff3af6190`, variant `5`

- source line: `44`
- prompt style: `goal_oriented`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `5606` / `5553` / `5606`
- similarity pred-vs-ref: `0.9953`
- instruction: the final text should no longer contain http, https, ftp, www-style links, or other web addresses.

Input around first ref/pred diff:
```text
rsity]], whose lettermark resembles "ATM"
* [[ATM (method)]] ({{langx|id|amati, tiru, modifikasi|lit=observe, imitate, modify|links=no}}), a widely used approach in Indonesia's business sector

==See also==
{{Self-reference tool}}
* [[ATMS (disambiguation)]]
{{Disambiguation}}
{{DEFAULTSORT:Atm}}
[[Category:Bangladeshi masculine given names]]
[[Category:Masculine given names]]
```
Reference around first diff:
```text
rsity]], whose lettermark resembles "ATM"
* [[ATM (method)]] ({{langx|id|amati, tiru, modifikasi|lit=observe, imitate, modify|links=no}}), a widely used approach in Indonesia's business sector

==See also==
{{Self-reference tool}}
* [[ATMS (disambiguation)]]
{{Disambiguation}}
{{}}
[[ masculine given names]]
[[ given names]]
```
Prediction around first diff:
```text
rsity]], whose lettermark resembles "ATM"
* [[ATM (method)]] ({{langx|id|amati, tiru, modifikasi|lit=observe, imitate, modify|links=no}}), a widely used approach in Indonesia's business sector

==See also==
{{Self-reference tool}}
* [[ATMS (disambiguation)]]
{{Disambiguation}}
{{DEFAULTSORT:Atm}}
[[Category:Bangladeshi masculine given names]]
[[Category:Masculine given names]]
```

## Case 6: instance `2c58dd0ff3af6190`, variant `6`

- source line: `44`
- prompt style: `imperative_checklist`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `5606` / `5553` / `5606`
- similarity pred-vs-ref: `0.9953`
- instruction: remove all web links and URLs from the text, including http, https, ftp, and similar address-style links.

Input around first ref/pred diff:
```text
rsity]], whose lettermark resembles "ATM"
* [[ATM (method)]] ({{langx|id|amati, tiru, modifikasi|lit=observe, imitate, modify|links=no}}), a widely used approach in Indonesia's business sector

==See also==
{{Self-reference tool}}
* [[ATMS (disambiguation)]]
{{Disambiguation}}
{{DEFAULTSORT:Atm}}
[[Category:Bangladeshi masculine given names]]
[[Category:Masculine given names]]
```
Reference around first diff:
```text
rsity]], whose lettermark resembles "ATM"
* [[ATM (method)]] ({{langx|id|amati, tiru, modifikasi|lit=observe, imitate, modify|links=no}}), a widely used approach in Indonesia's business sector

==See also==
{{Self-reference tool}}
* [[ATMS (disambiguation)]]
{{Disambiguation}}
{{}}
[[ masculine given names]]
[[ given names]]
```
Prediction around first diff:
```text
rsity]], whose lettermark resembles "ATM"
* [[ATM (method)]] ({{langx|id|amati, tiru, modifikasi|lit=observe, imitate, modify|links=no}}), a widely used approach in Indonesia's business sector

==See also==
{{Self-reference tool}}
* [[ATMS (disambiguation)]]
{{Disambiguation}}
{{DEFAULTSORT:Atm}}
[[Category:Bangladeshi masculine given names]]
[[Category:Masculine given names]]
```

## Case 7: instance `2c58dd0ff3af6190`, variant `8`

- source line: `44`
- prompt style: `policy_like`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `5606` / `5553` / `5606`
- similarity pred-vs-ref: `0.9953`
- instruction: the usable version of the text must not retain URLs, embedded links, or other recognizable web addresses.

Input around first ref/pred diff:
```text
rsity]], whose lettermark resembles "ATM"
* [[ATM (method)]] ({{langx|id|amati, tiru, modifikasi|lit=observe, imitate, modify|links=no}}), a widely used approach in Indonesia's business sector

==See also==
{{Self-reference tool}}
* [[ATMS (disambiguation)]]
{{Disambiguation}}
{{DEFAULTSORT:Atm}}
[[Category:Bangladeshi masculine given names]]
[[Category:Masculine given names]]
```
Reference around first diff:
```text
rsity]], whose lettermark resembles "ATM"
* [[ATM (method)]] ({{langx|id|amati, tiru, modifikasi|lit=observe, imitate, modify|links=no}}), a widely used approach in Indonesia's business sector

==See also==
{{Self-reference tool}}
* [[ATMS (disambiguation)]]
{{Disambiguation}}
{{}}
[[ masculine given names]]
[[ given names]]
```
Prediction around first diff:
```text
rsity]], whose lettermark resembles "ATM"
* [[ATM (method)]] ({{langx|id|amati, tiru, modifikasi|lit=observe, imitate, modify|links=no}}), a widely used approach in Indonesia's business sector

==See also==
{{Self-reference tool}}
* [[ATMS (disambiguation)]]
{{Disambiguation}}
{{DEFAULTSORT:Atm}}
[[Category:Bangladeshi masculine given names]]
[[Category:Masculine given names]]
```

## Case 8: instance `2c58dd0ff3af6190`, variant `9`

- source line: `44`
- prompt style: `qa_request`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `5606` / `5553` / `5606`
- similarity pred-vs-ref: `0.9953`
- instruction: strip out any URL-like content from this text and consider it usable only after those web links have been removed.

Input around first ref/pred diff:
```text
rsity]], whose lettermark resembles "ATM"
* [[ATM (method)]] ({{langx|id|amati, tiru, modifikasi|lit=observe, imitate, modify|links=no}}), a widely used approach in Indonesia's business sector

==See also==
{{Self-reference tool}}
* [[ATMS (disambiguation)]]
{{Disambiguation}}
{{DEFAULTSORT:Atm}}
[[Category:Bangladeshi masculine given names]]
[[Category:Masculine given names]]
```
Reference around first diff:
```text
rsity]], whose lettermark resembles "ATM"
* [[ATM (method)]] ({{langx|id|amati, tiru, modifikasi|lit=observe, imitate, modify|links=no}}), a widely used approach in Indonesia's business sector

==See also==
{{Self-reference tool}}
* [[ATMS (disambiguation)]]
{{Disambiguation}}
{{}}
[[ masculine given names]]
[[ given names]]
```
Prediction around first diff:
```text
rsity]], whose lettermark resembles "ATM"
* [[ATM (method)]] ({{langx|id|amati, tiru, modifikasi|lit=observe, imitate, modify|links=no}}), a widely used approach in Indonesia's business sector

==See also==
{{Self-reference tool}}
* [[ATMS (disambiguation)]]
{{Disambiguation}}
{{DEFAULTSORT:Atm}}
[[Category:Bangladeshi masculine given names]]
[[Category:Masculine given names]]
```

## Case 9: instance `4e1d9249cba07140`, variant `0`

- source line: `48`
- prompt style: `analyst_handoff`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `5829` / `4793` / `4878`
- similarity pred-vs-ref: `0.9912`
- instruction: strip out http, https, ftp, www, and other link-like addresses from these text samples

Input around first ref/pred diff:
```text
Frazer, F.B.A., F.R.S. in 2 Volumes, Cambridge, MA, Harvard University Press; London, William Heinemann Ltd. 1921. ISBN 0-674-99135-4. [http://www.perseus.tufts.edu/hopper/text?doc=Perseus:text:1999.01.0022 Online version at the Perseus Digital Library.] [http://www.perseus.tufts.edu/hopper/text?doc=Perseus:text:1999.01.0021 Greek text available from the same website].
*[[Pausanias (geographer)|Pausanias]], ''Description of Greece'' with an English Translation by W.H.S. Jones, Litt.D., and H.A. Ormerod, M.A., in 4 Volumes. Cambridge, MA, Harvard Universi
```
Reference around first diff:
```text
text available at the Perseus Digital Library].
*[[Clement of Alexandria|Titus Flavius Clemens]], ''Exhortation against the Pagans'' translated by Butterworth, G W. Loeb Classical Library Volume 92. Cambridge, MA. Harvard University Press. 1919. [ Online version at theio.com]

[[ of Lycaon]]
[[ in Greek mythology]]
[[ kings of Arcadia]]
[[ Arcadians]]
[[ sacrifice in folklore and mythology]]
```
Prediction around first diff:
```text
text available at the Perseus Digital Library].
*[[Clement of Alexandria|Titus Flavius Clemens]], ''Exhortation against the Pagans'' translated by Butterworth, G W. Loeb Classical Library Volume 92. Cambridge, MA. Harvard University Press. 1919. [ Online version at theio.com]

[[Category:Sons of Lycaon]]
[[Category:Princes in Greek mythology]]
[[Category:Mythological kings of Arcadia]]
[[Category:Mythological Arcadians]]
[[Category:Human sacrifice in folklore and mythology]]
```

## Case 10: instance `4e1d9249cba07140`, variant `1`

- source line: `48`
- prompt style: `application_context`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `5829` / `4793` / `4845`
- similarity pred-vs-ref: `0.9878`
- instruction: embedded links, including standard URLs and similar web addresses, are removed before the text is used for retrieval.

Input around first ref/pred diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, [http://www.perseus.tufts.edu/hopper/text?doc=Paus.+8.17.6&fromdoc=Perseus%3Atext%3A1999.01.0160:chapter=&highlight=Nonacris 8.17.6]</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the po
```
Reference around first diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, [ 8.17.6]</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the possible [[eponym]]s for the city of [[Psophis]]. This can be explained by the following genealogical link; Nyctimus, Periphe
```
Prediction around first diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, 8.17.6</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the possible [[eponym]]s for the city of [[Psophis]]. This can be explained by the following genealogical link; Nyctimus, Periphetes
```

## Case 11: instance `4e1d9249cba07140`, variant `2`

- source line: `48`
- prompt style: `concise_brief`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `5829` / `4793` / `4855`
- similarity pred-vs-ref: `0.9888`
- instruction: Remove all URLs and web links from the text

Input around first ref/pred diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, [http://www.perseus.tufts.edu/hopper/text?doc=Paus.+8.17.6&fromdoc=Perseus%3Atext%3A1999.01.0160:chapter=&highlight=Nonacris 8.17.6]</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the po
```
Reference around first diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, [ 8.17.6]</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the possible [[eponym]]s for the city of [[Psophis]]. This can be explained by the following genealogical link; Nyctimus, Periphe
```
Prediction around first diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, 8.17.6</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the possible [[eponym]]s for the city of [[Psophis]]. This can be explained by the following genealogical link; Nyctimus, Periphetes
```

## Case 12: instance `4e1d9249cba07140`, variant `3`

- source line: `48`
- prompt style: `conversational_cooperative`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `5829` / `4793` / `4849`
- similarity pred-vs-ref: `0.9882`
- instruction: remove any web links from it, including normal URLs and similar online addresses.

Input around first ref/pred diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, [http://www.perseus.tufts.edu/hopper/text?doc=Paus.+8.17.6&fromdoc=Perseus%3Atext%3A1999.01.0160:chapter=&highlight=Nonacris 8.17.6]</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the po
```
Reference around first diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, [ 8.17.6]</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the possible [[eponym]]s for the city of [[Psophis]]. This can be explained by the following genealogical link; Nyctimus, Periphe
```
Prediction around first diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, 8.17.6</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the possible [[eponym]]s for the city of [[Psophis]]. This can be explained by the following genealogical link; Nyctimus, Periphetes
```

## Case 13: instance `4e1d9249cba07140`, variant `4`

- source line: `48`
- prompt style: `end_weighted_instruction`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `5829` / `4793` / `4838`
- similarity pred-vs-ref: `0.9870`
- instruction: delete any embedded URLs or other recognizable web links so the remaining content is link-free.

Input around first ref/pred diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, [http://www.perseus.tufts.edu/hopper/text?doc=Paus.+8.17.6&fromdoc=Perseus%3Atext%3A1999.01.0160:chapter=&highlight=Nonacris 8.17.6]</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the po
```
Reference around first diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, [ 8.17.6]</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the possible [[eponym]]s for the city of [[Psophis]]. This can be explained by the following genealogical link; Nyctimus, Periphe
```
Prediction around first diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, 8.17.6</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the possible [[eponym]]s for the city of [[Psophis]]. This can be explained by the following genealogical link; Nyctimus, Periphetes
```

## Case 14: instance `4e1d9249cba07140`, variant `5`

- source line: `48`
- prompt style: `goal_oriented`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `5829` / `4793` / `4848`
- similarity pred-vs-ref: `0.9881`
- instruction: the final text should no longer contain http, https, ftp, www-style links, or other web addresses.

Input around first ref/pred diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, [http://www.perseus.tufts.edu/hopper/text?doc=Paus.+8.17.6&fromdoc=Perseus%3Atext%3A1999.01.0160:chapter=&highlight=Nonacris 8.17.6]</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the po
```
Reference around first diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, [ 8.17.6]</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the possible [[eponym]]s for the city of [[Psophis]]. This can be explained by the following genealogical link; Nyctimus, Periphe
```
Prediction around first diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, 8.17.6</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the possible [[eponym]]s for the city of [[Psophis]]. This can be explained by the following genealogical link; Nyctimus, Periphetes
```

## Case 15: instance `4e1d9249cba07140`, variant `6`

- source line: `48`
- prompt style: `imperative_checklist`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `5829` / `4793` / `4850`
- similarity pred-vs-ref: `0.9883`
- instruction: remove all web links and URLs from the text, including http, https, ftp, and similar address-style links.

Input around first ref/pred diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, [http://www.perseus.tufts.edu/hopper/text?doc=Paus.+8.17.6&fromdoc=Perseus%3Atext%3A1999.01.0160:chapter=&highlight=Nonacris 8.17.6]</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the po
```
Reference around first diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, [ 8.17.6]</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the possible [[eponym]]s for the city of [[Psophis]]. This can be explained by the following genealogical link; Nyctimus, Periphe
```
Prediction around first diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, 8.17.6</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the possible [[eponym]]s for the city of [[Psophis]]. This can be explained by the following genealogical link; Nyctimus, Periphetes
```

## Case 16: instance `4e1d9249cba07140`, variant `7`

- source line: `48`
- prompt style: `negative_constraint_driven`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `5829` / `4793` / `4845`
- similarity pred-vs-ref: `0.9878`
- instruction: embedded web addresses or link-like URL text; also clean the text by deleting all such links.

Input around first ref/pred diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, [http://www.perseus.tufts.edu/hopper/text?doc=Paus.+8.17.6&fromdoc=Perseus%3Atext%3A1999.01.0160:chapter=&highlight=Nonacris 8.17.6]</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the po
```
Reference around first diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, [ 8.17.6]</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the possible [[eponym]]s for the city of [[Psophis]]. This can be explained by the following genealogical link; Nyctimus, Periphe
```
Prediction around first diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, 8.17.6</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the possible [[eponym]]s for the city of [[Psophis]]. This can be explained by the following genealogical link; Nyctimus, Periphetes
```

## Case 17: instance `4e1d9249cba07140`, variant `8`

- source line: `48`
- prompt style: `policy_like`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `5829` / `4793` / `4838`
- similarity pred-vs-ref: `0.9870`
- instruction: the usable version of the text must not retain URLs, embedded links, or other recognizable web addresses.

Input around first ref/pred diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, [http://www.perseus.tufts.edu/hopper/text?doc=Paus.+8.17.6&fromdoc=Perseus%3Atext%3A1999.01.0160:chapter=&highlight=Nonacris 8.17.6]</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the po
```
Reference around first diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, [ 8.17.6]</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the possible [[eponym]]s for the city of [[Psophis]]. This can be explained by the following genealogical link; Nyctimus, Periphe
```
Prediction around first diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, 8.17.6</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the possible [[eponym]]s for the city of [[Psophis]]. This can be explained by the following genealogical link; Nyctimus, Periphetes
```

## Case 18: instance `4e1d9249cba07140`, variant `9`

- source line: `48`
- prompt style: `qa_request`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `5829` / `4793` / `4860`
- similarity pred-vs-ref: `0.9893`
- instruction: strip out any URL-like content from this text and consider it usable only after those web links have been removed.

Input around first ref/pred diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, [http://www.perseus.tufts.edu/hopper/text?doc=Paus.+8.17.6&fromdoc=Perseus%3Atext%3A1999.01.0160:chapter=&highlight=Nonacris 8.17.6]</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the po
```
Reference around first diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, [ 8.17.6]</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the possible [[eponym]]s for the city of [[Psophis]]. This can be explained by the following genealogical link; Nyctimus, Periphe
```
Prediction around first diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, 8.17.6</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the possible [[eponym]]s for the city of [[Psophis]]. This can be explained by the following genealogical link; Nyctimus, Periphetes
```

## Case 19: instance `4e1d9249cba07140`, variant `10`

- source line: `48`
- prompt style: `recipe_narrative`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `5829` / `4793` / `4838`
- similarity pred-vs-ref: `0.9870`
- instruction: turn it into cleaner text by deleting embedded URLs and any other link-like web addresses.

Input around first ref/pred diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, [http://www.perseus.tufts.edu/hopper/text?doc=Paus.+8.17.6&fromdoc=Perseus%3Atext%3A1999.01.0160:chapter=&highlight=Nonacris 8.17.6]</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the po
```
Reference around first diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, [ 8.17.6]</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the possible [[eponym]]s for the city of [[Psophis]]. This can be explained by the following genealogical link; Nyctimus, Periphe
```
Prediction around first diff:
```text
mpious King [[Lycaon (king of Arcadia)|Lycaon]]<ref>[[Pausanias (geographer)|Pausanias]], 8.17.6</ref> either by the [[naiad]] [[Cyllene (nymph)|Cyllene]],<ref>[[Dionysius of Halicarnassus]], ''Antiquitates Romanae'' 1.13.1</ref> [[Nonacris (mythology)|Nonacris]],<ref>Pausanias, 8.17.6</ref> or by an unknown woman.

==Family==
Nyctimus was the father of [[Periphetes]], the ancestor of [[Psophis (mythology)|Psophis]], one of the possible [[eponym]]s for the city of [[Psophis]]. This can be explained by the following genealogical link; Nyctimus, Periphetes
```

## Case 20: instance `d1dd8565aac28af7`, variant `0`

- source line: `43`
- prompt style: `analyst_handoff`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `4663` / `4633` / `4609`
- similarity pred-vs-ref: `0.9959`
- instruction: strip out http, https, ftp, www, and other link-like addresses from these text samples

Input around first ref/pred diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$E-mail:birlasc@hd1.vsnl.net.in}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is i
```
Reference around first diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is it independent
of this scale. T
```
Prediction around first diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$E-mail:}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is it independent
of this s
```

## Case 21: instance `d1dd8565aac28af7`, variant `1`

- source line: `43`
- prompt style: `application_context`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `4663` / `4633` / `4609`
- similarity pred-vs-ref: `0.9959`
- instruction: embedded links, including standard URLs and similar web addresses, are removed before the text is used for retrieval.

Input around first ref/pred diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$E-mail:birlasc@hd1.vsnl.net.in}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is i
```
Reference around first diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is it independent
of this scale. T
```
Prediction around first diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$E-mail:}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is it independent
of this s
```

## Case 22: instance `d1dd8565aac28af7`, variant `2`

- source line: `43`
- prompt style: `concise_brief`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `4663` / `4633` / `4608`
- similarity pred-vs-ref: `0.9958`
- instruction: Remove all URLs and web links from the text

Input around first ref/pred diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$E-mail:birlasc@hd1.vsnl.net.in}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is i
```
Reference around first diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is it independent
of this scale. T
```
Prediction around first diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$E-mail:}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is it independent
of this s
```

## Case 23: instance `d1dd8565aac28af7`, variant `3`

- source line: `43`
- prompt style: `conversational_cooperative`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `4663` / `4633` / `4608`
- similarity pred-vs-ref: `0.9958`
- instruction: remove any web links from it, including normal URLs and similar online addresses.

Input around first ref/pred diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$E-mail:birlasc@hd1.vsnl.net.in}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is i
```
Reference around first diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is it independent
of this scale. T
```
Prediction around first diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$E-mail:}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is it independent
of this s
```

## Case 24: instance `d1dd8565aac28af7`, variant `4`

- source line: `43`
- prompt style: `end_weighted_instruction`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `4663` / `4633` / `4608`
- similarity pred-vs-ref: `0.9958`
- instruction: delete any embedded URLs or other recognizable web links so the remaining content is link-free.

Input around first ref/pred diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$E-mail:birlasc@hd1.vsnl.net.in}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is i
```
Reference around first diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is it independent
of this scale. T
```
Prediction around first diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$E-mail:}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is it independent
of this s
```

## Case 25: instance `d1dd8565aac28af7`, variant `5`

- source line: `43`
- prompt style: `goal_oriented`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `4663` / `4633` / `4650`
- similarity pred-vs-ref: `0.9954`
- instruction: the final text should no longer contain http, https, ftp, www-style links, or other web addresses.

Input around first ref/pred diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$E-mail:birlasc@hd1.vsnl.net.in}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is i
```
Reference around first diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is it independent
of this scale. T
```
Prediction around first diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$E-mail:birlasc@hd1.vsnl.net.in}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is i
```

## Case 26: instance `d1dd8565aac28af7`, variant `6`

- source line: `43`
- prompt style: `imperative_checklist`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `4663` / `4633` / `4640`
- similarity pred-vs-ref: `0.9943`
- instruction: remove all web links and URLs from the text, including http, https, ftp, and similar address-style links.

Input around first ref/pred diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$E-mail:birlasc@hd1.vsnl.net.in}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is i
```
Reference around first diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is it independent
of this scale. T
```
Prediction around first diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$E-mail:birlasc@hd1.vsnl.net.in}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is i
```

## Case 27: instance `d1dd8565aac28af7`, variant `8`

- source line: `43`
- prompt style: `policy_like`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `4663` / `4633` / `4631`
- similarity pred-vs-ref: `0.9933`
- instruction: the usable version of the text must not retain URLs, embedded links, or other recognizable web addresses.

Input around first ref/pred diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$E-mail:birlasc@hd1.vsnl.net.in}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is i
```
Reference around first diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is it independent
of this scale. T
```
Prediction around first diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$E-mail:birlasc@hd1.vsnl.net.in}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is i
```

## Case 28: instance `d1dd8565aac28af7`, variant `9`

- source line: `43`
- prompt style: `qa_request`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `4663` / `4633` / `4609`
- similarity pred-vs-ref: `0.9959`
- instruction: strip out any URL-like content from this text and consider it usable only after those web links have been removed.

Input around first ref/pred diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$E-mail:birlasc@hd1.vsnl.net.in}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is i
```
Reference around first diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is it independent
of this scale. T
```
Prediction around first diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$E-mail:}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is it independent
of this s
```

## Case 29: instance `d1dd8565aac28af7`, variant `10`

- source line: `43`
- prompt style: `recipe_narrative`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `4663` / `4633` / `4608`
- similarity pred-vs-ref: `0.9958`
- instruction: turn it into cleaner text by deleting embedded URLs and any other link-like web addresses.

Input around first ref/pred diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$E-mail:birlasc@hd1.vsnl.net.in}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is i
```
Reference around first diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is it independent
of this scale. T
```
Prediction around first diff:
```text
\documentstyle[12pt]{article}
\begin{document}
\title{SCALE DEPENDENT DIMENSIONALITY}
\author{B.G. Sidharth$^*$\\
B.M. Birla Science Centre, Hyderabad 500 063 (India)}
\date{}
\maketitle
\footnotetext{$^*$E-mail:}
\begin{abstract}
We argue that dimensionality is not absolute, but that it depends on the
scale of resolution, from the Planck to the macro scale.
\end{abstract}
\section{Introduction}
Is dimensionality dependent on the scale of resolution, or is it independent
of this s
```

## Case 30: instance `f882fe822969b6c9`, variant `0`

- source line: `45`
- prompt style: `analyst_handoff`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `4820` / `4259` / `4351`
- similarity pred-vs-ref: `0.9893`
- instruction: strip out http, https, ftp, www, and other link-like addresses from these text samples

Input around first ref/pred diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[Image:SimpleText.png|SimpleText icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [
```
Reference around first diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[ icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [[System 7]] – [[Mac OS 9]]
| ge
```
Prediction around first diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[Image:SimpleText.png|SimpleText icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [
```

## Case 31: instance `f882fe822969b6c9`, variant `1`

- source line: `45`
- prompt style: `application_context`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `4820` / `4259` / `4321`
- similarity pred-vs-ref: `0.9862`
- instruction: embedded links, including standard URLs and similar web addresses, are removed before the text is used for retrieval.

Input around first ref/pred diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[Image:SimpleText.png|SimpleText icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [
```
Reference around first diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[ icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [[System 7]] – [[Mac OS 9]]
| ge
```
Prediction around first diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[Image:SimpleText.png|SimpleText icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [
```

## Case 32: instance `f882fe822969b6c9`, variant `2`

- source line: `45`
- prompt style: `concise_brief`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `4820` / `4259` / `4321`
- similarity pred-vs-ref: `0.9862`
- instruction: Remove all URLs and web links from the text

Input around first ref/pred diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[Image:SimpleText.png|SimpleText icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [
```
Reference around first diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[ icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [[System 7]] – [[Mac OS 9]]
| ge
```
Prediction around first diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[Image:SimpleText.png|SimpleText icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [
```

## Case 33: instance `f882fe822969b6c9`, variant `3`

- source line: `45`
- prompt style: `conversational_cooperative`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `4820` / `4259` / `4321`
- similarity pred-vs-ref: `0.9862`
- instruction: remove any web links from it, including normal URLs and similar online addresses.

Input around first ref/pred diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[Image:SimpleText.png|SimpleText icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [
```
Reference around first diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[ icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [[System 7]] – [[Mac OS 9]]
| ge
```
Prediction around first diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[Image:SimpleText.png|SimpleText icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [
```

## Case 34: instance `f882fe822969b6c9`, variant `4`

- source line: `45`
- prompt style: `end_weighted_instruction`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `4820` / `4259` / `4321`
- similarity pred-vs-ref: `0.9862`
- instruction: delete any embedded URLs or other recognizable web links so the remaining content is link-free.

Input around first ref/pred diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[Image:SimpleText.png|SimpleText icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [
```
Reference around first diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[ icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [[System 7]] – [[Mac OS 9]]
| ge
```
Prediction around first diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[Image:SimpleText.png|SimpleText icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [
```

## Case 35: instance `f882fe822969b6c9`, variant `5`

- source line: `45`
- prompt style: `goal_oriented`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `4820` / `4259` / `4351`
- similarity pred-vs-ref: `0.9893`
- instruction: the final text should no longer contain http, https, ftp, www-style links, or other web addresses.

Input around first ref/pred diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[Image:SimpleText.png|SimpleText icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [
```
Reference around first diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[ icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [[System 7]] – [[Mac OS 9]]
| ge
```
Prediction around first diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[Image:SimpleText.png|SimpleText icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [
```

## Case 36: instance `f882fe822969b6c9`, variant `6`

- source line: `45`
- prompt style: `imperative_checklist`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `4820` / `4259` / `4351`
- similarity pred-vs-ref: `0.9893`
- instruction: remove all web links and URLs from the text, including http, https, ftp, and similar address-style links.

Input around first ref/pred diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[Image:SimpleText.png|SimpleText icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [
```
Reference around first diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[ icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [[System 7]] – [[Mac OS 9]]
| ge
```
Prediction around first diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[Image:SimpleText.png|SimpleText icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [
```

## Case 37: instance `f882fe822969b6c9`, variant `7`

- source line: `45`
- prompt style: `negative_constraint_driven`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `4820` / `4259` / `4353`
- similarity pred-vs-ref: `0.9891`
- instruction: embedded web addresses or link-like URL text; also clean the text by deleting all such links.

Input around first ref/pred diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[Image:SimpleText.png|SimpleText icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [
```
Reference around first diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[ icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [[System 7]] – [[Mac OS 9]]
| ge
```
Prediction around first diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[Image:SimpleText.png|SimpleText icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [
```

## Case 38: instance `f882fe822969b6c9`, variant `8`

- source line: `45`
- prompt style: `policy_like`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `4820` / `4259` / `4321`
- similarity pred-vs-ref: `0.9862`
- instruction: the usable version of the text must not retain URLs, embedded links, or other recognizable web addresses.

Input around first ref/pred diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[Image:SimpleText.png|SimpleText icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [
```
Reference around first diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[ icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [[System 7]] – [[Mac OS 9]]
| ge
```
Prediction around first diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[Image:SimpleText.png|SimpleText icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [
```

## Case 39: instance `f882fe822969b6c9`, variant `9`

- source line: `45`
- prompt style: `qa_request`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `4820` / `4259` / `4353`
- similarity pred-vs-ref: `0.9891`
- instruction: strip out any URL-like content from this text and consider it usable only after those web links have been removed.

Input around first ref/pred diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[Image:SimpleText.png|SimpleText icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [
```
Reference around first diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[ icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [[System 7]] – [[Mac OS 9]]
| ge
```
Prediction around first diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[Image:SimpleText.png|SimpleText icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [
```

## Case 40: instance `f882fe822969b6c9`, variant `10`

- source line: `45`
- prompt style: `recipe_narrative`
- status ref/pred: `KEEP` / `KEEP`
- lengths input/ref/pred: `4820` / `4259` / `4321`
- similarity pred-vs-ref: `0.9862`
- instruction: turn it into cleaner text by deleting embedded URLs and any other link-like web addresses.

Input around first ref/pred diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[Image:SimpleText.png|SimpleText icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [
```
Reference around first diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[ icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [[System 7]] – [[Mac OS 9]]
| ge
```
Prediction around first diff:
```text
{{Short description|Native text editor for the Apple classic Mac OS}}
{{Infobox software
| name = SimpleText
| logo = <!-- Commented out because image was deleted: [[Image:SimpleText.png|SimpleText icon]] -->
| screenshot = German SimpleText.png
| screenshot size = 250px
| caption = SimpleText under the German version of [[Mac OS 8]]
| developer = [[Apple Computer]]
| latest_release_version = 1.4
| latest_release_date =
| operating_system = [
```
