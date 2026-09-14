# Explain it without memorizing it

## Start with a seven-year-old's story

A child wants to put stickers in a book. SIMD means putting several stickers down with one motion. Cache means the stickers are on the desk. RAM means the stickers are across the room. SSD storage means asking the librarian to fetch a box. A long queue at the librarian can make everyone wait even when many boxes get delivered each minute.

The experiments ask which part takes time. We do the same job repeatedly and count carefully. We also try a trick that looks faster but is misleading, so we learn not to trust one shiny number.

## Then answer these questions

1. Why is SIMD speedup 5x for one small problem but nearly 1x for a big one?
2. Why does “the compiler used vector instructions” not prove the entire dot product runs in parallel?
3. Why is time per load in an ordinary array loop different from latency of a dependent load?
4. How can bandwidth increase while one request gets slower?
5. Why does scattered-page timing not prove the slowdown came only from the TLB?
6. Why do we keep failed optimizations in the report?
7. If an SSD performs 100,000 requests/second and matching mean latency is 100 microseconds, about how many requests are in flight? **10**, provided both measurements describe the same population and interval.
8. What does p99 mean? Why is it not the slowest request?
9. Why can a three-second SSD test differ from a half-hour test?
10. What evidence is still missing before claiming full rubric completion?

## A useful way to write every result

**Prediction:** what you expected before the run. **Observation:** a number and its units. **Explanation:** a mechanism consistent with that result. **Alternative:** another mechanism that could produce it. **Next test:** evidence that would distinguish them.

Example: “I expected more write traffic to increase latency. With six background writers, the probe median was about 366 ns versus 113 ns idle. Contention is consistent with this. Frequency and background activity may contribute. Longer repeated runs with counters would help separate the causes.”
