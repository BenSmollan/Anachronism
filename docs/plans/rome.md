# Rome: narrower and deeper (D-286)

The game becomes one campaign: **you are Rome, from the founding of the Republic (509 BC) to
Augustus (27 BC)**. Everything that is not Rome or its world is removed (archived on the branch
`claude/archive-multi-civ`). The core idea stays: you feed Rome ideas ahead of their time, the
AI interprets and narrates, a deterministic engine decides. What changes is the scale: one state, one
city, one Mediterranean, with a thousand times the historical detail.

## What "deeper" means (the design targets)

1. **Rome governs itself as Rome did.** The game must not reduce Rome to one ruler.
   - Each turn is a **consular year**. Two consuls are elected and named; there are censors,
     praetors, tribunes, and a dictator in emergencies.
   - The **Senate** decides, through the families and later the factions that fill it
     (patricians and plebeians; then optimates and populares).
   - You act as the guiding mind behind them. You never act as an absolute king.
   - The **Struggle of the Orders** (494–287 BC) and the **cursus honorum** shape who can do what.
2. **Real people.**
   - Every year's real consuls come from the *Fasti*. For example: 264 BC, Ap. Claudius Caudex and M. Fulvius Flaccus.
   - The great families are modelled, with members who age, hold office, marry, feud and die: Cornelii, Fabii, Claudii, Aemilii, Sempronii, Caecilii, Julii.
   - Famous figures arrive on cue, unless your changes alter history: Camillus, Appius Claudius Caecus, Scipio Africanus, Cato, the Gracchi, Marius, Sulla, Pompey, Caesar, Cicero, Octavian.
3. **Rome's real world, at province grain.**
   - **Italy** is mapped at the scale of its peoples: Latins, Etruscans, Volsci, Aequi, Sabines, Samnites, Umbrians, Gauls, and the Greek cities of Magna Graecia.
   - **Abroad:** Carthage, Syracuse, Epirus, Macedon, the Seleucids, the Ptolemies, Numidia, Pontus and Parthia, met in the order Rome met them.
   - Rome's way of expanding is modelled. **Allies** (*socii*) and **Latin rights** come first; **citizenship** and **colonies** follow. **Provinces** come later, with governors who can enrich themselves, misgovern and be prosecuted.
4. **The army as it really changed.**
   - The army moves through three systems: the phalanx; then the manipular legion (hastati, principes, triarii); then the Marian cohort legion.
   - Recruitment runs through the census classes. Soldiers serve as farmers, then as professionals, and their loyalty shifts to the general.
   - Battles stay tactical (D-108). The order of battle is drawn from real engagements: Cannae, Zama, Cynoscephalae, Pydna, Alesia, Pharsalus.
5. **Economy and society.**
   - *Ager publicus*, latifundia and slavery.
   - The grain supply and, later, the grain dole.
   - Coinage, including the denarius (c. 211 BC), and tribute from the provinces.
   - Debt and land reform: the Gracchi.
6. **Religion and state.**
   - Pontifices, augurs, auspices before battle, the Sibylline Books, and new cults (Aesculapius 291 BC, Magna Mater 204 BC).
   - Prodigies and expiations are modelled, because the Romans acted on them.
7. **The city of Rome as a living model that grows year by year** (see below).
8. **Ideas ahead of their time measured against what Rome actually knew.**
   - Every anachronism is weighed against the Roman technology and institutions of its year: concrete (*opus caementicium*, c. 200 BC), the arch, aqueducts, roads, surveying, the codex, Greek mechanics.
   - What it changes is told through Roman eyes and Roman politics.

## The city of Rome

Rome Reborn is commercial (Flyover Zone holds an exclusive licence), so it cannot go into the
game. We build our own model, **using Rome Reborn only as a visual reference**, from sources we
are allowed to use. Each licence is checked and logged before any data is used.

- **Topography.**
  - The Tiber, the seven hills, the Campus Martius and the marshes of the early Forum, built from public elevation data (SRTM, public domain).
  - Ancient ground levels are adjusted by hand from the archaeology.
- **Monuments, dated.** Each building enters the game in the year it was built, is rebuilt after its fires, and stands where it stood. The main sources:
  - **Platner and Ashby, *A Topographical Dictionary of Ancient Rome* (1929).** It is now in the public domain, and its text is on LacusCurtius. It gives every known building, its date and its history.
  - **Lanciani, *Forma Urbis Romae* (1893–1901).** Public domain; the plans of the city.
  - **Pleiades** gazetteer (openly licensed: attribution) for places.
  - **DARE** (Digital Atlas of the Roman Empire) for roads and sites. Its licence is reported both as CC BY and as CC BY-SA, and is checked before use.
- **What it covers.** Each item enters at its date:
  - the **Servian Wall** (378 BC);
  - the **Cloaca Maxima**;
  - the aqueducts: **Aqua Appia** 312 BC, **Anio Vetus** 272 BC, **Marcia** 144 BC;
  - the **Via Appia** (312 BC) and the bridges: **Pons Aemilius** 179 BC, **Fabricius** 62 BC;
  - the temples of the Capitol, the Forum, the Circus Flaminius and the Largo Argentina;
  - the **basilicas**: Porcia 184 BC, Aemilia, Sempronia, Opimia;
  - the **Theatre of Pompey** (55 BC) and the **Forum of Caesar**;
  - the insulae and domus that fill the city as it grows, from about 30,000 people to about 1,000,000.
- **How it is built.**
  - The model kit of D-280 is extended with Roman forms, each checked against excavated plans: temple orders, basilicas, porticoes, insulae, domus, horrea, aqueduct arcades and walls.
  - Districts are laid out by the planner of D-281, on the real street grid where it is known.
- **What the player sees.** The capital view becomes a visit to the city: its monuments named, dated and explained. Your ideas also show up here, for example concrete domes before their time, or an aqueduct a century early.

## Accuracy rules (how a thousandfold detail stays true)

- **Every historical fact carries its source.** Each fact in the content files names where it comes from, for example "Livy 9.29" or "Polybius 1.20". The content linter rejects a fact with no source.
- **Public-domain ancient sources first.**
  - The ancient authors: Livy, Polybius, Plutarch, Appian, Dionysius, Cassius Dio, Sallust, Caesar, Cicero. Their translations are on LacusCurtius and in the public domain.
  - The *Fasti Capitolini*.
  - Modern reference is used only for checking, never copied. Broughton's *Magistrates of the Roman Republic* is still in copyright.
- **Disputed facts are marked as disputed,** and the game says so. Early Roman history before about 300 BC is half legend, and the game is honest about it.
- **The chronicle notes keep the existing "in our history" form,** now from Roman sources.

## Phases (each ends at a gate for the owner)

- **R0 — Plan and archive.** This document, the archive branch and the decision log. *Gate: owner approves this plan.*
- **R1 — Narrow the game.**
  - Remove the other packs, chronicles, scenarios and client styles. The tests stay green.
  - Keep one Mediterranean map, re-cut finer for Italy.
  - Make Rome the only playable state, and set start points along the Republic: 509, 390, 264, 133 and 49 BC.
  - *Gate: the game runs as Rome-only.*
- **R2 — The Roman state.**
  - Magistracies and the yearly election.
  - The Senate, families and factions, the orders, and the cursus honorum.
  - The real *Fasti* consuls as the default history; your changes let others win.
  - The engine stays deterministic and every rule is tested.
  - *Gate: one played-through decade reads right to the owner.*
- **R3 — Italy and the world.**
  - The peoples of Italy, the alliance system, citizenship and colonies.
  - The overseas powers and their real scripts, from the Punic Wars to Actium.
  - Provinces and governors.
- **R4 — Army, economy, religion.**
  - The legion's three eras and recruitment by class.
  - Land, grain, slaves and coinage.
  - Priesthoods, auspices and prodigies.
- **R5 — The city of Rome.**
  - Topography, then the dated monuments (several hundred).
  - Roman model-kit forms and districts.
  - The city visit.
- **R6 — Depth pass.**
  - Every year from 509 to 27 BC checked against the sources, every person and every chronicle line.
  - Then balance, and a full campaign played through.

Agents are used sparingly: three or four at a time on separate files, never ten. That keeps
within usage limits.
