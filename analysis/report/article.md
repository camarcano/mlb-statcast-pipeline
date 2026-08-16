# Everyone Is Building the Same Slider

**Six seasons. 3.1 million pitches. A league that keeps teaching itself the same shapes, and the pitchers who profit by ignoring it.**

BY CARLOS MARCANO · DRAFT

Two out of every three big-league pitchers move their best pitch toward the league average every year. I measured it across five consecutive pairs of seasons. It happened all five times, and 2026 is the strongest one yet.

That's the short version. The longer version has a twist I didn't see coming, and it involves rookies.

I pulled every regular-season pitch from 2021 through 2026, 3.1 million of them. The 2026 season is only two-thirds played, so I cut every season off at August 13. Without that cut I'd be comparing a partial season against five full ones and calling the calendar a finding. Matched this way, the six seasons stay within 40,000 pitches of each other.

## The drift

For each pitcher who appears in back-to-back seasons, I located his slider (or fastball, or changeup) in movement-and-velocity space. Then I checked which way it moved the next year. Toward the league center, or away from it.

One trap ruins this measurement. Random noise creates fake convergence. A pitcher who posts a lucky-high spin reading in April drifts back toward average next season without changing a thing. So I measured his starting position from one half of his pitches and his movement from the other half. The two halves carry independent noise, so the artifact cancels.

Then I built a control. I ran the same calculation inside a single season, where no real development can have happened, and looked at what came out.

![Every season, about two-thirds of pitchers move toward the middle](figures/art01_convergence.png)

The control sits between 50 and 57 percent, about where a coin flip belongs. The real number runs from 61 to 69 percent. Five seasons out of five.

## The rookies are already there

I expected turnover to refill the edges. Rookies arrive with strange arm slots, get sanded down over three years, and look like everybody else by 27. That was my assumption going in.

It's wrong. Pitchers in their debut season sit about 5 percent closer to the center of their pitch type than established pitchers do. The paired test returns p = 0.0012.

Nobody is grinding the strange out of these arms after they arrive. The strange is gone before they get here. College programs, draft models, and player development departments have already aimed the slider at the same coordinates.

One number cuts against all of this, and I want it on the table. Arsenals are getting wider, not narrower. Pitchers threw 3.08 distinct pitches at a meaningful rate in 2021 and 3.56 in 2026. The share of a pitcher's most-used pitch fell from 49 to 41 percent. Each individual pitch converges while the collection around it expands. Only the first half of that is a problem.

## What convergence costs

The sweeper shows the bill.

![The sweeper got popular and got worse. The changeup did the reverse.](figures/art02_usage_value.png)

Follow the years in the left panel. Sweeper run value against league average fell every season for six straight years: +0.334, +0.265, +0.184, +0.162, +0.035, and now −0.014. Usage climbed from 19.4 percent of all pitches to 22.2 percent across the same stretch. The sweeper is now a below-average pitch by run value for the first time in this window.

Then usage turned down. Sweeper share dropped 0.6 points in 2026, the first decline of the boom, in the same season its value crossed zero. The market took six years to price the pitch. It priced it.

One pitch type proves nothing, so I tested the idea at a finer grain. I cut each family's movement space into small cells: two miles per hour by four inches of vertical break by four inches of horizontal break. Then I asked whether the same cell performs worse in seasons when more pitchers occupy it. Cell and year effects absorb the obvious objections.

The answer is yes. When a shape gets crowded, hitters hit it harder. Doubling a shape's usage costs about 6 points of expected wOBA on contact.

## Hitters just need reps

The mechanism is ordinary, which is why I trust it.

For every pitch, I counted how many pitches of that same shape the hitter had faced in the previous 30 days. Then I compared each hitter against himself, his well-prepared at-bats against his unprepared ones, holding count, location, and pitch quality fixed.

![A pitch works worse once the hitter has seen it lately](figures/art04_familiarity.png)

Doubling a hitter's recent exposure costs the pitcher 0.46 percentage points of whiff rate. The estimate barely moves at a 15-day, 30-day, or 60-day window.

The interaction matters more than the main effect. Strange pitches lose more to exposure than ordinary ones do. A generic 94-mph four-seamer has no novelty to spend. A strange pitch does, and it spends it as hitters bank looks.

Crowding and familiarity are one thing measured from opposite ends. A shape spreads, every hitter's recent exposure to it rises, the shape stops paying.

## Strange pitches pay

![The stranger the pitch, the more bats it misses](figures/art03_uniqueness.png)

Sort every pitcher-season by how far its shape sits from the league norm. Whiff rate climbs from 23.2 percent in the most ordinary tenth to 24.4 percent in the strangest.

Selection is the obvious objection. Maybe good pitchers throw weird pitches and I'm measuring talent by a longer route. So I separated the two. One estimate compares different pitchers against each other. The other follows the same pitcher as his own pitch drifts from the norm across seasons.

They come out at +1.78 and +1.43 points of whiff rate. When a pitcher's own slider gets stranger, it misses more bats. Talent can't explain that, because the pitcher stays fixed.

Now the caveat, because it changes what you do with this. I gave a machine-learning model velocity, movement, location, and count, and asked it to predict whiffs. Then I added my uniqueness score on top. It added nothing. Zero improvement.

That makes sense once you see it. Uniqueness gets calculated from those same shape features, so the model already held the information. What pays is scarcity. Occupy a shape hitters aren't seeing right now, and the strangeness takes care of itself.

## The changeup already knew

The changeup was the most abandoned offspeed pitch in this study. Usage fell four straight years to a six-season low of 10.15 percent. It carried the second-worst relative run value of any family in 2025. Splitter adopters cannibalized it, cutting their own changeup usage by 3 to 6 points in the year they picked the splitter up.

Then 2026 arrived and the changeup posted its best season on every measure at once. Usage 11.21 percent, the largest gain of any family. Whiff rate 29.8 percent, best of the six years. Expected wOBA on contact .277, best of the six years. Run value +0.025, the first positive mark in six seasons.

A pitch got abandoned into scarcity, turned effective again because almost nobody threw it, and pitchers noticed inside a single season.

This also explains something I'd found and couldn't place. I ranked the strangest pitches thrown from conventional arm slots. Submariners came out of that list first. Their strangeness lives in the delivery, and you can't hand a delivery to another pitcher. The list came back almost entirely changeups. Devin Williams' Airbender. Logan Webb's. Pedro Avila's. Trevor Richards'. The changeup resisted standardization because it was never a spin-and-shape pitch. It runs on velocity separation and tunneling, and no model templates that the way it templates a sweeper.

## The one I got wrong

The deathball should be following the sweeper's path. It's the hard gyro slider with almost no horizontal break and a few inches of drop, the pitch Roki Sasaki and Ryne Nelson made famous. Adoption is climbing fast. 168 pitchers threw it in 2026, up from 159 last year, and its share of slider-type pitches went from 1.5 to 2.2 percent this season.

Its edge over ordinary sliders hasn't eroded. It's bounced between +4 and +8 percentage points of whiff rate for four years with no trend I can defend. I read that series earlier as a peak in 2023 followed by decline. The 2026 number killed that reading. Three noisy points aren't a trend, and I fit a line to them anyway.

Maybe gyro spin resists standardization the way the changeup does. Maybe the pitch stays scarce enough that crowding hasn't reached it. I don't know yet.

## What to do with this

The outlier advantage shows up in every count state. I checked all four and it holds in each. Yet outlier pitches get thrown about one percentage point more often with two strikes than when the pitcher is behind. That gap should be far wider. Nobody is deploying these on purpose.

Aim for scarce, not strange. Those two sound alike and aren't. Sinker and cutter movement cells exist that lost half their occupancy since 2021 and still beat league average. The league walked away from that real estate and it still pays rent.

Pitch design carries a self-limiting mechanism, and I don't think the industry prices it. Every model that tells you what a good slider looks like got trained on a league where that slider was rare. It gets less rare the moment everybody reads the model. The edge lives in the gap between finding a shape and everybody else finding it.

So: how much of the sweeper's collapse was fixed the moment the pitch became teachable? Should a pitching department optimize for stuff, or for stuff divided by the number of other arms throwing it? And if the changeup can come back from six years of neglect in one season, what else is sitting in the discard pile?

*Data: Baseball Savant, 2021-2026 regular seasons, every season truncated at August 13 for comparability. Further reading: Driveline Baseball on pitch design, Eno Sarris on Stuff+, and Baseball Prospectus on times-through-order familiarity.*
