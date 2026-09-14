# Controlled follow-up hypotheses (before collection)

The lectures distinguish shared-core SMT from multicore execution and stress changing the mechanism that addresses the measured bottleneck. The original sweep changed core type with worker count and allowed full-pass worker overhang.

1. Fixing background workers on P-core logical CPUs 2, 4 and 6 while probing CPU 0 should remove the P/E placement change as a sweep variable. Native Windows core masks must confirm separate physical cores.
2. Varying a delay between 128 KiB traffic chunks, rather than changing worker placement, should expose a more controlled offered-load curve. This does not guarantee saturation.
3. Checking the stop signal at chunk boundaries should substantially reduce worker overhang relative to the original 128 MiB pass boundary. Record measured start lag and end overhang rather than assuming perfect synchronization.
4. Five repetitions improve visibility into variability. A separate pointer probe still measures a different request population from streamers, so exact Little's Law occupancy for streamers remains unavailable.
