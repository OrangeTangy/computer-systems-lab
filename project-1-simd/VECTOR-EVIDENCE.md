# Targeted vectorization evidence

Source: GCC 13.1.0 native float build, `-O3 -march=native -ffp-contract=off`. Full compiler reports and objdump output are retained under `data/`.

The AXPY unit-stride path includes:

```asm
vmulps (%rdx,%rax,1),%ymm1,%ymm0
vaddps (%r8,%rax,1),%ymm0,%ymm0
```

YMM registers are 256 bits: eight float32 or four float64 lanes. Multiply and add are separate instructions because FMA contraction was disabled consistently. No AVX-512 masking is claimed.

The native dot-product path includes packed multiplication but scalar accumulation and lane rearrangement:

```asm
vmulps (%r8,%rax,1),%ymm4,%ymm1
vaddss %xmm1,%xmm0,%xmm0
vshufps $0x55,%xmm1,%xmm1,%xmm3
vaddss %xmm3,%xmm0,%xmm0
```

This explains why a compiler report can call a loop vectorized without removing its ordered-add dependency. A claim that this dot loop is completely non-vectorized would be false. Our original hypothesis was therefore too simple: some work vectorized, but the reduction remained constrained.

The native compiler report records 32-byte and 16-byte vector paths plus missed non-unit-stride paths. The source branches on stride at runtime, and the compiler can version a loop. Inspect the executed path rather than counting every vector instruction in the whole executable (which also includes initialization and runtime library code).

Scalar build disables tree vectorization. Default build targets baseline x86-64 instructions; native build selects the host ISA. Actual small/large runtime comparisons, not instruction names alone, decide whether the optimization helped.
