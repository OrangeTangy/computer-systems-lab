# Predictions before the thermal log (written before collection)

A SATA SSD at about 300 MB/s dissipates little power, so temperature should rise only a few degrees during a 30 GiB write and stay far below typical throttling points (about 70 C). If so, the slow plateaus of the sustained-write sawtooth are SLC-cache behavior, not thermal throttling. A throughput drop that coincides with a temperature peak would contradict this.
