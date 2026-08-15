# Everyone Is Throwing the Same Pitch

**Six seasons and 3.1 million pitches say the league is converging — and that the pitchers who refuse to are getting paid for it.**

BY CARLOS MARCANO · DRAFT

There's a moment in every pitching lab conversation where somebody pulls up a movement plot, points at a cluster of dots, and says some version of: *this is what a good slider looks like now.* And they're right — the target is real, it's measurable, and pitchers who hit it get better. But I've spent a few years watching those clusters get tighter, and a question started nagging at me. If everybody knows what a good slider looks like, and everybody can measure whether they've built one, what happens when everybody builds it?

So I pulled every regular-season pitch from 2021 through 2026 — 3.1 million of them — with one rule set up front: because 2026 is only two-thirds played, every season gets cut off at August 13. Otherwise I'd be comparing a partial season to five complete ones and calling the calendar a discovery. Matched that way the six seasons land within 40,000 pitches of each other.

What came back is not the simple story I expected, and the part that surprised me most had nothing to do with the pitchers already in the league.

## The drift is real, and it's every single year

Start with the most direct question: are individual pitchers moving toward the league-average version of their own pitch? For every pitcher appearing in back-to-back seasons, I found where his slider (or fastball, or changeup) sat in movement-and-velocity space, then measured which direction it moved the next year. Toward the league center, or away?

There's a trap here worth one paragraph, because it's what separates a fake finding from a real one. Measurement noise alone produces apparent convergence — a guy who posted a fluky-high spin reading in April will "regress" toward average next year without changing a thing. So I measured his starting position on one half of his pitches and his movement on the other half. Independent noise in each half, and the artifact cancels. Then I built a null: run the identical calculation *within* a single season, where no real development can have happened, and see what the machinery spits out.

![Every season, about two-thirds of pitchers move toward the middle](figures/art01_convergence.png)

The null lands at 50-57%, right about where a coin flip should. The real number is 61 to 69 percent, five seasons out of five, and 2026 is the highest of the bunch. Roughly two out of every three pitchers in this league are drifting toward the middle of their own pitch type, and the drift is not slowing down.

## The part that stopped me: the rookies are already there

Here's where I had to check my assumptions.

If everyone in the league is converging but the league-wide spread isn't collapsing as fast, something has to be refilling the edges. The obvious candidate is turnover: rookies show up with weird arm slots and unpolished deliveries, spend three years getting sanded down, and by 27 they look like everybody else. That's the story I'd have told you before I ran this.

It's backwards. Pitchers in their **debut season sit closer to the center of their pitch type than the veterans do** — about 5% closer, consistently enough across family-seasons that the paired test comes back at p = 0.0012. The new arrivals are *more* league-standard, not less.

Sit with that one. The development pipeline isn't grinding the strange out of pitchers after they arrive. It's delivering them pre-conformed. By the time a guy throws his first big-league pitch, some combination of college programs, draft models, and player-development departments has already pointed his slider at the same coordinates as everyone else's.

One thing cuts against the headline, and I want to be careful with it: **arsenals are getting broader, not narrower.** Pitchers throw more distinct types, more evenly — 3.08 pitches at a meaningful clip in 2021, 3.56 in 2026, with the share of a guy's top pitch falling from 49% to 41%. So "homogenization" is the wrong word at the arsenal level. Variety *within* a pitcher is up; it's each individual pitch converging on a template. Only the second one is the problem.

## The sweeper paid the bill

If pitches converge, what does it cost? This is the part I find genuinely fun, because the league already ran the experiment for us and the receipt is sitting right there in the sweeper.

![The sweeper got popular and got worse. The changeup did the reverse.](figures/art02_usage_value.png)

Look at the left panel and follow the years. The sweeper's run value relative to league average has gone down **every single season for six straight years** — +0.334, +0.265, +0.184, +0.162, +0.035, and now −0.014 — while its usage climbed from 19.4% of all pitches to 22.2%. In 2026, for the first time in this window, the sweeper is a below-average pitch by run value.

And then usage finally turned down. The sweeper's share dropped 0.6 points this year, the first decline of the boom, arriving in the exact season its value hit zero. The market took six years to price it, but it priced it.

This isn't just one pitch type. I tested it at a finer grain, chopping each family's movement space into small cells — two miles per hour by four inches of vertical break by four of horizontal — and asking whether *the same cell* performs worse in seasons when more pitchers live in it. Comparing a cell to itself across years, holding the shape constant: **when a shape gets crowded, hitters square it up harder.** Doubling a shape's usage costs about 6 points of expected wOBA on contact.

## Why it works: hitters just need reps

The mechanism turns out to be almost boringly human, which is why I believe it. For every pitch, I counted how many of that same shape the hitter had faced in the previous 30 days, then compared each hitter against *himself* — his well-prepared at-bats versus his unprepared ones — holding count, location, and the pitch's own quality fixed.

![A pitch works worse once the hitter has seen it lately](figures/art04_familiarity.png)

Doubling a hitter's recent exposure to a shape costs the pitcher about 0.46 percentage points of whiff rate, and the estimate barely moves at a 15-, 30-, or 60-day window. Here's the kicker: **the penalty is bigger for unusual pitches than ordinary ones.** A generic 94-mph four-seamer has no novelty to lose. A weird one does, and it bleeds that edge as hitters bank looks.

That's the engine. As a shape spreads, every hitter's recent exposure to it rises and the shape stops paying. Crowding and familiarity are one phenomenon measured from two directions.

## So being weird is worth something

If familiarity is a tax, scarcity should be a subsidy. It is.

![The stranger the pitch, the more bats it misses](figures/art03_uniqueness.png)

Sort every pitcher-season by how far its shape sits from the league norm and the whiff rate climbs steadily from the most ordinary tenth to the strangest: 23.2% up to 24.4%.

The obvious objection — and it's a good one — is selection. Maybe good pitchers just happen to throw weird pitches, and I'm measuring talent with extra steps. So I split it: how much comes from comparing *different pitchers*, versus following *the same pitcher* as his own pitch drifts from the norm?

The two numbers come out at +1.78 and +1.43 points of whiff rate. Nearly identical. When a given pitcher's slider gets weirder, it misses more bats — and that can't be talent, because the pitcher is held fixed by construction.

One honest caveat, because it constrains what you do with this. I also fed the whole thing to a model predicting whiffs from velocity, movement, location and count, then added my "uniqueness" score on top. It added nothing. Zero — which makes sense, since uniqueness is calculated *from* those same features, so the model already had the information. The lesson isn't "be weird." It's **occupy a shape hitters aren't currently seeing**, and what makes that valuable is scarcity, not strangeness.

## The changeup already figured this out

Which brings me to my favorite thing in this dataset. Go back to that second chart, right panel. The changeup was the most-abandoned offspeed pitch in the study: usage falling four straight years to a six-season low of 10.15%, second-worst relative run value of any family in 2025, and actively cannibalized by the splitter boom — pitchers who picked up a splitter cut their changeup usage 3 to 6 points in the adoption year.

Then 2026 happened, and the changeup posted its best season on every measure at once. Usage up to 11.21%, the largest gain of any family. Whiff rate 29.8%, best of the six years. Expected wOBA on contact at .277, best of the six years. And a run value of +0.025 — the **first positive mark in six seasons**.

A pitch got abandoned into scarcity, became effective again because nobody was throwing it, and pitchers noticed within a single season. That's the whole thesis of this article, delivered by the league, unprompted, while I was still writing it.

It also explains something I'd found earlier and couldn't place. When I ranked the most unusual pitches thrown from *conventional* arm slots — filtering out submariners, whose weirdness is the delivery and isn't transferable advice — the list came back almost entirely changeups. Devin Williams' Airbender. Logan Webb's. Pedro Avila's. Trevor Richards'. The changeup resisted standardization because it was never a spin-and-shape pitch to begin with: it lives off velocity separation and tunneling, and you can't template that the way you template a sweeper.

## One that didn't cooperate

I'd be doing the thing I complain about if I only showed you the parts that fit.

The "deathball" — the hard gyro slider with almost no horizontal break and a few inches of drop, the one Roki Sasaki and Ryne Nelson made famous — should be following the sweeper's arc. It's getting adopted fast: 168 pitchers throwing it in 2026, up from 159 last year, and its share of all slider-type pitches jumped from 1.5% to 2.2% this year alone.

Its edge over ordinary sliders has not eroded. It's bounced between +4 and +8 percentage points of whiff rate for four years with no trend I can defend. I had read that series as "peaked in 2023, declining since," and the 2026 number blew it up — three noisy points is not a trend, and I over-fitted it. Maybe the deathball is still scarce enough that crowding hasn't bitten. Maybe gyro spin is harder to standardize than sweep. I don't know yet, and this data can't tell me.

## What I'd actually do with this

If you run a pitching department, the actionable version is short. The outlier advantage shows up in *every* count state — significant in all four — yet outlier pitches get thrown barely a percentage point more often with two strikes than when behind. Nobody is deploying this on purpose.

And the target should not be "weird." It should be "scarce." Those sound alike and aren't. There are movement cells in the sinker and cutter families that lost half their occupancy since 2021 while still beating league average — real estate the league walked away from that still pays rent.

The deeper point is that pitch design has a self-limiting mechanism baked in, and I don't think the industry has priced it. Every model telling you what a good slider looks like was trained on a league where that slider was rarer than it will be once everyone reads the model. The edge lives in the gap between when you find a shape and when everybody else does.

So I'll end where I like to, with the questions. How much of the sweeper's collapse was inevitable the moment it became teachable? Should a pitch-design department be optimizing for stuff, or for stuff *net of how many other guys throw it*? And if the changeup could come back from six years of neglect in one season, what else is sitting in the discard pile right now?

I don't have those figured out. But I'm a lot less impressed by a movement plot that lands right in the middle of the cluster than I was six months ago.

*Data: Baseball Savant, 2021–2026 regular seasons, all seasons truncated at August 13 for comparability. Further reading: Driveline Baseball's work on pitch design and arsenal construction, Eno Sarris on Stuff+, and Baseball Prospectus on times-through-order familiarity effects.*
