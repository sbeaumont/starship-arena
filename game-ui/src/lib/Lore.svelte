<script>
  let { onLeave } = $props();
</script>

<div class="screen">
  <header>
    <button type="button" class="back" onclick={onLeave}>‹ back</button>
    <h1>Lore</h1>
  </header>

  <article>
    <p class="lede">
      Millenia in the future, war has followed humanity into the skies. Now, instead of fighting
      for land and power, humanity fights with other powerful races across the galaxy for
      ownership of entire planets. Some of these races fight for dominance and prestige, others
      fight for their very survival, but one thing is for sure: nobody will ever submit. The
      races of Starship Arena are battling over one thing: planets rich in oxygen and liquid
      water, with survivable conditions to allow them to continue to grow and prosper in this
      brutal universe. They will do whatever it takes to gain control of planets for their
      species. Survival is not an option. Peace is not an option.
    </p>

    <h2>Amphibian</h2>
    <p>
      The Anuran Alliance of amphibious races is permanently searching for wet, lush climates to
      reproduce on. Their populations swing between dwindling and exploding at an alarming rate as
      they decimate the resources of each planet with their enormous birth rates and the inherent
      need for huge amounts of flora and fauna to feed their young. They have short lifespans
      compared to other races and so the cycle continues in a desperately violent frenzy to
      capture and absorb more and more planets.
    </p>
    <p>
      Amphibian ships fight the war at arm's length. They carry the longest ranged scanners in the
      fleet and the heaviest guided warheads to put on the end of them: a Terrapin sees 330 units,
      mounts five tubes and no gun at all. They find you first, fire on a wide forward arc, and
      spend the rest of the fight keeping the distance they opened with.
    </p>

    <h2>Feline</h2>
    <p>
      The Felidae live for the thrill of the hunt. Content with the food produced on their
      planets, they simply want more hunting grounds for their entertainment. Felidae planets are
      vicious places, ruled by an alpha-leader and steeped in thousands of years of violent
      history. Leadership is disorganized, with some rulers only living for mere days, but their
      intentions are clear: bigger prey brings greater prestige and honour among their peers, and
      so they will always hunt the biggest and most dangerous prey without fear or mercy.
    </p>
    <p>
      Feline hulls are the fastest and most agile in the war, and every one of them cloaks, though
      never as deeply as a Reptilian. They are also the thinnest, so a bad approach costs the ship.
      Turning up to 50 degrees a tick they can aim guns nobody else could bring to bear: a Cheetah
      swings its bow laser onto a target in three ticks where an Insectoid Swarm needs eight. Each
      carries a few mines, laid where the prey is going rather than sown as a field.
    </p>

    <h2>Human</h2>
    <p>
      Humanity destroyed their original home planet over a relatively short period of time due to
      their industrious nature and they are no strangers to strife and desperation. Their desire
      to grow and expand is driven by the need to find resources and habitable land for their
      enormous populations, but also by their scientific curiosity, which shows in what their
      fleets carry.
    </p>
    <p>
      Human ships are the generalists of the war, competent everywhere and extreme nowhere. What
      belongs to them alone is ordnance that leaves a hull untouched and ruins everything behind
      it: EMP warheads that drain shields and batteries, and nanocyte mines whose cloud splashes
      off a shield and burns bare hull. Knock a quadrant down, then let the nanocytes through it.
      Only the Babylon carries a cloak.
    </p>

    <h2>Insectoid</h2>
    <p>
      These curious creatures do not understand the political or recreational agendas of other
      races. They do not communicate well with the other species of the universe, and they work
      only to protect and grow their hive. Guided by a single entity known as the Royal Guardian,
      who can communicate with the entire hive instantaneously through their Psionic Link, they
      can perform complex military manoeuvres in perfect unison. A fleet of Insectoid vessels can
      strip a planet of all its resources in less than a solar year.
    </p>
    <p>
      Insectoid vessels are gargantuan hive ships, three models where every other race fields
      four, each slower, thicker and more heavily armed than anything else in space. Turning 20 to
      30 degrees a tick they can never swing a narrow gun onto anything, so their weapons point
      across the beam and they fight by holding ground: broadsides, magazines deep enough to keep
      firing all round, and mines sown as fields. No Insectoid hull carries a cloak. A hive does
      not hide.
    </p>

    <h2>Reptilian</h2>
    <p>
      The ferocious Reptilia are a xenophobic race of highly trained weapons of war. They are
      genetically perfect killing machines and have no interest in peace. On their home planet,
      genetic modification in birth centres is used to make each generation stronger, faster and
      smarter. To them, there is only one acceptable outcome in the great war: total annihilation
      of their foes.
    </p>
    <p>
      Reptilian ships carry the deepest cloaks in the game and the hardest lasers, and they lay no
      mines at all. Every gun points forward or across a beam, so a Reptilian commander picks an
      approach and lives with it. A Cobra's bow laser covers 30 degrees and does 320 damage at
      contact, and nothing whatsoever past 55 units. One pass decides the fight.
    </p>
  </article>
</div>

<style>
  .screen {
    height: 100%; overflow-y: auto; padding: 40px 32px;
    background: radial-gradient(120% 90% at 50% 0%, #0e1526 0%, #080b12 70%);
  }
  header, article { max-width: 680px; margin-left: auto; margin-right: auto; }
  header { margin-bottom: 24px; }
  h1 { margin: 10px 0 0; font-size: 19px; font-weight: 600; letter-spacing: 0.2em;
       text-transform: uppercase; color: var(--hull); }
  h2 { margin: 28px 0 8px; font-size: 12px; font-weight: 600; letter-spacing: 0.14em;
       text-transform: uppercase; color: var(--amber); }
  p { margin: 0; font-size: 13.5px; line-height: 1.7; color: var(--ink); }
  p + p { margin-top: 12px; }
  .lede { color: var(--ink-dim); }

  .back {
    font-family: var(--mono); font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--ink-dim); background: transparent; border: none; padding: 0; cursor: pointer;
  }
  .back:hover { color: var(--cyan); }
</style>