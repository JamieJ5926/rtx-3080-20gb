#include <cstdio>
#include <cuda_runtime.h>
#define CHECK(x) do { cudaError_t e=(x); if(e){ fprintf(stderr,"CUDA %s:%d %s\n",__FILE__,__LINE__,cudaGetErrorString(e)); return 1; } } while(0)
__global__ void saxpy(int n, float a, float *x, float *y) {
  int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i < n) y[i] = a * x[i] + y[i];
}
int main() {
  const int n = 1 << 24;
  size_t bytes = n * sizeof(float);
  float *hx = new float[n], *hy = new float[n];
  for (int i = 0; i < n; i++) { hx[i] = 1.0f; hy[i] = 2.0f; }
  float *dx, *dy;
  CHECK(cudaMalloc(&dx, bytes));
  CHECK(cudaMalloc(&dy, bytes));
  CHECK(cudaMemcpy(dx, hx, bytes, cudaMemcpyHostToDevice));
  CHECK(cudaMemcpy(dy, hy, bytes, cudaMemcpyHostToDevice));
  saxpy<<<(n+255)/256, 256>>>(n, 2.0f, dx, dy);
  CHECK(cudaDeviceSynchronize());
  CHECK(cudaMemcpy(hy, dy, bytes, cudaMemcpyDeviceToHost));
  int bad = 0;
  for (int i = 0; i < n; i++) if (hy[i] != 4.0f) bad++;
  printf("compute_probe n=%d mismatches=%d\n", n, bad);
  cudaFree(dx); cudaFree(dy); delete[] hx; delete[] hy;
  return bad ? 1 : 0;
}
