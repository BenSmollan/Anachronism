# data/rome/city: dataset for the 3D city of Rome (phase R5)

Not loaded by the game yet. Covers the city between 509 and 27 BC (a few Augustan items
begun in range but finished slightly later are kept, flagged in their `built` text).

## Files
- `monuments.yaml`: top-level key `monuments`, a list of structures.
- `population.yaml`: census figures, grain dole, city-population estimates, built-up area.
- `topography.yaml`: hills, valleys, Tiber, Campus Martius.

## Monument fields
| field | meaning |
|---|---|
| `id` | unique snake_case id |
| `latin`, `english` | names |
| `type` | temple, basilica, forum, portico, aqueduct, bridge, wall, gate, theatre, circus, curia, comitium, rostra, horrea, market, arch, road, sewer, house, tomb, ... |
| `regio` | later Augustan regio number (1-14); `0` means outside the regions (walls, aqueducts, roads) |
| `lat`, `lon` | WGS84 degrees, representative point |
| `precision` | `exact` (identified remains, a few metres), `approx` (100-300 m), `rough` (site only known by area, 300 m or worse) |
| `location` | plain-text place description |
| `built` | `{year, certainty, by}`: negative year = BC; `null` if unknown; certainty is `certain`, `probable`, `traditional` (legend or late tradition) or `uncertain`; `by` names the builder and office and the source of the claim |
| `events` | list of `{year, what}`: rebuilds, fires, destructions |
| `ended` | `{year, what}` if it went out of use before 27 BC |
| `form`, `materials` | size and shape; building materials (tufa, travertine, concrete, marble) |
| `route` | `[[lat, lon], ...]` point list for linear features (aqueducts, sewer, wall, roads) |
| `sources` | ancient authors and `Platner-Ashby s.v. ...` entries |
| `pleiades` | Pleiades id where known, else `null` (not yet cross-checked; Pleiades data is CC BY) |
| `notes` | doubts and disagreements |

## Method and caveats
- Primary source: Platner and Ashby, *A Topographical Dictionary of Ancient Rome* (1929, public domain; LacusCurtius). Dates come from Livy, Dionysius, Frontinus, Plutarch, Dio, Suetonius and Cicero as cited on each entry. Text is paraphrased.
- **Coordinates are estimates**, placed from the identified standing or excavated remains where these exist (Forum, Largo Argentina, Theatre of Marcellus, bridges, Circus Maximus) and from Platner-Ashby / Lanciani's *Forma Urbis Romae* descriptions elsewhere. The Servian gates, many Capitoline and Quirinal temples, Navalia, the houses and the aqueduct source points are `rough`. Pleiades coordinates have NOT been cross-checked yet (only Roma = 423025 was confirmed online); do that pass before the 3D build.
- Citations were written from knowledge of the sources and many individual passage numbers have not been re-read on LacusCurtius. Treat passage numbers marked or doubtful as to be verified. Entries with `certainty: uncertain` or `precision: rough` need review.
- Heights and floor levels in topography are approximate modern values; the ancient valley floors were lower than today.
