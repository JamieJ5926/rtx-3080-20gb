#include <cstdio>
#include <cstdlib>
#include <unistd.h>
#include <cstdint>
#include <cuda_runtime.h>
#define CHECK(x) do { cudaError_t e=(x); if(e){ fprintf(stderr,"CUDA %s:%d %s\n",__FILE__,__LINE__,cudaGetErrorString(e)); return 1; } } while(0)
__global__ void touch(uint32_t *p, size_t nwords, uint32_t seed) {
  size_t i = blockIdx.x * (size_t)blockDim.x + threadIdx.x;
  size_t stride = (size_t)gridDim.x * blockDim.x;
  for (; i < nwords; i += stride) p[i] = (uint32_t)i ^ seed;
}
__global__ void verify(uint32_t *p, size_t nwords, uint32_t seed, unsigned long long *errs) {
  size_t i = blockIdx.x * (size_t)blockDim.x + threadIdx.x;
  size_t stride = (size_t)gridDim.x * blockDim.x;
  for (; i < nwords; i += stride) if (p[i] != ((uint32_t)i ^ seed)) atomicAdd(errs, 1ULL);
}
int main(int argc, char **argv) {
  if (argc < 2) { fprintf(stderr, "usage: vram <gib> [hold_sec]\n"); return 2; }
  double gib = atof(argv[1]);
  int hold = argc > 2 ? atoi(argv[2]) : 8;
  size_t bytes = (size_t)(gib * 1024.0 * 1024.0 * 1024.0);
  bytes &= ~((size_t)4095);
  size_t nwords = bytes / 4;
  uint32_t *p; unsigned long long *derr, herr = 0;
  printf("allocating %.2f GiB (%zu bytes)\n", gib, bytes);
  CHECK(cudaMalloc(&p, bytes));
  CHECK(cudaMalloc(&derr, sizeof(unsigned long long)));
  CHECK(cudaMemset(derr, 0, sizeof(unsigned long long)));
  touch<<<256, 256>>>(p, nwords, 0xA5A5A5A5u);
  CHECK(cudaDeviceSynchronize());
  verify<<<256, 256>>>(p, nwords, 0xA5A5A5A5u, derr);
  CHECK(cudaDeviceSynchronize());
  CHECK(cudaMemcpy(&herr, derr, sizeof(herr), cudaMemcpyDeviceToHost));
  printf("verify_mismatches=%llu hold=%ds\n", herr, hold);
  if (herr) { cudaFree(p); cudaFree(derr); return 1; }
  cudaEvent_t start, stop;
  CHECK(cudaEventCreate(&start)); CHECK(cudaEventCreate(&stop));
  CHECK(cudaEventRecord(start));
  for (int t = 0; t < hold; t++) {
    touch<<<256, 256>>>(p, nwords, 0x5A5A5A5Au + t);
    CHECK(cudaDeviceSynchronize());
  }
  CHECK(cudaEventRecord(stop)); CHECK(cudaEventSynchronize(stop));
  float ms = 0; CHECK(cudaEventElapsedTime(&ms, start, stop));
  printf("holding_alloc_sleep=%ds\n", hold);
  fflush(stdout);
  sleep(hold);
  printf("hold_ok elapsed_ms=%.0f\n", ms);
  cudaFree(p); cudaFree(derr);
  return 0;
}
