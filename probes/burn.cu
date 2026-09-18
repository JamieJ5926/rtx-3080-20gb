#include <cstdio>
#include <cstdlib>
#include <ctime>
#include <cuda_runtime.h>
#define CHECK(x) do { cudaError_t e=(x); if(e){ fprintf(stderr,"CUDA %s\n",cudaGetErrorString(e)); return 1; } } while(0)
__global__ void burn(float *a, int n, int iters) {
  int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i >= n) return;
  float x = a[i];
  float y = 1.0000001f + (i & 7) * 0.0001f;
  for (int k = 0; k < iters; k++) {
    x = fmaf(x, y, 1.0000001f);
    y = fmaf(y, x, 1.0000001f);
  }
  a[i] = x + y;
}
int main(int argc, char **argv) {
  int seconds = argc > 1 ? atoi(argv[1]) : 600;
  int n = 1 << 24;
  float *d;
  CHECK(cudaMalloc(&d, n * sizeof(float)));
  CHECK(cudaMemset(d, 1, n * sizeof(float)));
  int blocks = (n + 255) / 256;
  time_t end = time(0) + seconds;
  unsigned long long rounds = 0;
  printf("burn_start seconds=%d n=%d\n", seconds, n);
  fflush(stdout);
  while (time(0) < end) {
    burn<<<blocks, 256>>>(d, n, 256);
    CHECK(cudaDeviceSynchronize());
    rounds++;
  }
  printf("burn_done rounds=%llu\n", rounds);
  cudaFree(d);
  return 0;
}
