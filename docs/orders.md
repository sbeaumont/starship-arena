# The order language

What a player may write, what reads it, and what can be checked before a round runs.

The file it lives in is described in [data.md](data.md). This page is the grammar.

## The grammar

```ebnf
plan      = { line } ;
line      = tick ":" order ;
order     = verb [ selector ] { parameter } ;

tick      = digit { digit } ;
verb      = letter { letter } ;
selector  = word ;                  (* a component's own name: R1, Shields, C1 *)
parameter = word ;
```

A verb is letters only, so `R25` is a verb and a parameter with no space between them, and
`Fire R1 90` is three words. Everything after the verb is split on whitespace, which is why no
value may contain one.

## Every order

| order | shape | example |
|---|---|---|
| accelerate | verb parameter | `1: A-10` |
| turn | verb parameter | `2: R25` |
| replenish | verb | `5: Rep` |
| fire | verb selector parameters | `3: Fire R1 90` |
| boost | verb selector parameters | `4: Boost Shields W 100` |
| power | verb selector parameter | `2: Power C1 4` |
| activation | verb selector parameter | `1: Act <component> on` |

The first three address the ship. The rest address one of its components, and take a selector to
say which.

Turning is one verb per direction, and the sign composes: `L-90` turns the same way as `R90`.
`Scan` is a second spelling of `Fire`, for pointing a gravscan.

Nothing offers an on/off at the moment, so `Act` has no valid target. The cloak took one until it
started taking a power level instead. The verb is kept for whatever wants switching rather than
setting.

## Who owns which part

Three owners, and keeping them apart is what stops any one of them growing knowledge of the
others.

**The verb belongs to the parser.** `COMMAND_WORDS` maps every accepted spelling to a command,
and a command never learns which word summoned it. Wording changes and aliases cost nothing.
[ADR 0005](adr/0005-commands-validated-before-execution.md)

**The selector names a component**, and resolves against the machine's own `all_components`. It is
the component's own name from the registry, so a player reads it off their ship.

**The parameters belong to the component.** `expected_parameters` is the component saying what an
order to it needs, each one carrying a `kind` an interface can offer a control for and answering
`is_valid` for itself. [ADR 0004](adr/0004-components-own-their-parameters.md)

That last one is an inversion of the usual arrangement, where an operation declares its own
arguments. It buys the generic planner: the game UI offers the right control for a component
without knowing what a shield is, and a new kind of weapon needs no interface change.

## What is checked, and what is not

Checked before the round runs, so a refusal reaches the player while they are still planning:

- the line has the `<tick>: <verb>` shape at all
- the verb is a word the parser knows
- the selector names a component this machine actually carries
- the number of words matches what that component's parameters consume
- each parameter validates its own word: a bearing inside a firing arc, a number in range, a
  quadrant that exists, a name the ship has scanned

Not checked: **whether the verb suits the component.** `Boost R1 90` is well formed. R1 offers one
parameter, one word was supplied, and 90 is a valid bearing, so every check above passes. Nothing
records which orders a component answers to, deliberately, so nothing can notice that a launcher
does not boost.

Such a line fails when it runs, and command execution is not guarded, so it takes the round with
it rather than being refused on its own. The order language assumes correct orders. The planner
cannot write a wrong one, and a hand written file can.